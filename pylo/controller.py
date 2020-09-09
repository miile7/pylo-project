import os
import sys
import inspect
import typing
import importlib
import threading

from .events import init_ready
from .events import user_ready
from .events import before_init
from .events import before_start
from .events import series_ready

from .measurement import Measurement
from .stop_program import StopProgram
from .abstract_view import AbstractView
from .exception_thread import ExceptionThread
from .cameras.camera_interface import CameraInterface
from .abstract_configuration import AbstractConfiguration
from .microscopes.microscope_interface import MicroscopeInterface

# from .config import PROGRAM_NAME
# from .config import CONFIGURATION
# from .config import VIEW

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

# the number of times the user is asked for the input, this is for avoiding
# infinite loops that are caused by any error
MAX_LOOP_COUNT = 1000

# for importing with import_lib in Controller::_dynamicCreateClass()
# add pylo/root, the key is the text to display in the help, the value will be
# added to the sys.path
import_dirs = {
    "root": os.path.dirname(__file__),
    "microscopes": os.path.join(os.path.dirname(__file__), "microscopes"),
    "cameras": os.path.join(os.path.dirname(__file__), "cameras"),
    "current working directory": os.getcwd()
}
for v in import_dirs.values():
    if not v in sys.path:
        sys.path.append(v)

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

    def __init__(self, view: typing.Optional[AbstractView]=None,
                 configuration: typing.Optional[AbstractConfiguration]=None) -> None:
        """Create the controller object.

        Parameters
        ----------
        view : AbstractView, optional
            The view object to use, if not given the `config.VIEW` will be used
            instead
        configuration : AbstractConfiguration, optional
            The configuration object to use, if not given the 
            `config.CONFIGURATION` will be used instead

        Fired Events
        ------------
        before_start
            Fired right after the function is called, nothing is set up
        """

        before_start()

        if not isinstance(view, AbstractView):
            # import as late as possible to allow changes by extensions
            from .config import VIEW
            self.view = VIEW
        else:
            self.view = view
        
        if not isinstance(configuration, AbstractConfiguration):
            # import as late as possible to allow changes by extensions
            from .config import CONFIGURATION
            self.configuration = CONFIGURATION
        else:
            self.configuration = configuration

        Controller.defineConfigurationOptions(self.configuration)
        Measurement.defineConfigurationOptions(self.configuration)

        self.microscope = None
        self.camera = None
        self.measurement = None
        self._measurement_thread = None
    
    def _dynamicCreateClass(self, class_: type, 
                            constructor_args: typing.Optional[typing.Sequence]=None) -> object:
        """Dynamically create the an object of the `class_`.

        Raises
        ------
        NameError, TypeError
            When the `class_` is not a class

        Parameters
        ----------
        class_ : str
            The class to create
        constructor_args : tuple, optional
            The arguments for the construtor
        
        Returns
        -------
            The object of the class in the module
        """
        
        if isinstance(constructor_args, typing.Sequence):
            return class_(*constructor_args)
        else:
            return class_()

    def _dynamicGetClasses(self, *class_config: typing.Union[typing.Tuple[str, str], 
                                                    typing.Tuple[str, str, typing.Sequence], 
                                                    typing.Tuple[str, str, typing.Sequence, typing.Sequence]]) -> type:
        """Dynamically get the class of the given module and class where the 
        module and class are loaded form the config.

        If the config does not contain the keys or there are not the values 
        given, the module and class are asked from the user.

        Raises
        ------
        ModuleNotFoundError
            When the module name saved in `config_key_module` is not a valid 
            module
        AttributeError
            When the class name saved in `class_options` does not exist in the 
            given module
        TypeError
            When the class name saved in `class_options` exists in the module 
            but is not a class

        Parameters
        ----------
        class_config : tuple
            The load class configuration with the 
            - index 0: key name in the configuration of the module to load from
            - index 1: key name in the configuration of the class to load
            - index 2 (optional): The options of the modules to show to the 
              user if the key is not given
            - index 3 (optional): The options of the classes to show to the 
              user if the key is not given
        
        Returns
        -------
        list
            The classes of each of the modules
        """

        args = []
        for module_key, class_key, *options in class_config:
            module_arg = [CONFIG_SETUP_GROUP, module_key]
            if len(options) > 0 and isinstance(options[0], typing.Sequence):
                module_arg.append(list(options[0]))
            module_arg = tuple(module_arg)

            class_arg = [CONFIG_SETUP_GROUP, class_key]
            if len(options) > 1 and isinstance(options[1], typing.Sequence):
                class_arg.append(list(options[1]))
            class_arg = tuple(class_arg)
            
            args.append(module_arg)
            args.append(class_arg)

        names = self.getConfigurationValuesOrAsk(*args)

        module_names = names[::2]
        class_names = names[1::2]
        classes = []
        extensions = (".py", ".py3", ".pyd", ".pyc", ".pyo", ".pyw", ".pyx",
                    ".pxd", ".pxi", ".pyi", ".pyz", ".pywz")
        
        for module_name, class_name in zip(module_names, class_names):
            for ext in extensions:
                if module_name.endswith(ext):
                    module_name = module_name[:-1*len(ext)]
            
            print("Controller._dynamicGetClass():", module_name, class_name, sys.path, "\n")

            module = importlib.import_module(module_name, "pylo")
            class_ = getattr(module, class_name)

            if not isinstance(class_, type):
                raise TypeError("The class '{}' is not a class.".format(class_))
                
            classes.append(class_)

        return classes
    
    def getConfigurationValuesOrAsk(self, *config_lookup: typing.List[typing.Union[typing.Tuple[str, str], typing.Tuple[str, str, typing.Iterable]]],
                                    save_if_not_exists: typing.Optional[bool]=True,
                                    fallback_default: typing.Optional[bool]=False) -> typing.Tuple[typing.Union[str, int, float, bool, None]]:
        """Get the configuration values or ask for them if they are not given.

        If the user is asked for the value, the value will be saved for the 
        given group and key in the configuration, if the `safe_if_not_exists`
        is not False.

        Note that if the configuration returns None, this is interpreted as a 
        missing value. Also if the default is None.

        Example:
        ```python
        v1, v2, v3 = controller.getConfigurationValuesOrAsk(
            ("configuration-group", "configuration-key-1"),
            ("configuration-group", "configuration-key-2"),
            ("configuration-group-2", "configuration-key"),
            save_if_not_exists=True, fallback_default=True
        )
        ```

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
                val = self.configuration.getValue(
                    group, key, fallback_default=fallback_default
                )
            except KeyError:
                val = None
            
            values.append(val)

            if val is None:
                if len(_) > 0 and isinstance(_[0], typing.Iterable):
                    # check if there are options for this ask
                    input_params[i] = (group, key, list(_[0]))
                else:
                    # save the index and the ask parameters
                    input_params[i] = (group, key)
        
        # ordering of dict.values() and dict.keys() changes between python
        # versions, this makes sure the order is the same
        params_values = []
        params_keys = []
        for k, v in input_params.items():
            params_values.append(v)
            params_keys.append(k)
        
        # check if there are values to ask for
        if len(input_params) > 0:
            # save the results of the user
            results = self.askForConfigValues(*params_values)

            for i, result in enumerate(results):
                # the index in the result to return and in the parameter list
                original_index = params_keys[i]
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
    
    def askIfNotPresentConfigurationOptions(self, ask_if_default: typing.Optional[bool]=False) -> None:
        """Ask all configuration options which have `ask_if_not_present=True` 
        but do not exist.

        If all options are present, this function does nothing.

        Parameters
        ----------
        ask_if_default : bool, optional
            If False all values that have `ask_if_not_present=True` and neither
            have a value nor a default will be asked, if True all values that 
            have `ask_if_not_present=True` and do not have a value will be 
            asked, the default value will not be checked in the second case
        """

        input_params = []

        for group, key in self.configuration.getGroupsAndKeys():
            if self.configuration.getAskIfNotPresent(group, key):
                try:
                    self.configuration.getValue(
                        group, key, fallback_default=not ask_if_default
                    )
                except KeyError:
                    input_params.append((group, key))
        
        if len(input_params) > 0:
            input_vals = self.askForConfigValues(*input_params)

            for i, (group, key) in enumerate(input_params):
                self.configuration.setValue(group, key, input_vals[i])
        
    def askForConfigValues(self, *values: typing.Union[typing.Tuple[str, str], typing.Tuple[str, str, typing.Sequence]]) -> tuple:
        """Ask for the configuration values.

        Execute the `AbstractView::askFor()` function on each entry of the 
        `values` list. The `values` list contains the configuration group
        at index 0 and the key at index 1. This function will try to get 
        the description and datatype.

        Parameters
        ----------
        values : tuple
            A list of tuples with the configuration group name at index 0 
            and the configuration key name at index 1 of each tuple, the 
            optional index 2 can contain a list of options
        
        Returns
        -------
        tuple
            A tuple of values which contains the configuration value to use
            on the corresponding index
        """

        input_params = []
        for group, key, *_ in values:
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
            
            if len(_) > 0 and isinstance(_[0], typing.Sequence):
                # check if there are options for this ask
                input_param["options"] = list(_[0])
            
            input_params.append(input_param)

        return self.view.askFor(*input_params)
    
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
            camera_class = None
            microscope_class = None
            security_counter = 0
            load_microscope = False
            load_camera = False
            # self.camera = None
            # self.microscope = None
            while ((not isinstance(self.microscope, MicroscopeInterface) or
                    not isinstance(self.camera, CameraInterface)) and
                   security_counter < MAX_LOOP_COUNT):
                security_counter += 1
                try:
                    args = []

                    if not isinstance(self.microscope, MicroscopeInterface):
                        args.append(("microscope-module", "microscope-class", modules))
                        load_microscope = True
                    if not isinstance(self.camera, CameraInterface):
                        args.append(("camera-module", "camera-class"))
                        load_camera = True

                    # get the microscope and the camera from the config or 
                    # from the user
                    classes = self._dynamicGetClasses(*args)

                    if load_microscope and load_camera:
                        microscope_class = classes[0]
                        camera_class = classes[1]
                    elif load_microscope:
                        microscope_class = classes[0]
                    elif load_camera:
                        camera_class = classes[0]
                    
                except (ModuleNotFoundError, AttributeError, NameError, 
                        TypeError, ImportError) as e:
                    if isinstance(e, (ModuleNotFoundError, ImportError)):
                        msg = ("The microscope or the camera module could " + 
                                "not be found: {}")
                        fix = ("Change the 'microscope-module' or the " + 
                               "'camera-module' in the '{}' group in the " + 
                               "configuration or type in a valid value. The " + 
                               "value can either be a python file or a " + 
                               "python module. In case of a file, place " + 
                               "that file in the current directory where " + 
                               "this script is executed or in the " + 
                               "'microscopes' or 'cameras' directory in the " + 
                               "{} directory ({}).").format(
                                   CONFIG_SETUP_GROUP, 
                                    os.path.basename(os.path.dirname(__file__)),
                                    os.path.dirname(__file__)
                                )
                        keys = ("microscope-module", "camera-module")
                    else:
                        msg = ("The microscope or the camera module could " + 
                               "be loaded but the given class either does " + 
                               "not exist or is not a class: {}")
                        fix = ("Change the 'microscope-class' or the " + 
                               "'camera-class' in the '{}' group in the " + 
                               "configuration or type in a valid value. The " + 
                               "value has to be the name of the class that " +
                               "defines the microscope or the camera. The " + 
                               "microscope class has to extend the class " + 
                               "'pylo.microscopes.MicroscopeInterface', the " + 
                               "camera the 'pylo.cameras.CameraInterface'.").format(
                                   CONFIG_SETUP_GROUP
                                )
                        keys = ("microscope-class", "camera-class")
                    self.view.showError(msg.format(e), fix)
                    microscope_class = None
                    camera_class = None
                    # remove the saved value, this either does not exist or is
                    # wrong, in both cases the user will be asked in the next run
                    for key in keys:
                        self.configuration.removeValue(CONFIG_SETUP_GROUP, key)
                
                # define the configuration options if there are some
                if (microscope_class is not None and 
                    hasattr(microscope_class, "defineConfigurationOptions")):
                    config_keys_before = self.configuration.getGroupsAndKeys()

                    microscope_class.defineConfigurationOptions(
                        self.configuration
                    )

                    config_keys_after = self.configuration.getGroupsAndKeys()
                
                    # taken from https://stackoverflow.com/a/3462202/5934316
                    s = set(config_keys_before)
                    microscope_keys = [x for x in config_keys_after if x not in s]
                else:
                    microscope_keys = []
                
                if (camera_class is not None and
                    hasattr(camera_class, "defineConfigurationOptions")):
                    config_keys_before = self.configuration.getGroupsAndKeys()

                    camera_class.defineConfigurationOptions(
                        self.configuration
                    )
                    
                    config_keys_after = self.configuration.getGroupsAndKeys()
                
                    # taken from https://stackoverflow.com/a/3462202/5934316
                    s = set(config_keys_before)
                    camera_keys = [x for x in config_keys_after if x not in s]
                else:
                    camera_keys = []

                # ask all non-existing but required configuration options
                self.askIfNotPresentConfigurationOptions()
                
                if microscope_class is not None:
                    try:
                        self.microscope = self._dynamicCreateClass(
                            microscope_class, (self, )
                        )
                    except Exception as e:
                        self.view.showError(e)
                        self.microscope = None

                        for group, key in microscope_keys:
                            self.configuration.removeElement(group, key)
                
                if camera_class is not None:
                    try:
                        self.camera = self._dynamicCreateClass(
                            camera_class, (self, )
                        )
                    except Exception as e:
                        self.view.showError(e)
                        self.camera = None

                        for group, key in camera_keys:
                            self.configuration.removeElement(group, key)

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

            if not load_microscope:
                # microscope is set from outside, load configuration options
                if (hasattr(self.microscope, "defineConfigurationOptions") and 
                    callable(self.microscope.defineConfigurationOptions)):
                    self.microscope.defineConfigurationOptions(self.configuration)

            if not load_camera:
                # camera is set from outside, load configuration options
                if (hasattr(self.camera, "defineConfigurationOptions") and 
                    callable(self.camera.defineConfigurationOptions)):
                    self.camera.defineConfigurationOptions(self.configuration)

            # ask all non-existing but required configuration options
            self.askIfNotPresentConfigurationOptions()
            
            self.measurement = None

            # save the config
            self.configuration.saveConfiguration()

            # fire init_ready event
            init_ready()

            # prevent infinite loop
            security_counter = 0
            # build the view
            measurement_layout = None
            while (not isinstance(self.measurement, Measurement) and 
                security_counter < MAX_LOOP_COUNT):
                security_counter += 1
                
                measurement_layout = self.view.showCreateMeasurement(self)
                
                if(not isinstance(measurement_layout, typing.Sequence) or 
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
            self.view.progress_max = len(self.measurement.steps)
            self.view.showRunning()

        except StopProgram:
            self.stopProgramLoop()
            return
        except Exception as e:
            try:
                self.view.showError(e)
            except StopProgram:
                self.stopProgramLoop()
    
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
                    self.view.showError(e)
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

        # import as late as possible to allow changes by extensions        
        from .config import PROGRAM_NAME

        # ordering of dict.values() and dict.keys() changes between python
        # versions, this makes sure the order is the same
        import_dir_keys = []
        import_dir_values = []
        for k, v in import_dirs.items():
            import_dir_keys.append(k)
            import_dir_values.append(v)
        
        # create a human readable list separated by comma and the last one
        # with an 'or', parameter is the list
        humanlist = lambda x: ", ".join(x[:-1]) + " or " + x[-1]
        # the path names where the Controller::_dynamicCreateClass() function 
        # looks in
        path_names = humanlist(list(map(str, import_dir_keys)))
        # the root path to make other paths relative to this
        root = os.path.realpath(os.path.dirname(__file__))
        # the paths the Controller::_dynamicCreateClass() function looks in
        paths = list(map(lambda p: str(os.path.realpath(p)).replace(root, ""), 
                         import_dir_values))
        # a callback to create the file paths that are looked in, parameter is 
        # the file name
        files = lambda x: humanlist(list(map(lambda p: os.path.join(p, x), paths)))
        
        # add the option for the microscope module
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, 
            "microscope-module", 
            datatype=str, 
            description=("The module name where the microscope to use is " + 
            "defined. This must be a valid python module name. The file can " + 
            "be placed in {paths} directory. For example the input " + 
            "`my_custom_microscope` will check for the files " + 
            "{files}.").format(name=PROGRAM_NAME, paths=path_names, 
                               files=files("my_custom_microscope.py")),
            restart_required=True
        )
        # the configuration option for the microscope class
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, 
            "microscope-class", 
            datatype=str, 
            description=("The class name of the microscope class that " + 
            "communicates with the physical microscope. The class name must " + 
            "be defined in the 'microscope-module' file."), 
            restart_required=True
        )
        # add the option for the camera module
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, 
            "camera-module", 
            datatype=str, 
            description=("The module name where the camera to use is " + 
            "defined. This must be a valid python module name. The file can " + 
            "be placed in {paths} directory. For example the input " + 
            "`my_custom_camera` will check for the files " + 
            "{files}.").format(name=PROGRAM_NAME, paths=path_names, 
                               files=files("my_custom_camera.py")),
            restart_required=True
        )
        # the configuration option for the camera class
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, 
            "camera-class", 
            datatype=str, 
            description=("The class name of the camera class that " + 
            "communicates with the physical camera. The class name must " + 
            "be defined in the 'camera-module' file."), 
            restart_required=True
        )