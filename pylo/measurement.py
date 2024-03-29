import io
import os
import copy
import math
import time
import typing
import logging
import datetime

import numpy as np

from collections import defaultdict

from .events import emergency
from .events import after_stop
from .events import microscope_ready
from .events import before_approach
from .events import before_record
from .events import after_record
from .events import measurement_ready

from .errors import BlockedFunctionError

from .image import Image
from .logginglib import log_info
from .logginglib import log_debug
from .logginglib import log_error
from .datatype import Datatype
from .logginglib import get_logger
from .log_thread import LogThread
from .pylolib import expand_vars
from .pylolib import human_concat_list
from .pylolib import get_expand_vars_text
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
        The relaxation time in seconds to wait after the microscope has reached 
        the measurement variable values after approaching each step
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
    step_index : int
        The current step that is performed, if no measurement is running, the 
        step is -1
    current_step : dict or None
        The current step that is used, if no measurement is running, the 
        current step is None
    substep_count : int, read-only
        The number of sub steps to perform, each step will be divided into 
        this number of steps to allow "continously" and "parallel" setting of 
        the measurement variables, note that this is read-only since changing
        this value does not have any effect
        
    Listened Events
    ---------------
    emergency
        Stop the measurement if the event is fired
    """

    def __init__(self, controller: "Controller", 
                 steps: typing.Union[MeasurementSteps, typing.Sequence[dict]],
                 start: typing.Optional[dict]=None,
                 series: typing.Optional[dict]=None) -> None:
        """Create a measurememt object.

        Parameters
        ----------
        controller : Controller
            The controller
        steps : MeasurementSteps or dict
            The steps to perform
        start, series : dict
            The start and the series definition, they are only used for 
            offering name formatting and image details, if the `steps` is a
            `MeasurementSteps` object the internal `series` and `start` are 
            used and those parameters are ignored even if they are given,
            default: None
        """

        self.controller = controller
        self.tags = {}
        self.steps = steps

        self.substep_count = controller.configuration.getValue(
            CONFIG_MEASUREMENT_GROUP, "substeps", default_value=1)
        
        if not isinstance(self.substep_count, int) or self.substep_count == 0:
            self.substep_count = 1
        elif self.substep_count < 1:
            self.substep_count = abs(self.substep_count)

        if isinstance(steps, MeasurementSteps):
            self.series_start = self.steps.start
            self.series_definition = self.steps.series
        else:
            if isinstance(start, dict):
                self.series_start = start
            else:
                self.series_start = None
            
            if isinstance(series, dict):
                self.series_definition = series
            else:
                self.series_definition = None

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
                "relaxation-time"
            )
        except KeyError:
            self.relaxation_time = None
        
        if (not isinstance(self.relaxation_time, (int, float)) or 
            self.relaxation_time < 0):
            self.relaxation_time = 0
        
        log_debug(self._logger, ("Setting relaxation time to " + 
                                 "'{}'").format(self.relaxation_time))

        self.current_image = None
        self.running = False
        self.finished = False
        self.measurement_logging = True
        self._image_save_threads = []

        # stop the measurement when the emergency event is fired
        log_debug(self._logger, "Adding stop() function call to emergency " + 
                                "event")
        self.stop_event_id = "measurement_stop"
        emergency[self.stop_event_id] = self.stop

        # the index in the steps that is currently being measured
        self.step_index = -1
        self.current_step = None
    
    def formatName(self, name_format: typing.Optional[str]=None) -> str:
        """Return the name for the current measurement step

        Parameters
        ----------
        name_format : str, optional
            The name to use, if not given the `Measurement.name_format` is used
        
        Returns
        -------
        str
            The formatted file name for the current measurement step
        """

        if not isinstance(name_format, str):
            name_format = self.name_format
        
        name, *_ = expand_vars(name_format, controller=self.controller, 
                               step=self.current_step, 
                               start=self.series_start, 
                               series=self.series_definition, 
                               tags=self.tags, counter=self.step_index)
        log_debug(self._logger, "Formatting name to '{}'".format(name))
        return name
    
    def _setSafe(self, force: typing.Optional[bool]=True, 
                 output: typing.Optional[bool]=False) -> typing.List[ExceptionThread]:
        """Set the microscope and the camera to be in safe state.
        
        Parameters
        ----------
        force : bool, optional
            Whether to force setting to the safe state (True) or to check, if 
            the microscope and/or camera should be set to the safe state after
            the measurement (False)
        output : bool, optional
            Whether to print a message to the view when the resetting process
            is running
        
        Returns
        -------
        list of ExceptionThreads
            The list of started threads that are currently setting the hardware
            devices to the safe state or an empty list if there is nothing to 
            do
        """

        log_debug(self._logger, "Setting micorsocpe and camera to safe state",
                               exc_info=True)
        
        reset_threads = []

        if force or self.microscope_safe_after:
            thread_name = "reset microscope to safe state"
            log_debug(self._logger, ("Setting microscope to safe state " + 
                                     "in thread '{}'").format(thread_name))
            thread = ExceptionThread(
                target=self.controller.microscope.resetToSafeState,
                name=thread_name
            )
            thread.start()
            reset_threads.append(thread)

            if output:
                self.controller.view.print("Setting microscope to safe state...")
        
        if force or self.camera_safe_after:
            thread_name = "reset camera to safe state"
            log_debug(self._logger, ("Setting microscope to safe state " + 
                                     "in thread '{}'").format(thread_name))
            thread = ExceptionThread(
                target=self.controller.camera.resetToSafeState,
                name=thread_name
            )
            thread.start()
            reset_threads.append(thread)

            if output:
                self.controller.view.print("Setting camera to safe state...")
        
        return reset_threads
    
    def start(self) -> None:
        """Start the measurement.
        
        Fired Events
        ------------
        microscope_ready
            Fired when the microscope is in lorentz mode the measurement is 
            right about starting
        before_approach
            Fired before approaching the next measurement point
        before_record
            Fired after the measurements points values are reached but before
            recording the image
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

            if not self.running:
                log_debug(self._logger, ("Stopping measurement because running " + 
                                         "is now '{}'").format(self.running))
                # stop() is called
                return
            
            # trigger microscope ready event
            log_debug(self._logger, "Firing 'microscope_ready' event")
            microscope_ready(self.controller)
            self.controller.view.print("Done.")

            last_step = None
            for self.step_index, self.current_step in enumerate(self.steps):
                # start going through steps
                log_debug(self._logger, "Starting step '{}': '{}'".format(
                                        self.step_index, self.current_step))

                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return

                # check all thread exceptions
                self.raiseThreadErrors()
                
                # fire event before approaching
                log_debug(self._logger, "Firing 'before_approach' event")
                before_approach(self.controller)

                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return

                if self.measurement_logging:
                    # add the values to reach to the current log
                    self.addToMeasurementLog(self.current_step, 
                        "Targetting values", "", 
                        datetime.datetime.now().isoformat())

                step_descr = ", ".join(["{}: {}".format(k, v) for k, v in self.current_step.items()])  
                self.controller.view.print("Approaching step {}: {}.".format(
                    self.step_index, step_descr
                ))

                for i in range(self.substep_count):
                    # the asynchronous threads to set the values at the micrsocope
                    measurement_variable_threads = []

                    for variable_name in self.current_step:
                        if (isinstance(last_step, dict) and
                            variable_name in last_step):
                            if (last_step[variable_name] == self.current_step[variable_name] or
                                (isinstance(last_step[variable_name], float) and
                                 isinstance(self.current_step[variable_name], float) and
                                 math.isclose(last_step[variable_name], 
                                              self.current_step[variable_name]))):
                                log_debug(self._logger, ("Skipping '{}', the " + 
                                                         "last value is the " + 
                                                         "same as the current " + 
                                                         "one.").format(
                                                            variable_name))
                                continue
                                
                            approach_value = (last_step[variable_name] + 
                                              (self.current_step[variable_name] - 
                                              last_step[variable_name]) / 
                                              self.substep_count * (i + 1))
                        else:
                            approach_value = self.current_step[variable_name]
                        
                        log_debug(self._logger, ("Setting variable '{}' of " + 
                                                 "step to value '{}'").format(
                                                    variable_name,
                                                    approach_value))
                        # set each measurement variable
                        if not self.running:
                            log_debug(self._logger, ("Stopping measurement " + 
                                                     "because running is " + 
                                                     "now '{}'").format(self.running))
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
                                args=(variable_name, approach_value),
                                name="microscope variable {} in step {}".format(
                                    variable_name, self.step_index
                                )
                            )
                            log_debug(self._logger, "Starting variable setting " + 
                                                "thread")
                            thread.start()
                            measurement_variable_threads.append(thread)
                        else:
                            # set measurement variables sequential
                            self.controller.microscope.setMeasurementVariableValue(
                                variable_name, approach_value)
                
                    log_debug(self._logger, ("Waiting for '{}' variable setting " + 
                                            "threads").format(len(measurement_variable_threads)))
                    # Wait for all measurement variable threads to finish
                    for thread in measurement_variable_threads:
                        thread.join()
                    
                    if not isinstance(last_step, dict):
                        break
                        
                    if (isinstance(self.relaxation_time, (int, float)) and 
                        self.relaxation_time > 0):
                        wait_time = self.relaxation_time / 2 / self.substep_count
                        text = ("Waiting relaxation time of '{}'/2/'{}'='{}' " + 
                                "seconds").format(self.relaxation_time, 
                                                  self.substep_count, 
                                                  wait_time)
                        log_info(self._logger, text)
                        self.controller.view.print(text)
                        start_time = time.time()

                        while time.time() - start_time < wait_time:
                            # allow calling stop() function while waiting
                            time.sleep(0.01)

                            if not self.running:
                                # stop() is called
                                return
                        
                        log_debug(self._logger, ("Continuing with measurement at " + 
                                                 "time '{:%Y-%m-%d %H:%M:%S,%f}'").format(datetime.datetime.now()))
        
                if (isinstance(self.relaxation_time, (int, float)) and 
                    self.relaxation_time > 0):
                    text = "Waiting relaxation time of '{}'/2 seconds".format(self.relaxation_time)
                    log_info(self._logger, text)
                    self.controller.view.print(text)
                    start_time = time.time()

                    while time.time() - start_time < self.relaxation_time / 2:
                        # allow calling stop() function while waiting
                        time.sleep(0.01)

                        if not self.running:
                            # stop() is called
                            return
                    
                    log_debug(self._logger, ("Continuing with measurement at " + 
                                             "time '{:%Y-%m-%d %H:%M:%S,%f}'").format(datetime.datetime.now()))
                
                log_debug(self._logger, "Receiving values from microscope and " + 
                                        "writing it to the current_step")
                # get the actual values
                for variable_name in self.current_step:
                    self.current_step[variable_name] = (
                        self.controller.microscope.getMeasurementVariableValue(variable_name)
                    )
                
                log_debug(self._logger, "Got values '{}' from microscope".format(
                                        self.current_step))
                
                # check all thread exceptions
                self.raiseThreadErrors(*measurement_variable_threads)
                
                info = "{{varname[{v}]}}: {{humanstep[{v}]}} {{varunit[{v}]}}"
                info = human_concat_list(map(lambda v: info.format(v=v),
                                             self.current_step.keys()), 
                                             surround="", word=" and ")
                info, *_ = expand_vars(("Reached point {counter} with values " + 
                                        info), controller=self.controller, 
                                        step=self.current_step, 
                                        counter=self.step_index)
                log_info(self._logger, info)
                self.controller.view.print("Done.", inset="  ")
                
                # fire event before recording
                log_debug(self._logger, "Firing 'before_record' event")
                before_record(self.controller)
                
                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                             "running is now '{}'").format(self.running))
                    # stop() is called
                    return

                log_debug(self._logger, "Recording image")
                
                self.controller.view.print("Recording image...", inset="  ")
                # record measurement, add the real values to the image
                self.current_image = self.controller.camera.recordImage(
                    self.createTagsDict(self.current_step), 
                    step=self.current_step, 
                    series=self.series_definition, start=self.series_start, 
                    counter=self.step_index)
                
                name = self.formatName()
                
                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return
                
                if self.measurement_logging:
                    # add the real values to the log
                    self.addToMeasurementLog(self.current_step, 
                                             "Recording image", name, 
                                             datetime.datetime.now().isoformat())
                
                if not self.running:
                    log_debug(self._logger, ("Stopping measurement because " + 
                                            "running is now '{}'").format(self.running))
                    # stop() is called
                    return
                
                # fire event after recording but before saving
                log_debug(self._logger, "Firing 'after_record' event")
                after_record(self.controller)

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

                log_debug(self._logger, "Increasing progress to '{}'".format(self.step_index + 1))
                
                self.controller.view.progress = self.step_index + 1
                last_step = copy.deepcopy(self.current_step)

            self.step_index = -1
            self.current_step = None
            log_debug(self._logger, "Done with all steps")
            
            self.controller.view.print("Done with measurement.")

            # reset microscope and camera to a safe state so there is no need
            # for the operator to come back very quickly, do this while waiting
            # for the save threads to finish
            reset_threads = self._setSafe(False, True)

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

            log_debug(self._logger, "Setting 'finished' to True")
            self.finished = True

            log_debug(self._logger, "Firing 'measurement_ready' event")
            measurement_ready(self.controller)
        except StopProgram as e:
            log_debug(self._logger, "Stopping program", exc_info=e)
            self.stop()
            raise e
        except BlockedFunctionError as e:
            # stop if any error occurres, just to be sure
            log_error(self._logger, e)
            self.stop()
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
                        log_error(self._logger, error)
                        raise error
        
        log_debug(self._logger, "Done with waiting")
    
    def stop(self, *args) -> None:
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
        reset_threads = self._setSafe(False, True)

        if isinstance(self._measurement_log_thread, LogThread):
            log_debug(self._logger, "Stopping measurement log thread")
            self._measurement_log_thread.stop()
        
        # wait for reset threads if there are threads to wait for
        for thread in reset_threads:
            thread.join()
        
        # raise error if there occurred some
        self.raiseThreadErrors(*reset_threads)

        # fire stop event
        log_debug(self._logger, "Firing 'after_stop' event")
        after_stop(self.controller)
    
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

                    if not isinstance(error, BlockedFunctionError):
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

        beautified_step = []
        for var_id in step.keys():
            var = self.controller.microscope.getMeasurementVariableById(var_id)

            if var.has_calibration and var.calibrated_name is not None:
                name = str(var.calibrated_name)
            else:
                name = str(var.name)

            if var.has_calibration and var.calibrated_unit is not None:
                name += " (in {})".format(var.calibrated_unit)
            elif var.unit is not None:
                name += " (in {})".format(var.unit)
            
            beautified_step.append("{{varname[{id}]}}{{? (in {{varunit[{id}]}})?}}".format(
                                   id=var.unique_id))
            beautified_step.append("{{humanstep[{}]}}".format(var.unique_id))
        
        beautified_step = expand_vars(*beautified_step, 
                                      controller=self.controller, step=step,
                                      start=self.series_start, 
                                      series=self.series_definition,
                                      tags=self.tags, counter=self.step_index)
        beautified_step = dict(zip(beautified_step[0::2], beautified_step[1::2]))

        tags = {
            "Measurement Values": {
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
            CONFIG_MEASUREMENT_GROUP, "relaxation-time", 
            datatype=float, 
            default_value=DEFAULT_RELAXATION_TIME, 
            description="The relaxation time in seconds to wait after the " + 
            "microscope has reached all the measurement variable values."
        )
        
        # break steps into sub steps
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "substeps", 
            datatype=Datatype.int, 
            default_value=1, 
            description="For setting values 'parallel' and 'continously' the " + 
                        "step width of each step can be divided by the number " + 
                        "of 'supsteps'. This means that if two measurement " + 
                        "variables should be set, each of their step widths " + 
                        "are divided by this number. Then both alternating are " + 
                        "increased or decreased by this small step width " + 
                        "value. This way this emulates continously and " + 
                        "parallel setting of the measurement values."
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
            description=("The name format to use to save the recorded " + 
                         "images. " + get_expand_vars_text())
        )
        
        # add the save path for the log
        configuration.addConfigurationOption(
            CONFIG_MEASUREMENT_GROUP, "log-save-path",
            datatype=Datatype.filepath,
            default_value=DEFAULT_LOG_PATH,
            description=("The file path (including the file name) to save " + 
            "log to.")
        )