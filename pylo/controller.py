import os
import sys
import time
import typing
import inspect
import importlib
import threading

from .events import init_ready
from .events import user_ready
from .events import before_init
from .events import before_start
from .events import series_ready

from .datatype import Datatype
from .measurement import Measurement
from .stop_program import StopProgram
from .abstract_view import AbstractView
from .exception_thread import ExceptionThread
from .cameras.camera_interface import CameraInterface
from .blocked_function_error import BlockedFunctionError
from .abstract_configuration import AbstractConfiguration
from .microscopes.microscope_interface import MicroscopeInterface

from .config import MAX_LOOP_COUNT
from .config import MEASUREMENT_START_TIMEOUT

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

# for importing with import_lib in Controller::_loadCameraAndMicroscope()
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
        self._running_thread = None
        
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

        for group, key in self.configuration.groupsAndKeys():
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
                input_param["datatype"] = Datatype.options(_[0])
            
            input_params.append(input_param)

        return self.view.askFor(*input_params)
    
    def _handleLoadCameraAndMicroscopeError(self, kind: str, error: typing.Union[Exception, None], msg: str, fix: str, **format_args) -> None:
        """Show an error for the `Controller._loadCameraAndMicroscope()` 
        function.

        This will show an error with the view showing the `msg` with the `fix`.
        The `kind` can either be 'camera' or 'microscope' for defining the used
        values.

        This will also reset the '<kind>-module' and '<kind>-class' 
        configuration values in the `CONFIG_SETUP_GROUP` to make sure that they
        are asked again in the next run.

        The `msg` and the `fix` can contain python string formats. The 
        supported variables are the following:
        - 'kind': The `kind` parameter value
        - 'error': The `error` parameter value
        - 'config': The `CONFIG_SETUP_GROUP` value
        - 'path': The path to the location where the `kind` classes should be 
          placed
        - 'interface': The interface class name (the full module path) that the
          class has to implement

        Parameters
        ----------
        kind : str
            Use 'camera' or 'microscope'
        error : Exception or None
            The error that was raised
        msg : str
            The error message to show, `format()` will be called on this value
        fix : str
            The error fix to show, `format()` will be called on this value

        Keyword Arguments
        -----------------
        All keyword arguments will be passed to the `str.format()` function 
        directly.
        """
        if kind == "camera":
            path = os.path.join(os.path.dirname(__file__), "cameras")
            keys = ("camera-module", "camera-class")
            interface_name = "pylo.cameras.CameraInterface"
        elif kind == "microscope":
            path = os.path.join(os.path.dirname(__file__), "microscopes")
            keys = ("microscope-module", "microscope-class")
            interface_name = "pylo.microscopes.MicroscopeInterface"
        
        format_args["kind"] = kind
        format_args["error"] = error
        format_args["config"] = CONFIG_SETUP_GROUP
        format_args["path"] = path
        format_args["interface"] = interface_name

        msg = msg.format(**format_args)
        fix = fix.format(**format_args)

        self.view.showError(msg, fix)

        for key in keys:
            self.configuration.removeValue(CONFIG_SETUP_GROUP, key)
            
    def _loadCameraAndMicroscope(self) -> bool:
        """Load the camera and/or the microscope from the settings.

        This checks if the microscope and/or the camera have to be loaded. If 
        only one is not set, it will load only this one.
        
        For loading it uses the 'microscope-module', 'microscope-class', 
        'camera-module' and 'camera-class' settings in the `CONFIG_SETUP_GROUP`
        configuration group. Those define the file and the class name. And 
        those classes will be loaded and initialized.

        If one or more of the keys are not given in the configuration, this 
        will ask for the values. If the camera and the microscope are not set
        and both are missing keys in the configuration, only one dialog will be
        shown. That is the reason for loading both with one method.

        If there is an error when loading a class, the error will be displayed
        to the user and the loading will start over again (reloading only the 
        part that did not work). 

        If the user keeps setting wrong values (or there is an internal error)
        there is a security counter. After `MAX_LOOP_COUNT` runs the function
        will stop and return False. It will return True if the load was 
        successfully.

        If the class(es) have been loaded successfully (so if this method 
        returned true), the `Controller.camera` and the `Controller.microscope`
        are valid objects. If not, the not loadable one will be set to None.

        The camera and the controllers configuration options will be asked for 
        if they are required and not set.

        Returns
        -------
        bool
            Whether the camera and/or the microscope were loaded successfully
        """
        # prevent infinite loop
        security_counter = 0
        # python extensions to load, remove the extension and let the importer
        # handle that
        extensions = (".py", ".py3", ".pyd", ".pyc", ".pyo", ".pyw", ".pyx",
                    ".pxd", ".pxi", ".pyi", ".pyz", ".pywz")

        load_camera = False
        load_microscope = False
        while ((not isinstance(self.microscope, MicroscopeInterface) or
                not isinstance(self.camera, CameraInterface)) and
                security_counter < MAX_LOOP_COUNT):
            
            security_counter += 1

            args = []
            if not isinstance(self.camera, CameraInterface):
                args.append((CONFIG_SETUP_GROUP, "camera-module"))
                args.append((CONFIG_SETUP_GROUP, "camera-class"))
                load_camera = True
            
            if not isinstance(self.microscope, MicroscopeInterface):
                args.append((CONFIG_SETUP_GROUP, "microscope-module"))
                args.append((CONFIG_SETUP_GROUP, "microscope-class"))
                load_microscope = True

            names = list(self.getConfigurationValuesOrAsk(*args))
            
            # remove file extensions of module name
            for ext in extensions:
                for i in range(0, len(names), 2):
                    if names[i].endswith(ext):
                        names[i] = names[i][:-1*len(ext)]

            load_dict = {}
            if load_camera:
                # set camera module and class name, make sure to use a list
                load_dict["camera"] = [names[0], names[1]]
            
            if load_microscope and load_camera:
                # set camera module and class name, make sure to use a list
                load_dict["microscope"] = [names[2], names[3]]
            elif load_microscope:
                # set camera module and class name, make sure to use a list
                load_dict["microscope"] = [names[0], names[1]]

            loading_error = False
            for kind, (module_name, class_name) in load_dict.items():
                msg = ""
                fix = ""
                config_keys = tuple()
                error = False

                try:
                    module = importlib.import_module(module_name, "pylo")
                except Exception as e:
                    msg = "The {kind} module could not be imported: {error}"
                    fix = ("Change the '{kind}-module' in the '{config}' " + 
                           "group in the configuration or type in a valid " + 
                           "value. The value can either be a python file or " + 
                           "a python module name. In case of a file, place " + 
                           "that file in the current directory where this " + 
                           "script is executed or in the '{kind}s' directory.")
                    self._handleLoadCameraAndMicroscopeError(kind, e, msg, fix)
                    error = True

                if not error:
                    try:
                        class_ = getattr(module, class_name)
                    except Exception as e:
                        msg = ("The {kind} module does not define the given " + 
                               "class {class_name}: {error}")
                        fix = ("Change the {class_name}-class in the " + 
                               "'{config}' group in the configuration or " + 
                               "type in a valid value. The value has to be " + 
                               "the name of the class that defines the " + 
                               "{kind}. The {class_name} has to extend the " + 
                               "{interface} class.")
                        self._handleLoadCameraAndMicroscopeError(kind, e, msg, 
                                fix, class_name=class_name)
                        error = True

                if not error and not loading_error:
                    # define the configuration options if there are some
                    if (hasattr(class_, "defineConfigurationOptions") and 
                        callable(class_.defineConfigurationOptions)):
                        config_keys_before = list(self.configuration.groupsAndKeys())

                        class_.defineConfigurationOptions(self.configuration)

                        config_keys_after = list(self.configuration.groupsAndKeys())
                    
                        # save the key this class sets, if the class cannot be 
                        # loaded, remove those keys again
                        # taken from https://stackoverflow.com/a/3462202/5934316
                        s = set(config_keys_before)
                        config_keys = [x for x in config_keys_after if x not in s]
                
                if error:
                    # do not break here, check all modules and classes first if 
                    # they are loadable, if not the user only has one dialog 
                    # to type in everything again, not multiple dialogs for 
                    # every missing value
                    loading_error = True
                elif not loading_error:
                    # save the added keys to remove them on later errors if 
                    # needed
                    load_dict[kind].append(config_keys)
                    load_dict[kind].append(class_)

            if loading_error:
                # there was at least one object that could not be loaded, 
                # before creating the objects re-ask for this error object
                continue

            # ask all non-existing but required configuration options 
            # before initializing the microscope and/or camera but ask for 
            # both objects together to prevent annoying the user by too many 
            # dialogs
            self.askIfNotPresentConfigurationOptions()
            
            for kind, (module_name, class_name, config_keys, class_) in load_dict.items():
                error = False
                try:
                    obj = class_(self)
                except Exception as e:
                    msg = ("The {kind} module defines the {class_name} " + 
                           "attribute but an object cannot be created from " + 
                           "this attribute: {error}")
                    fix = ("Change the '{class_name}' class in the " + 
                           "'{module_name}' module. It needs to be a class " + 
                           "extending the {interface} class.")
                    self._handleLoadCameraAndMicroscopeError(kind, e, msg, 
                            fix, class_name=class_name, module_name=module_name)
                    
                    error = True
                
                if not error:
                    if ((kind == "camera" and not isinstance(obj, CameraInterface)) or
                        (kind == "microscope" and not isinstance(obj, MicroscopeInterface))):
                        msg = ("The {kind} object is not inheriting from " + 
                               "the {interface} class which is required. " + 
                               "Therefore the {class_name} class cannot be " + 
                               "used as a {kind}.")
                        fix = ("Change the '{class_name}' class in the " + 
                               "'{module_name}' module to extend the " + 
                               "{interface} class.")
                        self._handleLoadCameraAndMicroscopeError(kind, None, msg, 
                                fix, class_name=class_name, module_name=module_name)
                        
                        error = True
                
                if not error:
                    if kind == "camera":
                        self.camera = obj
                    elif kind == "microscope":
                        self.microscope = obj
                else:
                    for key in config_keys:
                        self.configuration.removeElement(key)
        
        # show an error that the max loop count is reached and stop the
        # execution
        if security_counter + 1 >= MAX_LOOP_COUNT:
            self.view.showError(("The program is probably trapped in an " + 
                                "infinite loop when trying to get the " + 
                                "camera. The execution will be stopped now " + 
                                "after {} iterations.").format(security_counter),
                                "This is a bigger issue. Look in the code " + 
                                "and debug the 'pylo/controller.py' file.")
            return False
        else:
            return True

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
            
            if not isinstance(self.microscope, MicroscopeInterface):
                load_microscope = True
            else:
                load_microscope = False
            
            if not isinstance(self.camera, CameraInterface):
                load_camera = True
            else:
                load_camera = False
            
            if load_microscope or load_camera:
                # the function will check itself if it has to load something,
                # this has to be one function so the user will get asked only
                # once for the microscope AND the camera if both are missing,
                # if only one is missing, this function will ask for the 
                # missing one only
                self._loadCameraAndMicroscope()

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

            # ask all non-existing but required configuration values
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
                target=self.measurement.start, name="measurement"
            )
            self._measurement_thread.start()

            self.view.progress_max = len(self.measurement.steps)
            self.view.progress = 0
            self.view.clear()
            
            self._running_thread = ExceptionThread(
                target=self.view.showRunning, name="running"
            )
            self._running_thread.start()
        except StopProgram:
            self.stopProgramLoop()
            return
        except Exception as e:
            try:
                self.view.showError(e, self._getFixForError(e))
                self.view.show_running = False
            except StopProgram:
                self.stopProgramLoop()
    
    def waitForProgram(self, raise_error_when_not_started: typing.Optional[bool]=False) -> None:
        """Wait until the program has finished.

        Raises
        ------
        RuntimeError
            When the measurement has not started after the waiting timeout
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

        # check if the start function has been called, that is the case if 
        # the threads are set and they are alive
        if ((isinstance(self._measurement_thread, threading.Thread) and 
             self._measurement_thread.is_alive()) or 
            (isinstance(self._running_thread, threading.Thread) and 
             self._running_thread.is_alive())):
            running = True
        else:
            running = False

        # wait until the measurement has started, this is only for fixing
        # synchronizing problems because this funciton is started before the 
        # measurement thread is fully started
        if running:
            start_time = time.time()

            # wait until the measurement is running
            while (not self.measurement.running and 
                   time.time() < start_time + MEASUREMENT_START_TIMEOUT):
                time.sleep(MEASUREMENT_START_TIMEOUT / 10)
            
            if (not self.measurement.running and (
                not isinstance(self._measurement_thread, ExceptionThread) or 
                len(self._measurement_thread.exceptions) == 0)):
                raise RuntimeError("The measurement was told to start by the " + 
                                "controller but when the controller is " + 
                                "waiting for the measurement to end, the " + 
                                "measurement still has not started. This " + 
                                "can be because of a too short " + 
                                "measurement timeout. If changing the " + 
                                "maximum time does not help, this is " + 
                                "a fatal error caused by a big internal " + 
                                "problem.")

        try:
            while running and self.measurement.running:
                self.raiseThreadErrors()
                time.sleep(0.05)
            
            # if the measurement detects an error, Measurement.running will be 
            # False, so the while-loop is not executed and if an exception 
            # occurres before starting the measurement, the loop will not be 
            # running too
            self.raiseThreadErrors()
            
            # finished
            stop_program = True
        except StopProgram:
            stop_program = True
        except Exception as e:
            try:
                # stop before the error, mostly the view raises the python 
                # error too so the program would not end then
                print("Controller.waitForProgram(): Error detected:", e.__class__.__name__, e)
                self.stopProgramLoop()
                self.view.showError(e, self._getFixForError(e))
            except StopProgram:
                stop_program = True
        
        self.stopProgramLoop()

        if stop_program:
            return
        elif not running and raise_error_when_not_started:
            raise RuntimeError("Cannot wait for the program if the program " + 
                               "has not started or has already finished.")
    
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

        for thread in (self._measurement_thread, self._running_thread, *additional_threads):
            if (isinstance(thread, ExceptionThread) and len(thread.exceptions) > 0):
                for error in thread.exceptions:
                    print("Controller.raiseThreadErrors(): Raising error from thread '{}'".format(thread.name))
                    raise error
    
    def _getFixForError(self, error: Exception) -> typing.Union[None, str]:
        """Get a possible fix for the given error.

        Parameters
        ----------
        error : Exception
            The error to get the possible fix for
        
        Returns
        -------
        None or str
            The text how to possibly fix this error or None if there is no fix
            found
        """

        fix = None
        if isinstance(error, BlockedFunctionError):
            fix = ("A function was blocked due to security reasons, " + 
                    "probably because an error occurred. You will continue " + 
                    "getting this error until you restart the program " + 
                    "completely.")
        
        return fix
    
    def stopProgramLoop(self) -> None:
        """Stop the program loop.

        This funciton will also wait for all threads to join.
        """

        if isinstance(self.measurement, Measurement) and self.measurement.running:
            self.measurement.stop()

        if isinstance(self.view, AbstractView):
            self.view.hideRunning()
            self.view.show_running = False

        if isinstance(self._measurement_thread, ExceptionThread):
            self._measurement_thread.join()
        
        if isinstance(self._running_thread, ExceptionThread):
            self._running_thread.join()
            
        if isinstance(self.measurement, Measurement):
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
        # the path names where the Controller::_loadCameraAndMicroscope() 
        # function looks in
        path_names = humanlist(list(map(str, import_dir_keys)))
        # the root path to make other paths relative to this
        root = os.path.realpath(os.path.dirname(__file__))
        # the paths the Controller::_loadCameraAndMicroscope() function looks in
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