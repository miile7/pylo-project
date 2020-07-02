import threading
import importlib
import typing
import os

from .microscopes.microscope_interface import MicroscopeInterface
from .camera_interface import CameraInterface
from .abstract_configuration import Savable
from .stop_program import StopProgram
from .measurement import Measurement
from .events import series_ready
from .events import init_ready
from .events import user_ready
from .config import CONFIGURATION
from .config import PROGRAM_NAME
from .config import VIEW

CONFIG_SETUP_GROUP = "setup"

class Controller:
    """This is the controller for the pylo program.

    This object contains all the other objects and is the main entry point for 
    the program.

    Attributes
    ----------
    view : AbstractView
        The view
    microscope : MicroscopeInterface
        The microscope that is used for measuring
    configuration : AbstractConfiguration
        The configuration
    camera : CameraInterface
        The camera that is used for receiving the images
    measurement : Measurement or None
        The measurement to do
    """

    def __init__(self):
        self.configuration = CONFIGURATION
        self.view = VIEW

        Controller.defineConfigurationOptions(self.configuration)
        Measurement.defineConfigurationOptions(self.configuration)

        self.microscope = None
        self.camera = None
        self.measurement = None
        self._measurement_thread = None
    
    def _dynamicCreateClass(self, config_key_module: str, config_key_class: str, 
                              module_options: typing.Optional[typing.Collection]=None, 
                              class_options: typing.Optional[typing.Collection]=None,
                              constructor_args: typing.Optional[typing.Collection]=None) -> typing.Any:
        """Dynamically create the an object of the given module and class where
        the module and class are loaded form the config.

        If the config does not contain the keys or there are not the values 
        given, the module and class are asked from the user.

        Raises
        ------
        ModuleNotFoundError
            When the `module_name` is not a valid module
        AttributeError
            When the `class_name` does not exist in the given module
        NameError
            When the `class_name` exists in the module but is not a class

        Parameters
        ----------
        config_key_module : str
            The key name in the configuration of the module to load the object 
            from
        config_key_class : str
            The key name in the configuration of the class
        module_options : Collection, optional
            The options of the modules to show to the user if the key is not 
            given
        class_options : Collection, optional
            The options of the classes to show to the user if the key is not 
            given
        constructor_args : tuple, optional
            The arguments to pass to the constructor
        
        Returns
        -------
            The object of the class in the module
        """

        module_name, class_name = self.getConfigurationValuesOrAsk(
            ((CONFIG_SETUP_GROUP, config_key_module, module_options),
             (CONFIG_SETUP_GROUP, config_key_class, class_options))
        )

        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)

        if isinstance(constructor_args, typing.Collection):
            return class_(*constructor_args)
        else:
            return class_()
    
    def getConfigurationValuesOrAsk(self, *config_lookup: typing.List[typing.Union[str, typing.Optional[typing.Collection]]]) -> typing.Tuple[Savable]:
        """Get the configuration values or ask for them if they are not given.

        Parameters
        ----------
        tuple : 
            A tuple with the group at index 0, the key at index 1 and optional
            the allowed options at index 2
        """

        # the values to return
        values = {}
        # the values to ask
        input_params = {}

        for i, (group, key, *_) in enumerate(config_lookup):
            try:
                values[i] = self.configuration.getValue(group, key)
            except KeyError:
                # set the name to ask for
                input_param = {"name": "{} ({})".format(key, group)}

                try:
                    # try to get a description for the user asking
                    input_param["description"] = self.configuration.getDescription(
                        group, key
                    )
                except KeyError:
                    pass
                
                try:
                    # try to get the datatype
                    input_param["datatype"] = self.configuration.getDatatype(
                        group, key
                    )
                except KeyError:
                    input_param["datatype"] = str
                
                if len(_) > 0 and isinstance(_[0], typing.Iterable):
                    # check if there are options for this ask
                    input_param["options"] = list(_[0])
                
                # save the index and the ask parameters
                input_params[i] = input_param
        
        # check if there are values to ask for
        if len(input_params) > 0:
            # save the results of the user
            results = self.view.askFor(list(input_params.values()))
            # check where the results should be saved in
            target_keys = list(input_params.keys())

            for i, result in enumerate(results):
                # replace the missing value with the asked result
                values[target_keys[i]] = result
        
        return tuple(values.values())
    
    def startProgramLoop(self) -> None:
        """Start the program loop.
        
        Fired Events
        ------------
        init_ready
            Fired after the initializiation is done
        """

        # the default microscope options
        default_module_path = os.path.join(os.path.dirname(__file__), 
                                           "microscopes")
        modules = filter(lambda x: (x.endswith(".py") and
                                    x != "microscope_interface.py" and 
                                    x != "__init__.py"), 
                        os.listdir(default_module_path))

        self.microscope = None
        while not isinstance(self.microscope, MicroscopeInterface):
            try:
                # get the microscope from the config or from the user
                self.microscope = self._dynamicCreateClass("microscope-module", 
                                                        "microscope-class",
                                                        modules)
            except ModuleNotFoundError:
                self.view.showError("The microscope module could not be " + 
                                    "found.")
                self.microscope = None
            except (AttributeError, NameError):
                self.view.showError("The microscope module does define " + 
                                    "the given microscope class.")
                self.microscope = None
            except StopProgram:
                self.stopProgramLoop()
                return

        self.camera = None
        while not isinstance(self.camera, CameraInterface):
            try:
                # get the camera form the config or form the user
                self.camera = self._dynamicCreateClass("camera-module", "camera-class")
            except ModuleNotFoundError:
                self.view.showError("The camera module could not be " + 
                                    "found.")
                self.camera = None
            except (AttributeError, NameError):
                self.view.showError("The camera module does define " + 
                                    "the given camera class.")
                self.camera = None
            except StopProgram:
                self.stopProgramLoop()
                return
        
        self.measurement = None

        # fire init_ready event
        init_ready()

        # build the view
        measurement_layout = None
        while (not isinstance(measurement_layout, typing.Collection) or 
               len(measurement_layout) <= 1):
            try:
                measurement_layout = self.view.showCreateMeasurement()
            except StopProgram:
                self.stopProgramLoop()
                return
            
            if(not isinstance(measurement_layout, typing.Collection) or 
               len(measurement_layout) <= 1):
                self.view.showError("The measurement layout contains errors.")
        
        # fire user_ready event
        user_ready()

        self.measurement = Measurement.fromSeries(self, 
                                                  measurement_layout[0], 
                                                  measurement_layout[1])
        
        # fire series_ready event
        series_ready()

        self._measurement_thread = threading.Thread(
            target=self.measurement.start
        )
    
    def stopProgramLoop(self) -> None:
        """Stop the program loop.

        This funciton will also wait for all threads to join.
        """

        if isinstance(self.measurement, Measurement) and self.measurement.running:
            self.measurement.stop()

            if isinstance(self._measurement_thread, threading.Thread):
                self._measurement_thread.join()
            
            self.measurement.waitForAllImageSavings()
    
    def restartProgramLoop(self):
        """Stop and restart the program loop."""
        self.stopProgramLoop()
        return self.startProgramLoop()
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration"):
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        """
        
        # add the option for the microscope module
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, "microscope-module", str, description=("The " + 
            "module name where the microscope to use is defined. This must " + 
            "be a valid python module name relative to the {name} root. So " + 
            "if you are outside {name}, you should type pylo<your input>" + 
            "(usually including the first dot). For example use " + 
            ".microscopes.my_custom_microscope. (The file is then " + 
            "pylo/microscopes/my_custom_microscope.py)").format(name=PROGRAM_NAME),
            restart_required=True
        )
        # the configuration option for the microscope class
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, "microscope-class", str, description=("The " + 
            "class name of the microscope class that communicates with the " + 
            "physical microscope. The class name must be in the " + 
            "'microscope-module'."), restart_required=True
        )
        # add the option for the camera module
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, "camera-module", str, description=("The " + 
            "camera name where the camera to use is defined. This must " + 
            "be a valid python module name relative to the {name} root. So " + 
            "if you are outside {name}, you should type pylo<your input>" + 
            "(usually including the first dot). For example use " + 
            ".my_custom_camera. (The file is then " + 
            "pylo/my_custom_camera.py)").format(name=PROGRAM_NAME),
            restart_required=True
        )
        # the configuration option for the camera class
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, "camera-class", str, description=("The " + 
            "class name of the camera class that communicates with the " + 
            "physical camera. The class name must be in the " + 
            "'camera-module'."), restart_required=True
        )