import datetime
import typing
import os

import numpy as np
from collections import defaultdict

from .blocked_function_error import BlockedFunctionError
from .measurement_variable import MeasurementVariable
from .exception_thread import ExceptionThread
from .stop_program import StopProgram
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

    def __init__(self, controller: "Controller", steps: typing.List[dict]) -> None:
        self.controller = controller
        self.tags = {}
        self.steps = steps

        self.save_dir, self.name_format = self.controller.getConfigurationValuesOrAsk(
            ("measurement", "save-directory"),
            ("measurement", "save-file-format"),
            fallback_default=True
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
        
        return name_format.format_map(defaultdict(str, tags=tags, 
            variables=variables, var=variables, imgtags=imgtags, time=time,
            date=time, datetime=time, counter=counter, number=counter, 
            num=counter))
    
    def _setSafe(self) -> None:
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
        before_record
            Fired before setting the microscope to the the next measurement 
            point
        after_record
            Fired after setting the microscope to measurement point and 
            recording an image but before saving the image to the directory
        measurement_ready
            Fired when the measurement has fully finished
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
                        thread = ExceptionThread(
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
                    
                    if len(thread.exceptions):
                        for error in thread.exceptions:
                            raise error
                
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
                thread = ExceptionThread(
                    target=self.current_image.saveTo,
                    args=(os.path.join(self.save_dir, name), )
                )
                thread.start()
                self._image_save_threads.append(thread)
            
            reset_threads = []
            # reset microscope and camera to a safe state so there is no need
            # for the operator to come back very quickly, do this while waiting
            # for the save threads to finish
            thread = ExceptionThread(target=self.controller.microscope.resetToSafeState)
            thread.start()
            reset_threads.append(thread)
            
            thread = ExceptionThread(target=self.controller.camera.resetToSafeState)
            thread.start()
            reset_threads.append(thread)

            # wait for all saving threads to finish
            self.waitForAllImageSavings()

            # wait for all machine reset threads to finish
            for thread in reset_threads:
                thread.join()

                if len(thread.exceptions):
                    for error in thread.exceptions:
                        raise error

            # reset everything to the state before measuring
            self.running = False
            self._step_index = -1
            measurement_ready()
        except StopProgram:
            self.stop()
            return
        except Exception as e:
            # stop if any error occurres, just to be sure
            self.stop()
            raise e
    
    def waitForAllImageSavings(self) -> None:
        """Wait until all threads where images are saved have finished."""
        for thread in self._image_save_threads:
            thread.join()
            
            if len(thread.exceptions):
                for error in thread.exceptions:
                    raise error
    
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
        error_path : tuple, optional
            This is for internal use only. It holds the variable names of the 
            parent series if the current parse series is in the 'on-each-step'
            index of another series
        
        Returns
        -------
        Measurement
            The measurement that holds all the steps to perform defined 
            measurement
        """

        steps = Measurement._parseSeries(controller, start_conditions, series)
        return Measurement(controller, steps)
    
    @staticmethod
    def _parseSeries(controller: "Controller", start_conditions: dict, 
                     series: dict, error_path: typing.Optional[tuple]=None) -> list:
        """Create the steps for the measurement by the given `start_conditions`
        and the `series`.

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
        error_path : tuple, optional
            This is for internal use only. It holds the variable names of the 
            parent series if the current parse series is in the 'on-each-step'
            index of another series
        
        Returns
        -------
        list of dicts
            Returns the steps which is a list of dicts where each dict contains
            every `MeasurementVariable` id as the key its corresponding value.
            The full list represents the measurement defined by the 
            `start_condition` and the `series`.
        """

        steps = []
        if isinstance(error_path, (list, tuple)):
            error_str = "".join([" in 'on-each-step' of {}".format(p) 
                                  for p in error_path])
        else:
            error_str = ""

        # check type and keys of series
        for key, datatype in {"start": (int, float), "end": (int, float), 
                              "step-width": (int, float), "variable": str}.items():
            if key not in series:
                raise KeyError(("The series{} does not have a '{}' " + 
                                "index.").format(error_str, key))
            elif not isinstance(series[key], datatype):
                raise TypeError(("The series{} '{}' key has to be of type {} but " + 
                                 "it is {}.").format(
                                     error_str,
                                     key, 
                                     " or ".join(map(lambda x: "{}".format(x), 
                                        datatype))
                                        if isinstance(datatype, tuple) else datatype,
                                     type(series[key])))
        
        series_variable = None
        start_dict = {}
        # check and create start variables
        for var in controller.microscope.supported_measurement_variables:
            if var.unique_id == series["variable"]:
                series_variable = var
                # make sure also the measured variable is correct
                start_dict[var.unique_id] = series["start"]
            elif var.unique_id in start_conditions:
                # remove unnecessary keys
                start_dict[var.unique_id] = start_conditions[var.unique_id]
            else:
                raise KeyError(("The measurement variable {} (id: {}) "  + 
                                  "is neither contained in the " + 
                                  "start_conditions{} nor in the series{}. " + 
                                  "Cannot create a Measurement when some " + 
                                  "variables are not known.").format(
                                      error_str, error_str,
                                      var.name, var.unique_id))

            if not isinstance(start_dict[var.unique_id], (int, float)):
                raise TypeError(("The '{}' index in the start_conditions{} " + 
                                 "contains a {} but only int or float are " + 
                                 "supported.").format(
                                     error_str,
                                     var.unique_id, 
                                     type(start_dict[var.unique_id])))
            elif (start_dict[var.unique_id] < var.min_value or 
                  start_dict[var.unique_id] > var.max_value):
                raise ValueError(("The '{index}' index in the " + 
                                  "start_conditions{path} is out of bounds. " + 
                                  "The {index} has to be " + 
                                  "{min} <= {index} <= {max} but it is " + 
                                  "{val}.").format(
                                    path=error_str,
                                    index=var.unique_id, 
                                    min=series_variable.min_value,
                                    max=series_variable.max_value,
                                    val=start_dict[var.unique_id]
                                ))

        if series_variable is None:
            raise ValueError(("The variable '{}' in the series{} is not a " + 
                              "valid measurement variable id.").format(
                                  series["variable"], error_str))

        # test if step is > 0
        if series["step-width"] <= 0:
            raise ValueError(("The 'step-width' in the series{} must be "+ 
                              "greater than 0.").format(error_str))

        for index in ("start", "end"):
            if (series[index] < series_variable.min_value or 
                series[index] > series_variable.max_value):
                raise ValueError(("The '{index}' index in the series{path} is " + 
                                  "out of bounds. The {index} has to be " + 
                                  "{min} <= {index} <= {max} but it is " + 
                                  "{val}.").format(
                                      path=error_str,
                                      index=index, 
                                      min=series_variable.min_value,
                                      max=series_variable.max_value,
                                      val=series[index]
                                ))

        if isinstance(error_path, (tuple, list)):
            error_path = list(error_path)
        else:
            error_path = []
        
        error_path.append(series["variable"])

        for v in crange(series["start"], series["end"], series["step-width"]):
            step = start_dict.copy()
            step[series["variable"]] = v

            if "on-each-step" in series:
                
                steps += Measurement._parseSeries(controller, step, 
                                                  series["on-each-step"],
                                                  error_path)
            else:
                steps.append(step)
            
        return steps
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration") -> None:
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
    
def cust_range(*args, rtol=1e-05, atol=1e-08, include=[True, False]):
    """
    Combines numpy.arange and numpy.isclose to mimic
    open, half-open and closed intervals.
    Avoids also floating point rounding errors as with
    >>> numpy.arange(1, 1.3, 0.1)
    array([1. , 1.1, 1.2, 1.3])

    Taken from https://stackoverflow.com/a/57321916/5934316

    args: [start, ]stop, [step, ]
        as in numpy.arange
    rtol, atol: floats
        floating point tolerance as in numpy.isclose
    include: boolean list-like, length 2
        if start and end point are included
    """
    # process arguments
    if len(args) == 1:
        start = 0
        stop = args[0]
        step = 1
    elif len(args) == 2:
        start, stop = args
        step = 1
    elif len(args) == 3:
        start, stop, step = tuple(args)
    else:
        raise ValueError("There are too many or too fiew arugments given. " + 
                         "Use exactly 1, 2, or 3 arguments.")

    # determine number of segments
    n = (stop-start)/step + 1

    # do rounding for n
    if np.isclose(n, np.round(n), rtol=rtol, atol=atol):
        n = np.round(n)

    # correct for start/end is exluded
    if not include[0]:
        n -= 1
        start += step
    if not include[1]:
        n -= 1
        stop -= step

    return np.linspace(start, stop, int(n))

def crange(*args, **kwargs):
    """
    Create a range that includes the boundries.

    args: [start, ]stop, [step, ]
        as in numpy.arange
    rtol, atol: floats
        floating point tolerance as in numpy.isclose
    """
    return cust_range(*args, **kwargs, include=[True, True])

def orange(*args, **kwargs):
    """
    Create a numpy range.

    args: [start, ]stop, [step, ]
        as in numpy.arange
    rtol, atol: floats
        floating point tolerance as in numpy.isclose
    """
    return cust_range(*args, **kwargs, include=[True, False])