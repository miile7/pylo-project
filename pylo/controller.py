import importlib
import threading
import inspect
import typing
import sys
import os

from .microscopes.microscope_interface import MicroscopeInterface
from .camera_interface import CameraInterface
from .exception_thread import ExceptionThread
from .stop_program import StopProgram
from .measurement import Measurement
from .events import before_start
from .events import series_ready
from .events import before_init
from .events import init_ready
from .events import user_ready
from .config import PROGRAM_NAME
# from .config import CONFIGURATION
# from .config import VIEW

MAX_LOOP_COUNT = 1000

# for importing with import_lib in Controller::_dynamicCreateClass()
# add pylo/root
sys.path.append(os.path.dirname(__file__))
# add microscopes path
sys.path.append(os.path.join(os.path.dirname(__file__), "microscopes"))
# add current working directory
sys.path.append(os.getcwd())

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

    def __init__(self) -> None:
        """Create the controller object.

        Fired Events
        ------------
        before_start
            Fired right after the function is called, nothing is set up
        """

        before_start()

        # import values here, otherwise they cannot be changed dynamically
        # which is (only?) required for the tests
        from .config import CONFIGURATION
        from .config import VIEW

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
                              constructor_args: typing.Optional[typing.Collection]=None) -> object:
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
        NameError, TypeError
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
            (CONFIG_SETUP_GROUP, config_key_module, module_options),
            (CONFIG_SETUP_GROUP, config_key_class, class_options)
        )

        extensions = (".py", ".py3", ".pyd", ".pyc", ".pyo", ".pyw", ".pyx",
                      ".pxd", ".pxi", ".pyi", ".pyz", ".pywz")
        for ext in extensions:
            if module_name.endswith(ext):
                module_name = module_name[:-1*len(ext)]

        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)

        if isinstance(constructor_args, typing.Collection):
            return class_(*constructor_args)
        else:
            return class_()
    
    def getConfigurationValuesOrAsk(self, *config_lookup: typing.List[typing.Union[typing.Tuple[str, str], typing.Tuple[str, str, typing.Iterable]]],
                                    save_if_not_exists: typing.Optional[bool]=True,
                                    fallback_default: typing.Optional[bool]=False) -> typing.Tuple[typing.Union[str, int, float, bool, None]]:
        """Get the configuration values or ask for them if they are not given.

        If the user is asked for the value, the value will be saved for the 
        given group and key in the configuration, if the `safe_if_not_exists`
        is not False.

        Note that if the configuration returns None, this is interpreted as a 
        missing value. Also if the default is None.

        Parameters
        ----------
        config_lookup : list of tuples
            Each tuple defines one configuration value to loop up, the index 0
            is the group, the index 1 is the key. Index 2 is optional and can
            hold options to show to the user if the configuration value is not 
            defined
        save_if_not_exists : bool
            Whether to save the value if it was asked for and does not exist in
            the configuration, default: True
        
        Returns
        -------
        tuple
            A tuple with the length of the `config_lookup`, for each lookup the 
            value will be returned
        """

        # the values to return
        values = []
        # the values to ask
        input_params = {}

        for i, (group, key, *_) in enumerate(config_lookup):
            try:
                val = self.configuration.getValue(group, key, fallback_default=fallback_default)
            except KeyError:
                val = None
            
            values.append(val)

            if val is None:
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
            results = self.view.askFor(*list(input_params.values()))
            # check where the results should be saved in
            target_keys = list(input_params.keys())

            for i, result in enumerate(results):
                # the index in the result to return and in the parameter list
                original_index = target_keys[i]
                # replace the missing value with the asked result
                values[original_index] = result

                if save_if_not_exists:
                    # save the asked value in the configuration
                    self.configuration.setValue(
                        config_lookup[original_index][0],
                        config_lookup[original_index][1],
                        result
                    )

        
        return tuple(values)
    
    def startProgramLoop(self) -> None:
        """Start the program loop.
        
        Fired Events
        ------------
        before_init
            Fired right after the function start, before everything is 
            initialize
        init_ready
            Fired after the initializiation is done
        """

        try:
            before_init()

            # the default microscope options
            default_module_path = os.path.join(os.path.dirname(__file__), 
                                            "microscopes")
            modules = filter(lambda x: (x.endswith(".py") and
                                        x != "microscope_interface.py" and 
                                        x != "__init__.py"), 
                            os.listdir(default_module_path))

            # prevent infinite loop
            security_counter = 0
            self.microscope = None
            while (not isinstance(self.microscope, MicroscopeInterface) and 
                security_counter < MAX_LOOP_COUNT):
                security_counter += 1
                try:
                    # get the microscope from the config or from the user
                    self.microscope = self._dynamicCreateClass("microscope-module", 
                                                            "microscope-class",
                                                            modules)
                except (ModuleNotFoundError, AttributeError, NameError, TypeError) as e:
                    if isinstance(e, ModuleNotFoundError):
                        msg = "The microscope module could not be found: {}"
                        fix = ("Change the 'microscope-module' in the '{}' group " + 
                            "in the configuration or type in a valid value. " + 
                            "The value can either be a python file or a python " + 
                            "module. Place that file in the current directory " + 
                            "where the script is executed or in the " + 
                            "'microscopes' directory in the {} directory " + 
                            "({}).").format(CONFIG_SETUP_GROUP, 
                                    os.path.basename(os.path.dirname(__file__)),
                                    os.path.dirname(__file__))
                        key = "microscope-module"
                    else:
                        msg = ("The microscope module could be loaded but the " + 
                            "given microscope class either does not exist or " + 
                            "is not a class: {}")
                        fix = ("Change the 'microscope-class' in the '{}' group " + 
                            "in the configuration or type in a valid value. " + 
                            "The value has to be the name of the class that " + 
                            "defines the microscope class. The microscope " + 
                            "class has to extend the class " + 
                            "'pylo.microscopes.MicroscopeInterface'.").format(CONFIG_SETUP_GROUP)
                        key = "microscope-class"
                    self.view.showError(msg.format(e), fix)
                    self.microscope = None
                    # remove the saved value, this either does not exist or is
                    # wrong, in both cases the user will be asked in the next run
                    if self.configuration.keyExists(CONFIG_SETUP_GROUP, key):
                        self.configuration.removeValue(CONFIG_SETUP_GROUP, key)
            
            # show an error that the max loop count is reached and stop the
            # execution
            if security_counter + 1 >= MAX_LOOP_COUNT:
                self.view.showError(("The program is probably trapped in an " + 
                                    "infinite loop when trying to get the " + 
                                    "microsocpe. The execution will be stopped now " + 
                                    "after {} iterations.").format(security_counter),
                                    "This is a bigger issue. Look in the code " + 
                                    "and debug the 'pylo/controller.py' file.")
                return

            # prevent infinite loop
            security_counter = 0
            self.camera = None
            while (not isinstance(self.camera, CameraInterface) and 
                security_counter < MAX_LOOP_COUNT):
                security_counter += 1
                try:
                    # get the camera form the config or form the user
                    self.camera = self._dynamicCreateClass("camera-module", "camera-class")
                except (ModuleNotFoundError, AttributeError, NameError, TypeError) as e:
                    if isinstance(e, ModuleNotFoundError):
                        msg = "The camera module could not be found: {}"
                        fix = ("Change the 'camera-module' in the '{}' group " + 
                            "in the configuration or type in a valid value. " + 
                            "The value can either be a python file or a python " + 
                            "module. Place that file in the current directory " + 
                            "where the script is executed or in in the {} " + 
                            "directory ({}).").format(CONFIG_SETUP_GROUP, 
                                    os.path.basename(os.path.dirname(__file__)),
                                    os.path.dirname(__file__))
                        key = "camera-module"
                    else:
                        msg = ("The camera module could be loaded but the " + 
                            "given camera class either does not exist or " + 
                            "is not a class: {}")
                        fix = ("Change the 'camera-class' in the '{}' group " + 
                            "in the configuration or type in a valid value. " + 
                            "The value has to be the name of the class that " + 
                            "defines the camera class. The camera " + 
                            "class has to extend the class " + 
                            "'pylo.CameraInterface'.").format(CONFIG_SETUP_GROUP)
                        key = "camera-class"
                    self.view.showError(msg.format(e), fix)
                    self.camera = None
                    # remove the saved value, this either does not exist or is
                    # wrong, in both cases the user will be asked in the next run
                    if self.configuration.keyExists(CONFIG_SETUP_GROUP, key):
                        self.configuration.removeValue(CONFIG_SETUP_GROUP, key)

            # show an error that the max loop count is reached and stop the
            # execution
            if security_counter + 1 >= MAX_LOOP_COUNT:
                self.view.showError(("The program is probably trapped in an " + 
                                    "infinite loop when trying to get the " + 
                                    "camera. The execution will be stopped now " + 
                                    "after {} iterations.").format(security_counter),
                                    "This is a bigger issue. Look in the code " + 
                                    "and debug the 'pylo/controller.py' file.")
                return
            
            self.measurement = None

            # fire init_ready event
            init_ready()

            # prevent infinite loop
            security_counter = 0
            # build the view
            measurement_layout = None
            while (not isinstance(self.measurement, Measurement) and 
                security_counter < MAX_LOOP_COUNT):
                security_counter += 1
                
                measurement_layout = self.view.showCreateMeasurement()
                
                if(not isinstance(measurement_layout, typing.Collection) or 
                len(measurement_layout) <= 1):
                    self.view.showError("The view returned an invalid measurement.",
                                        "Try to input your measurement again, if " + 
                                        "it still doesn't work you have to debug " + 
                                        "your view in 'pylo/{}'.".format(
                                            inspect.getfile(self.view.__class__)))
            
                # fire user_ready event
                user_ready()

                try:
                    self.measurement = Measurement.fromSeries(self, 
                                                              measurement_layout[0], 
                                                              measurement_layout[1])
                except (KeyError, ValueError) as e:
                    self.view.showError("The measurement could not be initialized " + 
                                        "because it is not formatted correctly: " + 
                                        "{}".format(e),
                                        "Try again and make sure you entered a " + 
                                        "valid value for this.")

            # show an error that the max loop count is reached and stop the
            # execution
            if security_counter + 1 >= MAX_LOOP_COUNT:
                self.view.showError(("The program is probably trapped in an " + 
                                    "infinite loop when trying to initialize the " + 
                                    "measurement. The execution will be stopped now " + 
                                    "after {} iterations.").format(security_counter),
                                    "This is a bigger issue. Look in the code " + 
                                    "and debug the 'pylo/controller.py' file.")
                return
            
            # fire series_ready event
            series_ready()

            self._measurement_thread = ExceptionThread(
                target=self.measurement.start
            )
            self._measurement_thread.start()
            
        except StopProgram:
            self.stopProgramLoop()
            return
        except Exception as e:
            try:
                self.view.showError("An exception occurred: {}".format(e))
            except StopProgram:
                self.stopProgramLoop()
                return
    
    def waitForProgram(self, raise_error_when_not_started: typing.Optional[bool]=False) -> None:
        """Wait until the program has finished.

        Raises
        ------
        RuntimeError
            When `raise_error_when_not_started` is True and the 
            `Controller::startProgramLoop()` is not called before or the 
            program has already finished
        
        Parameters
        ----------
        raise_error_when_not_started : bool
            Whether to raise an error when this function is called but the 
            program loop is not started
        """

        if (isinstance(self._measurement_thread, threading.Thread) and 
            self._measurement_thread.is_alive()):
            try:
                self._measurement_thread.join()

                if len(self._measurement_thread.exceptions):
                    for error in self._measurement_thread.exceptions:
                        raise error
            except StopProgram:
                self.stopProgramLoop()
                return
            except Exception as e:
                try:
                    self.view.showError("An exception occurred: {}".format(e))
                except StopProgram:
                    self.stopProgramLoop()
                    return
        elif raise_error_when_not_started:
            raise RuntimeError("Cannot wait for the program if the program " + 
                               "is not started or has already finished.")
    
    def stopProgramLoop(self) -> None:
        """Stop the program loop.

        This funciton will also wait for all threads to join.
        """

        if isinstance(self.measurement, Measurement) and self.measurement.running:
            self.measurement.stop()

            if isinstance(self._measurement_thread, ExceptionThread):
                self._measurement_thread.join()
            
            self.measurement.waitForAllImageSavings()
    
    def restartProgramLoop(self) -> None:
        """Stop and restart the program loop."""
        self.stopProgramLoop()
        self.startProgramLoop()
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration") -> None:
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