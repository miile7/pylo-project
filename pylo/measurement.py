import io
import os
import copy
import time
import typing
import logging
import datetime

import numpy as np

from collections import defaultdict

from .events import emergency
from .events import after_stop
from .events import microscope_ready
from .events import before_record
from .events import after_record
from .events import measurement_ready

from .errors import BlockedFunctionError

from .image import Image
from .logginglib import log_debug
from .logginglib import log_error
from .datatype import Datatype
from .logginglib import get_logger
from .log_thread import LogThread
from .stop_program import StopProgram
from .exception_thread import ExceptionThread
from .measurement_steps import MeasurementSteps
from .measurement_variable import MeasurementVariable

# from .config import DEFAULT_SAVE_DIRECTORY
# from .config import DEFAULT_SAVE_FILE_NAME

CONFIG_MEASUREMENT_GROUP = "measurement"

class Measurement:
    """This class represents one measurement.

    Attributes
    ----------
    tags : dict
        Any information that should be stored about this measurement
    steps : MeasurementSteps or sequence of dicts
        A list of dicts where each dict contains **all** `MeasurementVariable`
        ids as the keys and the corresponding value in the
        `MeasurementVariable` specific unit
    controller : Controller
        The controller
    save_dir : str
        The absolute path of the directory where to save this measurement to
    microscope_safe_after : bool
        Whether to set the microscope in its safe mode if the measurememt is 
        finished
    camera_safe_after : bool
        Whether to set the camera in its safe mode if the measurememt is 
        finished
    relaxation_time : float
        The relaxation time in seconds to wait after the microscope has been 
        set to lorentz mode
    name_format : str
        The file name how to save the images (including the extension, 
        supported are all the extensions provided by the `CameraInterface`),
        placeholders are supported and described in the formatName() function
    current_image : Image
        The last recorded image object
    running : bool
        Whether the measurement is running or not, to stop the measurement 
        immediately set this to False
    finished : bool
        Whether the measurement was completely run and finished successfully
        
    Listened Events
    ---------------
    emergency
        Stop the measurement if the event is fired
    """

    def __init__(self, controller: "Controller", 
                 steps: typing.Union[MeasurementSteps, typing.Sequence[dict]]) -> None:
        self.controller = controller
        self.tags = {}
        self.steps = steps

        self._logger = get_logger(self)

        # prepare the save directory and the file format
        self.save_dir, self.name_format, self._measurement_log_path = self.controller.getConfigurationValuesOrAsk(
            (CONFIG_MEASUREMENT_GROUP, "save-directory"),
            (CONFIG_MEASUREMENT_GROUP, "save-file-format"),
            (CONFIG_MEASUREMENT_GROUP, "log-save-path"),
            fallback_default=True
        )

        # make sure the directory exists
        if not os.path.exists(self.save_dir):
            try:
                log_debug(self._logger, ("Creating measurement save directory " + 
                                        "'{}'").format(self.save_dir))
                os.makedirs(self.save_dir, exist_ok=True)
            except OSError as e:
                err = OSError(("The save directory '{}' does not exist and " + 
                               "cannot be created.").format(self.save_dir)).with_traceback(e.__traceback__)
                log_error(self._logger, err)
                raise err
        
        self._measurement_log_thread = None

        if self._measurement_log_path == "":
            self._measurement_log_path = self.controller.configuration.getDefaultValue(
                CONFIG_MEASUREMENT_GROUP, "log-save-path")

        # make sure the parent directory exists
        measurement_log_dir = os.path.dirname(self._measurement_log_path)
        if not os.path.exists(measurement_log_dir):
            try:
                log_debug(self._logger, ("Creating measurement log " + 
                                         "directory '{}'").format(
                                         measurement_log_dir))
                os.makedirs(measurement_log_dir, exist_ok=True)
            except OSError as e:
                err = OSError(("The log directory '{}' does not exist and " + 
                               "cannot be created.").format(measurement_log_dir)).with_traceback(e.__traceback__)
                log_error(self._logger, err)
                raise err
        
        # prepare whether to go in safe mode after the measurement has finished
        try:
            self.microscope_safe_after = self.controller.configuration.getValue(
                CONFIG_MEASUREMENT_GROUP,
                "microscope-to-safe-state-after-measurement"
            )
        except KeyError:
            log_debug(self._logger, ("Could not find key '{}' in group '{}'").format(
                "microscope-to-safe-state-after-measurement",
                CONFIG_MEASUREMENT_GROUP))
            self.microscope_safe_after = None

        self.microscope_safe_after = (self.microscope_safe_after == True)

        # prepare whether to go in safe mode after the measurement has finished
        try:
            self.camera_safe_after = self.controller.configuration.getValue(
                CONFIG_MEASUREMENT_GROUP,
                "camera-to-safe-state-after-measurement"
            )
        except KeyError:
            log_debug(self._logger, ("Could not find key '{}' in group '{}'").format(
                "camera-to-safe-state-after-measurement",
                CONFIG_MEASUREMENT_GROUP))
            self.camera_safe_after = None
        
        self.camera_safe_after = (self.camera_safe_after == True)

        # prepare the relaxation time to wait before continuing after the 
        # measurement is set to the lorentz mode
        try:
            self.relaxation_time = self.controller.configuration.getValue(
                CONFIG_MEASUREMENT_GROUP,
                "relaxation-time-lorentz-mode"
            )
        except KeyError:
            self.relaxation_time = None
        
        if (not isinstance(self.relaxation_time, (int, float)) or 
            self.relaxation_time < 0):
            self.relaxation_time = 0
        
        log_debug(self._logger, "Setting relaxation time to '{}'".format(self.relaxation_time))

        self.current_image = None
        self.running = False
        self.finished = False
        self.measurement_logging = True
        self._image_save_threads = []

        # stop the measurement when the emergency event is fired
        log_debug(self._logger, "Adding stop() function call to emergency " + 
                               "event")
        emergency.append(self.stop)

        # the index in the steps that is currently being measured
        self._step_index = -1
    
    def formatName(self, name_format: typing.Optional[str]=None, 
                   tags: typing.Optional[dict]=None,
                   variables: typing.Optional[dict]=None,
                   imgtags: typing.Optional[dict]=None,
                   time: typing.Optional[datetime.datetime]=None,
                   counter: typing.Optional[int]=None) -> str:
        """Format the given name_format.

        The following placeholders are supported:
        - {tags[tags_index]}: Any value of the measurement tags can be 
          accessed by using `tags` with the index. For recursive structures 
          use the next index also surrounded by brackets like accesssing dicts.
        - {variables[measurement_variable_id]}: The values of each measurement 
          variable can be accessed by using the `variables` keyword together 
          with the `measurement_variable_id` which is the `MeasurementVariable`
          id of the value to get, the value will be printed without units
        - {imgtags[image_tag_index]}: The tags of the recorded image can be 
          accessed by using `imgtags`
        - {time:%Y-%m-%d %H:%M:%S}: The measurement recording time can be 
          accessed using the `time` keyword followed by any valid `strftime()` 
          format
        - {counter}: The current index of the measurement step
    
        Parameters
        ----------
        name_format : str, optional
            The name format to use, default: `Measurement.name_format`
        tags : dict, optional
            The measurement tags to use for replacing in the `name_format`,
            default: `Measurement.tags`
        variables : dict, optional
            The values of the `MeasurementVariables` for replacing in the 
            `name_format`, the key is the id and the value is the value in the 
            units of the `MeasurementVariable`, default: current values
        imgtags : dict, optional
            The image tags to use for replacing in the `name_format`,
            default: `Measurement.current_image.tags`
        time : datetime, optional
            The datetime to use for replacing in the `name_format`,
            default: `datetime.datetime.now()`
        counter : int, optional
            The counter to use for replacing in the `name_format`,
            default: `Measurement._step_index`
        
        Returns
        -------
        str
            The formatted name
        """
        if not isinstance(name_format, str):
            name_format = self.name_format
        if not isinstance(tags, dict):
            tags = self.tags
        if not isinstance(variables, dict):
            if 0 <= self._step_index <= len(self.steps):
                variables = self.steps[self._step_index]
            else:
                variables = {}
        if not isinstance(imgtags, dict):
            if isinstance(self.current_image, Image):
                imgtags = self.current_image.tags
            else:
                imgtags = {}
        if not isinstance(time, datetime.datetime):
            time = datetime.datetime.now()
        if not isinstance(counter, int):
            counter = self._step_index
        
        name = name_format.format_map(defaultdict(str, tags=tags, 
            variables=variables, var=variables, imgtags=imgtags, time=time,
            date=time, datetime=time, counter=counter, number=counter, 
            num=counter))
        log_debug(self._logger, "Formatting name to '{}'".format(name))
        return name
    
    def _setSafe(self) -> None:
        """Set the microscope and the camera to be in safe state."""

        log_debug(self._logger, "Setting micorsocpe and camera to safe state",
                               exc_info=True)

        try:
            self.controller.microscope.resetToSafeState()
        except BlockedFunctionError:
            # emergency event is called, microscope goes in emergency state by 
            # itself
            pass

        try:
            self.controller.camera.resetToSafeState()
        except BlockedFunctionError:
            # emergency event is called, camera goes in emergency state by 
            # itself
            pass
    
    def start(self) -> None:
        """Start the measurement.
        
        Fired Events
        ------------
        microscope_ready
            Fired when the microscope is in lorentz mode the measurement is 
            right about starting
        before_record
            Fired before setting the microscope to the the next measurement 
            point
        after_record
            Fired after setting the microscope to measurement point and 
            recording an image but before saving the image to the directory
        measurement_ready
            Fired when the measurement has fully finished
        """
        log_debug(self._logger, ("Starting measurement with microscope '{}'" + 
                                "and camera '{}'").format(
                                self.controller.microscope, self.controller.camera))
        
        self.finished = False
        self.running = True
        
        # self.controller.view.progres_max = len(self.steps)
        self.controller.view.print("Starting measurement...")
        self.controller.view.print("Used devices:")
        self.controller.view.print("  Camera: {}".format(
            self.controller.camera.name))
        self.controller.view.print("  Microscope: {}".format(
            self.controller.microscope.name))
        self.controller.view.print(
            "Saving all images to {}.".format(self.save_dir), inset="  "
        )

        self._image_save_threads = []

        if self.measurement_logging:
            log_debug(self._logger, "Initializing measurement log")
            self.setupMeasurementLog(
                [v.unique_id for v in self.controller.microscope.supported_measurement_variables],
                ["Action"],
                ["Image path", "Time"]
            )

        try:
            log_debug(self._logger, "Setting microscope to lorentz mode")
            # set to lorentz mode
            self.controller.view.print("Setting to lorentz mode...")
            self.controller.microscope.setInLorentzMode(True)
        
            if (isinstance(self.relaxation_time, (int, float)) and 
                self.relaxation_time > 0):
                log_debug(self._logger, ("Waiting relaxation time of '{}' " + 
                                        "seconds").format(self.relaxation_time))
                start_time = time.time()

                while time.time() - start_time < self.relaxation_time:
                    # allow calling stop() function while waiting
                    time.sleep(0.01)

                    if not self.running:
                        # stop() is called
                        return
                
                log_debug(self._logger, "Continuing with measurement")

            if not self.running:
                log_debug(self._logger, ("Stopping measurement because running " + 
                                        "is now '{}'").format(self.running))
                # stop() is called
                return
            
            # trigger microscope ready event
            log_debug(self._logger, "Firing 'microscope_ready' event")
            microscope_ready()
            self.controller.view.print("Done.")

            for self._step_index, step in enumerate(self.steps):
                # start going through steps
                log_debug(self._logger, "Starting step '{}': '{}'".format(
                                       self._step_index, step))

                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return

                # check all thread exceptions
                self.raiseThreadErrors()
                
                # fire event before recording
                log_debug(self._logger, "Firing 'before_record' event")
                before_record()

                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return

                if self.measurement_logging:
                    # add the values to reach to the current log
                    self.addToMeasurementLog(step, "Targetting values", "", 
                                  datetime.datetime.now().isoformat())

                step_descr = ", ".join(["{}: {}".format(k, v) for k, v in step.items()])  
                self.controller.view.print("Approaching step {}: {}.".format(
                    self._step_index, step_descr
                ))

                # the asynchronous threads to set the values at the micrsocope
                measurement_variable_threads = []

                for variable_name in step:
                    log_debug(self._logger, ("Setting variable '{}' of step to " + 
                                            "value '{}'").format(variable_name,
                                           step[variable_name]))
                    # set each measurement variable
                    if not self.running:
                        log_debug(self._logger, ("Stopping measurement because " + 
                                                "running is now '{}'").format(self.running))
                        # stop() is called
                        return
                    
                    if self.controller.microscope.supports_parallel_measurement_variable_setting:
                        # MicroscopeInterface.setMeasurementVariableValue() can
                        # set parallel
                        log_debug(self._logger, ("Microscope can set variables " + 
                                                "parallely, creating new " + 
                                                "thread for variable"))
                        thread = ExceptionThread(
                            target=self.controller.microscope.setMeasurementVariableValue,
                            args=(variable_name, step[variable_name]),
                            name="microscope variable {} in step {}".format(
                                variable_name, self._step_index
                            )
                        )
                        log_debug(self._logger, "Starting variable setting " + 
                                               "thread")
                        thread.start()
                        measurement_variable_threads.append(thread)
                    else:
                        # set measurement variables sequential
                        self.controller.microscope.setMeasurementVariableValue(
                            variable_name, 
                            step[variable_name]
                        )
                
                log_debug(self._logger, ("Waiting for '{}' variable setting " + 
                                        "threads").format(len(measurement_variable_threads)))
                # Wait for all measurement variable threads to finish
                for thread in measurement_variable_threads:
                    thread.join()
                
                # check all thread exceptions
                self.raiseThreadErrors(*measurement_variable_threads)
                
                self.controller.view.print("Done.", inset="  ")
                
                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return

                log_debug(self._logger, "Receiving values from microscope")
                # get the actual values
                variable_values = {}
                for variable_name in step:
                    variable_values[variable_name] = (
                        self.controller.microscope.getMeasurementVariableValue(variable_name)
                    )
                log_debug(self._logger, "Got values '{}' from microscope".format(
                                        variable_values))
                log_debug(self._logger, "Recording image")
                
                self.controller.view.print("Recording image...", inset="  ")
                # record measurement, add the real values to the image
                self.current_image = self.controller.camera.recordImage(
                    self.createTagsDict(variable_values)
                )
                name = self.formatName()
                
                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return
                
                if self.measurement_logging:
                    # add the real values to the log
                    self.addToMeasurementLog(variable_values, "Recording image", name, 
                                  datetime.datetime.now().isoformat())
                
                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return
                
                # fire event after recording but before saving
                log_debug(self._logger, "Firing 'after_record' event")
                after_record()

                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called, maybe by after_record() event handler
                    return
                
                log_debug(self._logger, ("Starting image save thread for " +
                                        "image '{}'").format(name))
                
                # save the image parallel to working on, saveTo() funciton
                # returns a running thread
                thread = self.current_image.saveTo(
                    os.path.join(self.save_dir, name), overwrite=True, 
                    create_directories=True
                )
                self._image_save_threads.append(thread)
                self.controller.view.print("Saving image as {}...".format(name), 
                                           inset="  ")

                # check all thread exceptions
                self.raiseThreadErrors()

                log_debug(self._logger, "Increasing progress to '{}'".format(self._step_index + 1))
                
                self.controller.view.progress = self._step_index + 1

            log_debug(self._logger, "Done with all steps")
            
            self.controller.view.print("Done with measurement.")

            reset_threads = []
            # reset microscope and camera to a safe state so there is no need
            # for the operator to come back very quickly, do this while waiting
            # for the save threads to finish
            if self.microscope_safe_after:
                log_debug(self._logger, "Setting microscope to safe state " + 
                                       "in other thread because settings " + 
                                       "told so")
                thread = ExceptionThread(
                    target=self.controller.microscope.resetToSafeState,
                    name="reset microscope to safe state"
                )
                thread.start()
                reset_threads.append(thread)
                self.controller.view.print("Setting microscope to safe state...")
            if self.camera_safe_after:
                log_debug(self._logger, "Setting camera to safe state " + 
                                       "in other thread because settings " + 
                                       "told so")
                thread = ExceptionThread(
                    target=self.controller.camera.resetToSafeState,
                    name="reset camera to safe state"
                )
                thread.start()
                reset_threads.append(thread)
                self.controller.view.print("Setting camera to safe state...")

            # stop log thread
            if isinstance(self._measurement_log_thread, LogThread):
                self._measurement_log_thread.finishAndStop()
                
            # check all thread exceptions
            self.raiseThreadErrors(*reset_threads)

            log_debug(self._logger, "Waiting for images to finish saving")

            # wait for all saving threads to finish
            self.waitForAllImageSavings()
            self.controller.view.print("Waiting for saving images...")

            # wait for all machine reset threads to finish
            for thread in reset_threads:
                thread.join()
            
            # check all thread exceptions
            self.raiseThreadErrors(*reset_threads)

            self.controller.view.print("Everything done, finished.")

            # reset everything to the state before measuring
            self.running = False
            self._step_index = -1

            log_debug(self._logger, "Setting 'finished' to True")
            self.finished = True

            log_debug(self._logger, "Firing 'measurement_ready' event")
            measurement_ready()
        except StopProgram as e:
            log_debug(self._logger, "Stopping program", exc_info=e)
            self.stop()
            raise e
        except Exception as e:
            # stop if any error occurres, just to be sure
            log_error(self._logger, e)
            self.stop()
            raise e
    
    def waitForAllImageSavings(self) -> None:
        """Wait until all threads where images or the log are saved have 
        finished."""
        log_debug(self._logger, "Waiting for all save threads")
        
        for thread in self._image_save_threads + [self._measurement_log_thread]:
            if isinstance(thread, ExceptionThread):
                log_debug(self._logger, "Joining thread '{}'".format(thread.name))
                thread.join()
                
                if len(thread.exceptions):
                    for error in thread.exceptions:
                        log_error(error)
                        raise error
        
        log_debug(self._logger, "Done with waiting")
    
    def stop(self) -> None:
        """Stop the measurement. 
        
        Note that the current hardware action is still finished when it has 
        started already!

        Fired Events
        ------------
        after_stop
            Fired when this function is executed
        """

        log_debug(self._logger, "Stopping measurement")
        
        self.running = False
        self._setSafe()

        if isinstance(self._measurement_log_thread, LogThread):
            log_debug(self._logger, "Stopping measurement log thread")
            self._measurement_log_thread.stop()

        # fire stop event
        log_debug(self._logger, "Firing 'after_stop' event")
        after_stop()
    
    def raiseThreadErrors(self, *additional_threads: "ExceptionThread") -> None:
        """Check all thread collections of this class plus the 
        `additional_threads` if they contain exceptions and if so, raise them.

        Raises
        ------
        Exception
            Any exception that is contained in one of the threads

        Paramteres
        ----------
        additional_threads : ExceptionThread
            Additional threads to check
        """

        for thread in (*self._image_save_threads, self._measurement_log_thread, *additional_threads):
            if (isinstance(thread, ExceptionThread) and len(thread.exceptions) > 0):
                for error in thread.exceptions:
                    log_error(self._logger, error)
                    raise error
    
    def createTagsDict(self, step: dict) -> dict:
        """Get the tags dictionary by the given step.

        Paramters
        ---------
        step : dict
            A dict containing the ids of all measurement variables as the key
            and the current value as the value
        
        Returns
        -------
        dict
            The tags dict to save in the image
        """

        from .config import PROGRAM_NAME

        beautified_step = {}
        for var_id, val in step.items():
            var = self.controller.microscope.getMeasurementVariableById(var_id)

            if var.has_calibration and var.calibrated_name is not None:
                name = str(var.calibrated_name)
            else:
                name = str(var.name)

            if var.has_calibration and var.calibrated_unit is not None:
                name += " (in {})".format(var.calibrated_unit)
            elif var.unit is not None:
                name += " (in {})".format(var.unit)
            
            if var.has_calibration:
                val = var.ensureCalibratedValue(val)
            
            if var.has_calibration and isinstance(var.calibrated_format, Datatype):
                val = var.calibrated_format.format(val)
            elif isinstance(var.format, Datatype):
                val = var.format.format(val)

            beautified_step[name] = val

        tags = {
            "Measurement Step": {
                "Human readable": beautified_step,
                "Machine values": copy.deepcopy(step)
            },
            "Acquire time": datetime.datetime.now().isoformat(),
            "{} configuration".format(PROGRAM_NAME): self.controller.configuration.asDict()
        }
        if isinstance(self.tags, dict):
            tags.update(self.tags)

        return tags
    
    def setupMeasurementLog(self, variable_ids: typing.List[str], 
                 before_columns: typing.Optional[typing.List[str]]=[], 
                 after_columns: typing.Optional[typing.List[str]]=[]) -> None:
        """Define the log format.

        The `variable_ids` name and unit will be added to the log. If there is 
        a calibration, the uncalibrated value is automatically appended as a 
        column before the calibrated value.

        Raises
        ------
        OSError, IOError
            When the log file cannot be opened
        
        Parameters
        ----------
        variable_ids : list
            A list of all the `MeasurementVariable` ids that can occurre.
        before_columns : list
            A list that contains the header names of the columns that should be
            printed before the variables
        after_columns : list
            A list that contains the header names of the columns that should be
            printed after the variables
        """

        self._measurement_log_thread = LogThread(self._measurement_log_path)
        self._measurement_log_thread.start()

        self._log_columns = before_columns + variable_ids + after_columns
        column_headlines = before_columns

        for id_ in variable_ids:
            var = self.controller.microscope.getMeasurementVariableById(id_)
            column_headlines.append(
                str(var.name) + " " + 
                str(var.unique_id) + 
                ((" [" + str(var.unit) + "]") if var.unit is not None else "")
            )

            if var.has_calibration:
                column_headlines.append(
                    str(var.calibrated_name) + " " + 
                    str(var.unique_id) + 
                    ((" [" + str(var.calibrated_unit) + "]") 
                     if var.calibrated_unit is not None else "")
                )
        column_headlines += after_columns

        log_debug(self._logger, "Setting up measurement log with columns " + 
                               "'{}'".format(column_headlines))
        
        self._measurement_log_thread.addToLog(column_headlines)
    
    def addToMeasurementLog(self, variables: dict, *columns: str) -> None:
        """Add a line of columns to the log.

        If a `MeasurementVariable` has a calibration, the uncalibrated value is 
        automatically calculated and appended to the column before the variable
        itself.
        
        Parameters
        ----------
        variables : dict
            The measurement variables to log, the key is the id and the value
            is the measurement variable value in its own units, if there is a
            calibration given, the calibrated unit is assumed
        columns : str
            Additional columns, they will be added before and/or after the 
            variables, depending on the column layout defined in the 
            `Measurement::setupMeasurementLog()` function
        """
        cells = []
        variable_ids = [v.unique_id for v in 
                        self.controller.microscope.supported_measurement_variables]
        
        i = 0
        for col in self._log_columns:
            if col in variable_ids:
                if col in variables:
                    var = self.controller.microscope.getMeasurementVariableById(col)
                    
                    if isinstance(var.format, Datatype):
                        cells.append(var.format.format(variables[col]))
                    else:
                        cells.append(variables[col])

                    if var.has_calibration:
                        converted = var.convertToCalibrated(variables[col])
                        if isinstance(var.calibrated_format, Datatype):
                            cells.append(var.calibrated_format.format(converted))
                        else:
                            cells.append(converted)

                else:
                    cells.append("")
            elif i < len(columns):
                cells.append(columns[i])
                i += 1
            else:
                cells.append("")
        
        log_debug(self._logger, "Adding cells '{}' to measurement log".format(cells))
        
        self._measurement_log_thread.addToLog(cells)
    
    @classmethod
    def fromSeries(class_, controller: "Controller", start_conditions: dict, 
                   series: dict) -> "Measurement":
        """Create a measurement object.
        
        Create a measurement, the `start_conditions` contains all 
        `MeasurementVariable`s defined with their values, the series is a dict 
        that has a 'variable', a 'start', a 'step-width' and an 'end' index. 
        Optionally there can be a 'on-each-point' index which may contain 
        another series dict. The series defined in the 'on-each-point' index 
        will then be performed on each step of the `series`.

        Example
        -------
        >>> m = Measurement.fromSeries(
        ...     controller,
        ...     {"focus": 0, "magnetic-field": 0, "x-tilt": 0},
        ...     {"variable": "magnetic-field", "start": 0, "end": 5, 
        ...      "step-width": 2.5, "on-each-point": {
        ...         "variable": "x-tilt": "start": -35, "end": -35,
        ...         "step-width": 5}
        ...     }
        ... )
        <__main__.Measurement object at 0x0000000000000000>

        Notes
        -----
        The `start_condition` value for the `MeasurementVariable` that the 
        series is done of will be ignored because the `series` defines the 
        start conditions. 

        In other words: The value of the `start_condition[series["variable"]]`
        is ignored because `series["start"]` defines the start condition for
        the `series["variable"]`.

        Raises
        ------
        KeyError
            When the `start_conditions` does not contain all supported 
            `MeasurementVariables` or when the `series` is missing the 
            'variable', 'start', 'end' or 'step-width' indices
        ValueError
            When the `start_conditions` or the `series` 'step' or 'end' 
            contains invalid values (e.g. values are out of the bounds the 
            `MeasurementVariable` defines) or the `series` 'step-width' index
            is smaller or equal to zero
        TypeError
            When one of the values has the wrong type

        Parameters
        ----------
        controller : Controller
            The controller for the measurement and the microscope
        start_conditions : dict of int or floats
            The start conditions, the `MeasurementVariable` id has to be the 
            key, the value to start with (in the `MeasurementVariable` specific 
            units) has to be the value, note that every `MeasurementVariable` 
            has to be included
        series : dict with str, and three or four times int or float
            A dict with the 'variable', 'start', 'step-width', 'end' and the 
            optional 'on-each-point' indices. The series iterate the 
            `MeasurementVaraible` at the 'variable' index starting with 'start'
            and ending at 'end' (including start and end) while travelling with 
            the 'step-width'. The 'on-each-point' can hold another series dict
            that defines another series that will be iterated over on each step
            the current series does.
        
        Returns
        -------
        Measurement
            The measurement that holds all the steps to perform defined 
            measurement
        """

        return Measurement(controller, 
                           MeasurementSteps(controller, start_conditions, series))
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration") -> None:
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        """

        # import as late as possible to allow changes by extensions
        from .config import DEFAULT_MICROSCOPE_TO_SAFE_STATE_AFTER_MEASUREMENT
        from .config import DEFAULT_CAMERA_TO_SAFE_STATE_AFTER_MEASUREMENT
        from .config import DEFAULT_RELAXATION_TIME
        from .config import DEFAULT_SAVE_DIRECTORY
        from .config import DEFAULT_SAVE_FILE_NAME
        from .config import DEFAULT_LOG_PATH
        
        # add whether a relaxation time after the lornez mode is activated
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "relaxation-time-lorentz-mode", 
            datatype=float, 
            default_value=DEFAULT_RELAXATION_TIME, 
            description="The relaxation time in seconds to wait after the " + 
            "microscope is switched to lorentz mode. Use 0 or negative values " + 
            "to ignore."
        )
        
        # add whether to set the microscope to the safe state after the 
        # measurement has finished or not
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "microscope-to-safe-state-after-measurement", 
            datatype=bool, 
            default_value=DEFAULT_MICROSCOPE_TO_SAFE_STATE_AFTER_MEASUREMENT, 
            description="Whether to set the microscope in the safe sate " + 
            "after the measurement is finished."
        )
        
        # add whether to set the camera to the safe state after the 
        # measurement has finished or not
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "camera-to-safe-state-after-measurement", 
            datatype=bool, 
            default_value=DEFAULT_CAMERA_TO_SAFE_STATE_AFTER_MEASUREMENT, 
            description="Whether to set the camera in the safe sate " + 
            "after the measurement is finished."
        )

        # add an entry to the config and ask the user if there is nothing
        # saved
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "save-directory", 
            datatype=Datatype.dirpath, 
            default_value=DEFAULT_SAVE_DIRECTORY, 
            ask_if_not_present=True,
            description="The directory where to save the camera images to " + 
            "that are recorded while measuring."
        )

        # add an entry to the config and ask the user if there is nothing
        # saved
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "save-file-format", 
            datatype=str, 
            default_value=DEFAULT_SAVE_FILE_NAME, 
            ask_if_not_present=True,
            description="The name format to use to save the recorded images. " + 
            "Some placeholders can be used. Use {counter} to get the current " + 
            "measurement number, use {tags[your_value]} to get use the " + 
            "`your_value` of the measurement tags. Use " + 
            "{variables[your_variable]} to get the value of the measurement " + 
            "variable `your_variable`. To use the `your_img_value` of the " + 
            "image tags, use {imgtags[your_value]}. For times set the format " + 
            "according to the python `strftime()` format, started with a " + 
            "colon (:), like {time:%Y-%m-%d_%H-%M-%S} for year, month, day and " + 
            "hour minute and second. Make sure to inculde the file extension " + 
            "but use supported extensions only."
        )
        
        # add the save path for the log
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "log-save-path",
            datatype=Datatype.filepath,
            default_value=DEFAULT_LOG_PATH,
            description=("The file path (including the file name) to save " + 
            "log to.")
        )