import datetime
import asyncio
import typing
import os

from collections import defaultdict

from .config import DEFAULT_SAVE_DIRECTORY
from .config import DEFAULT_SAVE_FILE_NAME
from .measurement_variable import MeasurementVariable
from .image import Image
from .events import microscope_ready
from .events import measurement_ready
from .events import before_record
from .events import after_record
from .controller import Controller

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
    """

    def __init__(self, controller: Controller, steps: typing.List[dict]):
        self.controller = controller
        self.tags = {}
        self.steps = steps

        self.save_dir = DEFAULT_SAVE_DIRECTORY
        # add an entry to the config and ask the user if there is nothing
        # saved
        controller.configuration.addConfigurationOption(
            "measurement", "save-directory", datatype=str, 
            default_value=self.save_dir, ask_if_not_present=True,
            description="The directory where to save the camera images to " + 
            "that are recorded while measuring.")
        
        self.name_format = DEFAULT_SAVE_FILE_NAME
        # add an entry to the config and ask the user if there is nothing
        # saved
        controller.configuration.addConfigurationOption(
            "measurement", "save-file-format", datatype=str, 
            default_value=self.name_format, ask_if_not_present=True,
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
        
        self.current_image = None
        self.running = False

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

        self.controller.microscope.resetToEmergencyState()
        self.controller.camera.resetToEmergencyState()
    
    async def start(self) -> None:
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
        
        Listened Events
        ---------------
        stop, emergency
            Stop the async calls on the microscope and the camera if the stop
            event is fired
        """
        self.running = True

        try:
            # create async task
            task = asyncio.create_task(self.controller.microscope.setInLorenzMode())
            # add cancel to events
            emergency.append(task.cancel)
            stop.append(task.cancel)

            await task

            # remove references so the task and the event callbacks get removed
            # by the garbage collector
            emergency.remove(task.cancel)
            stop.remove(task.cancel)
            del task
        
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

                # the asynchronous tasks to set the values at the micrsocope
                tasks = []

                for variable_name in step:
                    # set each measurement variable
                    if not self.running:
                        # stop() is called
                        return
                    
                    # MicroscopeInterface.setMeasurementVariableValue() is 
                    # async so this is an future object
                    task = asyncio.create_task(
                        self.controller.microscope.setMeasurementVariableValue(
                            variable_name, step[variable_name]
                        )
                    )

                    # add cancel callback to emergency and stop event to stop 
                    # executing the async operation
                    emergency.append(task.cancel)
                    stop.append(task.cancel)
                    tasks.append(task)
                
                # wait until all the measurement vairables are set
                await asyncio.gather(*tasks)
                
                # remove the callback to let the garbage collector destroy the 
                # task
                for task in tasks:
                    emergency.remove(task.cancel)
                    stop.remove(task.cancel)
                    del task
                del tasks

                if not self.running:
                    # stop() is called
                    return
                
                # record measurement
                self.current_image = asyncio.run(self.controller.camera.recordImage())

                if not self.running:
                    # stop() is called
                    return
                
                # fire event after recording but before saving
                after_record()

                if not self.running:
                    # stop() is called, maybe by after_record() event handler
                    return
                
                name = self.formatName()
                self.current_image.saveTo(os.path.join(self.save_dir, name))
            
            # reset microscope and camera to a safe state so there is no need
            # for the operator to come back very quickly
            await asyncio.gather(
                self.controller.microscope.resetToSafeState(),
                self.controller.camera.resetToSafeState()
            )

            # reset everything to the state before measuring
            self.running = False
            self._step_index = -1
            measurement_ready()
        except Exception:
            # stop if any error occurres, just to be sure
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the measurement. 
        
        Note that the current hardware action is still finished when it has 
        started already!

        Fired Events
        ------------
        stop
            Fired when this function is executed
        """

        self.running = False
        self._setSafe()

        # fire stop event
        stop()
