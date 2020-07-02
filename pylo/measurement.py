import threading
import datetime
import typing
import os

import numpy as np

from collections import defaultdict

from .abstract_configuration import AbstractConfiguration
from .blocked_function_error import BlockedFunctionError
from .measurement_variable import MeasurementVariable
# from .controller import Controller
from .events import microscope_ready
from .events import measurement_ready
from .events import before_record
from .events import after_record
from .events import emergency
from .events import after_stop
from .image import Image

from .config import DEFAULT_SAVE_DIRECTORY
from .config import DEFAULT_SAVE_FILE_NAME

class Measurement:
    """This class represents one measurement.

    Attributes
    ----------
    tags : dict
        Any information that should be stored about this measurement
    steps : list of dicts
        A list of dicts where each dict contains **all** `MeasurementVariable`
        ids as the keys and the corresponding value in the
        `MeasurementVariable` specific unit
    controller : Controller
        The controller
    save_dir : str
        The absolute path of the directory where to save this measurement to
    name_format : str
        The file name how to save the images (including the extension, 
        supported are all the extensions provided by the `CameraInterface`),
        placeholders are supported and described in the formatName() function
    current_image : Image
        The last recorded image object
    running : bool
        Whether the measurement is running or not, to stop the measurement 
        immediately set this to False
        
    Listened Events
    ---------------
    emergency
        Stop the measurement if the event is fired
    """

    def __init__(self, controller: "Controller", steps: typing.List[dict]):
        self.controller = controller
        self.tags = {}
        self.steps = steps

        self.save_dir = self.controller.configuration.getValue(
            "measurement", "save-directory"
        )
        self.name_format = self.controller.configuration.getValue(
            "measurement", "save-file-format"
        )
        
        self.current_image = None
        self.running = False

        # stop the measurement when the emergency event is fired
        emergency.append(self.stop)

        # the index in the steps that is currently being measured
        self._step_index = -1
    
    def formatName(self, name_format: typing.Optional[str]=None, 
                   tags: typing.Optional[dict]=None,
                   variables: typing.Optional[dict]=None,
                   imgtags: typing.Optional[dict]=None,
                   time: typing.Optional[datetime.datetime]=None,
                   counter: typing.Optional[int]=None):
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
        
        return name_format.format_map(defaultdict(str, tags=tags, 
            variables=variables, var=variables, imgtags=imgtags, time=time,
            date=time, datetime=time, counter=counter, number=counter, 
            num=counter))
    
    def _setSafe(self):
        """Set the microscope and the camera to be in safe state and stop the 
        measurement."""

        try:
            self.controller.microscope.resetToEmergencyState()
        except BlockedFunctionError:
            # emergency event is called, microscope goes in emergency state by 
            # itself
            pass

        try:
            self.controller.camera.resetToEmergencyState()
        except BlockedFunctionError:
            # emergency event is called, camera goes in emergency state by 
            # itself
            pass
    
    def start(self) -> None:
        """Start the measurement.
        
        Fired Events
        ------------
        microscope_ready
            Fired when the microscope is in lorenz mode the measurement is 
            right about starting
        measurement_ready
            Fired when the measurement has fully finished
        before_record
            Fired before setting the microscope to the the next measurement 
            point
        after_record
            Fired after setting the microscope to measurement point and 
            recording an image but before saving the image to the directory
        """
        self.running = True
        self._image_save_threads = []

        try:
            # set to lorenz mode
            self.controller.microscope.setInLorenzMode(True)

            if not self.running:
                # stop() is called
                return
            
            # trigger microscope ready event
            microscope_ready()

            for self._step_index, step in enumerate(self.steps):
                # start going through steps
                if not self.running:
                    # stop() is called
                    return
                
                # fire event before recording
                before_record()

                # the asynchronous threads to set the values at the micrsocope
                measurement_variable_threads = []

                for variable_name in step:
                    # set each measurement variable
                    if not self.running:
                        # stop() is called
                        return
                    
                    if self.controller.microscope.supports_parallel_measurement_variable_setting:
                        # MicroscopeInterface.setMeasurementVariableValue() can
                        # set parallel
                        thread = threading.Thread(
                            target=self.controller.microscope.setMeasurementVariableValue,
                            args=(variable_name, step[variable_name])
                        )
                        thread.start()
                        measurement_variable_threads.append(thread)
                    else:
                        # set measurement variables sequential
                        self.controller.microscope.setMeasurementVariableValue(
                            variable_name, 
                            step[variable_name]
                        )
                
                # Wait for all measurement variable threads to finish
                for thread in measurement_variable_threads:
                    thread.join()
                
                if not self.running:
                    # stop() is called
                    return
                
                # record measurement
                self.current_image = self.controller.camera.recordImage()
                
                if not self.running:
                    # stop() is called
                    return
                
                # fire event after recording but before saving
                after_record()

                if not self.running:
                    # stop() is called, maybe by after_record() event handler
                    return
                
                name = self.formatName()
                # save the image parallel to working on
                thread = threading.Thread(
                    target=self.current_image.saveTo,
                    args=(os.path.join(self.save_dir, name), )
                )
                thread.start()
                self._image_save_threads.append(thread)
            
            reset_threads = []
            # reset microscope and camera to a safe state so there is no need
            # for the operator to come back very quickly, do this while waiting
            # for the save threads to finish
            thread = threading.Thread(target=self.controller.microscope.resetToSafeState)
            thread.start()
            reset_threads.append(thread)
            
            thread = threading.Thread(target=self.controller.camera.resetToSafeState)
            thread.start()
            reset_threads.append(thread)

            # wait for all saving threads to finish
            self.waitForAllImageSavings()

            # wait for all machine reset threads to finish
            for thread in reset_threads:
                thread.join()

            # reset everything to the state before measuring
            self.running = False
            self._step_index = -1
            measurement_ready()
        except Exception:
            # stop if any error occurres, just to be sure
            self.stop()
            raise
    
    def waitForAllImageSavings(self):
        """Wait until all threads where images are saved have finished."""
        for thread in self._image_save_threads:
            thread.join()
    
    def stop(self) -> None:
        """Stop the measurement. 
        
        Note that the current hardware action is still finished when it has 
        started already!

        Fired Events
        ------------
        after_stop
            Fired when this function is executed
        """

        self.running = False
        self._setSafe()

        # fire stop event
        after_stop()
    
    @classmethod
    def fromSeries(class_, controller: "Controller", start_conditions: dict, 
                   series: dict) -> "Measurement":
        """Create a measurement object.
        
        Create a measurement, start_conditions contains all 
        `MeasurementVariable`s defined with their values, the series is a dict 
        that has an 'variable', a 'start', a 'step-width' and an 'end' index, optional is the 
        'on-each-point' index which may contain another series dict (that will 
        do the series in this point)

        Raises
        ------
        KeyError
            When the "variable", "start", "end" or "step-width" indices are missing 
            in the series dicts
        ValueError
            When not all of the supported measurement variables are contained
            in either the start_conditions or the series
        ValueError
            When the "variable" index is not a valid `MeasurementVariable` id
        """

        steps = Measurement._parseSeries(controller, start_conditions, series)
        return Measurement(controller, steps)
    
    @staticmethod
    def _parseSeries(controller: "Controller", start_conditions: dict, 
                     series: dict) -> list:
        """Create the steps for the measurement by the given `start_conditions`
        and the `series`.

        """

        steps = []

        # check if all indices are present
        if ("start" not in series or 
            not isinstance(series["start"], (int, float))):
            raise KeyError(("The series does not contain a " + 
                                "'{}' index").format("start"))
        if ("end" not in series or 
            not isinstance(series["end"], (int, float))):
            raise KeyError(("The series does not contain a " + 
                                "'{}' index").format("end"))
        if ("step-width" not in series or 
            not isinstance(series["step-width"], (int, float))):
            raise KeyError(("The series does not contain a " + 
                                "'{}' index").format("step-width"))
        if "variable" not in series:
            raise KeyError(("The series does not contain a " + 
                                "'{}' index").format("variable"))
        
        # test if step is > 0
        if series["step-width"] <= 0:
            raise ValueError("The 'step-width' must be greater than 0.")
        
        series_variable = None
        for var in controller.microscope.supported_measurement_variables:
            if var.unique_id == series["variable"]:
                series_variable = var
            elif var.unique_id not in start_conditions:
                raise ValueError(("The measurement variable {} (id: {})"  + 
                                  "is neither contained in the " + 
                                  "start_conditions nor in the series. " + 
                                  "Cannot create a Measurement when some " + 
                                  "variables are not known.").format(var.name, 
                                                                     var.unique_id))

        if series_variable is None:
            raise ValueError(("The series variable {} is not a valid " + 
                              "measurement variable id.").format(series["variable"]))

        for v in np.arange(max(series_variable.min_value, series["start"]), 
                           min(series_variable.max_value, series["end"]) + 
                               series["step-width"],
                           series["step-width"]):
            step = start_conditions.copy()
            step[series["variable"]] = v

            if "on-each-step" in series:
                steps += Measurement._parseSeries(controller, step, 
                                                  series["on-each-step"])
            else:
                steps.append(step)
            
        return steps
    
    @staticmethod
    def defineConfigurationOptions(configuration: AbstractConfiguration):
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        """
        
        # add an entry to the config and ask the user if there is nothing
        # saved
        configuration.addConfigurationOption(
            "measurement", "save-directory", datatype=str, 
            default_value=DEFAULT_SAVE_DIRECTORY, ask_if_not_present=True,
            description="The directory where to save the camera images to " + 
            "that are recorded while measuring.")
        # add an entry to the config and ask the user if there is nothing
        # saved
        configuration.addConfigurationOption(
            "measurement", "save-file-format", datatype=str, 
            default_value=DEFAULT_SAVE_FILE_NAME, ask_if_not_present=True,
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
            "but use supported extensions only.")