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

from .errors import DeviceImportError
from .errors import DeviceCreationError
from .errors import BlockedFunctionError
from .errors import DeviceClassNotDefined

from .datatype import Datatype
from .measurement import Measurement
from .stop_program import StopProgram
from .abstract_view import AbstractView
from .camera_interface import CameraInterface
from .exception_thread import ExceptionThread
from .microscope_interface import MicroscopeInterface
from .abstract_configuration import AbstractConfiguration

from .config import MAX_LOOP_COUNT
from .config import MEASUREMENT_START_TIMEOUT

class TooManyRepetitionsError(RuntimeError):
    """Show that statements are repeated too many times. There is no more 
    progress expected."""
    pass

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
        The measurement to do, this only exists while the program is executed
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
        self._running_thread = None
        self._measurement_thread = None

        self.stopProgramLoop()
        
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
                restart_required = self.configuration.getRestartRequired(
                    group, key
                )

                if restart_required:
                    restart_required_msg = ("The program will be restarted " + 
                                            "automatically after confirmation.")
                    if (not "description" in input_param or 
                        not isinstance(input_param["description"], str)):
                        input_param["description"] = restart_required_msg
                    else:
                        input_param["description"] += restart_required_msg
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
            
    def _loadCameraAndMicroscope(self) -> bool:
        """Load the camera and/or the microscope from the settings.

        This checks if the microscope and/or the camera have to be loaded or if
        they have been set from outside already. If only one is not set, only 
        the not defined one will be loaded
        
        For loading it uses the 'microscope' and 'camera' settings in the 
        `CONFIG_SETUP_GROUP` configuration group. Those define the device name
        which can be found via the `loader` object in the `__init__.py`. The 
        loading of the class, if needed, will completely be handled by this 
        object.

        If one or more of the keys are not given in the configuration, this 
        function will ask for the values. If the camera and the microscope are 
        not set and both are missing keys in the configuration, only one dialog 
        will be shown.

        If a class could not be initialized, all settings will tried to be 
        reset to the state before the creation of the class. Then the user will
        be asked for changing the unloadable device. If the device keeps not
        being loadable or an error causes the initialization to start over, the
        execution will stop after `MAX_LOOP_COUNT` runs and raise a 
        `TooManyRepetitionsError`.

        If the class(es) have been loaded successfully (so if this method 
        returned true), the `Controller.camera` and the `Controller.microscope`
        are valid objects. If not, the unloadable one will be set to None.

        The camera and the controllers configuration options will be asked for 
        if they are required and not set.

        Raises
        ------
        TooManyRepetitionsError
            When there are more than `MAX_LOOP_COUNT` runs required to create a
            valid microscope and/or camera object
        StopProgram
            When class is loaded from the file and the class raises a 
            `StopProgram` exception anywhere

        Returns
        -------
        bool
            Whether the camera and/or the microscope were loaded successfully
        """
        # prevent infinite loop
        security_counter = 0

        while ((not isinstance(self.microscope, MicroscopeInterface) or
                not isinstance(self.camera, CameraInterface)) and
                security_counter < MAX_LOOP_COUNT):
            
            security_counter += 1

            args = []
            load_kinds = []
            if not isinstance(self.camera, CameraInterface):
                args.append((CONFIG_SETUP_GROUP, "camera"))
                load_kinds.append("camera")
            
            if not isinstance(self.microscope, MicroscopeInterface):
                args.append((CONFIG_SETUP_GROUP, "microscope"))
                load_kinds.append("microscope")

            names = list(self.getConfigurationValuesOrAsk(*args))
            
            from . import loader

            for name, kind in zip(names, load_kinds):
                device = None
                try:
                    device = loader.getDevice(name, self)
                    if device is None:
                        msg = ("The device '{}' neither is defined one of " +
                               "the devices.ini nor is added in " + 
                               "runtime.").format(name)
                        fix = (("Check the devices.ini if one of them " + 
                                "contains the '{}' definition. If so make " + 
                                "sure that it is not disabled, that its " + 
                                "kind is '{}' and that the 'file' and " + 
                                "'class' are valid, exist and are readable. " +
                                "If the '{}' is not found in one of the " + 
                                "devices.ini files, add it to one of them. " + 
                                "\n").format(name, kind, name) + 
                            "The following devices.ini are loaded at the " + 
                            "moment:\n".format() + 
                            "\n".join(map(lambda x: "- '{}'".format(x), 
                                            loader.device_ini_files)))
                        self.view.showError(msg, fix)
                except StopProgram as e:
                    raise e
                except (DeviceImportError, DeviceClassNotDefined, 
                        DeviceCreationError) as e:
                    self.view.showError(e, self._getFixForError(e))
                except Exception as e:
                    fix = ("Fix the error was raised during creation of " + 
                           "the '{}' object in the file '{}'. Fix the error " + 
                           "there, then the loading should work.").format(
                            name, loader.getDeviceClassFile(name))
                    self.view.showError(e, fix)
                
                if kind == "camera":
                    if device is not None:
                        self.camera = device
                    else:
                        self.configuration.removeValue(CONFIG_SETUP_GROUP,
                                                       "camera")
                elif kind == "microscope":
                    if device is not None:
                        self.microscope = device
                    else:
                        self.configuration.removeValue(CONFIG_SETUP_GROUP,
                                                       "microscope")

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
    
    def _configurationChangesNeedRestart(self, state_id: int, 
                                         show_hint: typing.Optional[bool]=True) -> typing.List[typing.Tuple[str, str]]:
        """Check if there are configuration changes in between the state made
        at the marked state with the `state_id` that trigger a restart.

        Note that if the `state_id` is not set, this will *not* raise an 
        Exception but simply ignore the function call. Also not that this 
        function does not perform the restart, it only checks if there is a 
        restart required.

        The state with the `state_id` is dropped if the state exists.

        If `show_hint` is True, a hint will be displayed to the user using the 
        registered `view` object.

        Raises
        ------
        StopProgram
            When a hint is shown and the user cancels the hint

        Parameters
        ----------
        state_id : int
            The state id
        show_hint : bool, optional
            Whether to show a hint to the user or not, default: True
        
        Returns
        -------
        list
            The list of restart required elements that have changed or an empty
            list if no elemnt has changed or the changed elements do not 
            require a restart
        """
        try:
            config_changes = (self.configuration.getAdditions(state_id, True, True) | 
                              self.configuration.getChanges(state_id))
        except KeyError:
            return False
        
        self.configuration.dropStateMark(state_id)
        # print("Controller._configurationChangesNeedRestart():", config_changes)
        # from pprint import pprint
        # pprint(self.configuration.configuration)

        # check if there is a change that requires a restart
        restart_required = []
        for group, key in config_changes:
            if self.configuration.getRestartRequired(group, key):
                restart_required.append((group, key))
        
        if len(restart_required) > 0:
            if show_hint:
                from .config import PROGRAM_NAME
                restart_settings_text = "\n".join(map(
                    lambda kg: "- '{}' in group '{}'".format(kg[1], kg[0]), 
                    restart_required
                ))

                self.view.showHint(("You changed the following {} settings " + 
                                    "that require {} to restart to have any " + 
                                    "effect. Confirm to restart or cancel to " + 
                                    "stop the execution completely.\n\n" + 
                                    "The following settings require this " + 
                                    "restart: \n\n{}").format(
                                        len(restart_required), PROGRAM_NAME,
                                        restart_settings_text
                                    ))
            
            return restart_required
        else:
            return []

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
            # mark the initial state to track changes that require a restart 
            # of the program loop
            state_id = self.configuration.markState()

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

            # not needed to check changes here, the user did not have a chance
            # of changing anything so all values are startup values
            # if self._configurationChangesNeedRestart(state_id):
            #     self.restartProgramLoop()
            #     return
            
            state_id = self.configuration.markState()

            # fire init_ready event
            init_ready()

            # prevent infinite loop
            security_counter = 0
            # build the view
            interactions = None
            while (not isinstance(self.measurement, Measurement) and 
                security_counter < MAX_LOOP_COUNT):
                security_counter += 1
                
                # index 0: measurement start parameters
                # index 1: measurement series paramters
                # index 2: configuration as a dict
                # index 3: custom tags as a dict
                interactions = self.view.showProgramDialogs(self)
                
                if (not isinstance(interactions, typing.Sequence) or 
                    len(interactions) < 4):
                    raise RuntimeError("The view does not return all required " + 
                                       "user values.")

                # update configuration
                self.configuration.loadFromMapping(interactions[2])
            
                # fire user_ready event
                user_ready()

                # save the config again, the view may show options
                self.configuration.saveConfiguration()

                # get the changes in the configuration, the view shows the 
                # settings
                restart_required_changes = self._configurationChangesNeedRestart(state_id)
                if len(restart_required_changes) > 0:
                    # reset microscope and camera if they changed
                    if ((CONFIG_SETUP_GROUP, "microscope") in 
                        restart_required_changes):
                        self.microscope = None
                    if ((CONFIG_SETUP_GROUP, "camera") in 
                        restart_required_changes):
                        self.camera = None

                    self.restartProgramLoop()
                    return

                try:
                    self.measurement = Measurement.fromSeries(self, 
                        interactions[0], interactions[1])
                except (KeyError, ValueError) as e:
                    msg = ("The measurement could not be initialized " + 
                           "because it is not formatted correctly: {}".format(e))
                    fix = ("Try again and make sure you entered a valid " + 
                           "value for this. If this error keeps appearing " + 
                           "even though all values are correct, there is " + 
                           "an internal problem with the Measurement class.")
                    self.view.showError(msg, fix)

                # set the custom tags to the measurement
                self.measurement.tags = interactions[3]

            # show an error that the max loop count is reached and stop the
            # execution
            if security_counter + 1 >= MAX_LOOP_COUNT:
                msg = ("The program is probably trapped in an infinite loop " +
                       "when trying to initialize the measurement. The " + 
                       "execution will be stopped now  after {} " + 
                       "iterations.").format(security_counter)
                self.view.showError(msg)
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
            self._handleErrorWhileProgramIsRunning(e)
    
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
        # synchronizing problems because this function may be started before 
        # the measurement thread is fully started, for very fast measurements 
        # (mostly test measurements, there are no IO-operations), the 
        # measurement may be finished before this function is called to wait 
        # for the finish, therefore skip the waiting completely
        if running and not self.measurement.finished:
            start_time = time.time()

            # wait until the measurement is running
            while (not self.measurement.running and 
                   time.time() < start_time + MEASUREMENT_START_TIMEOUT):
                time.sleep(MEASUREMENT_START_TIMEOUT / 10)
            
            if (not self.measurement.running and not self.measurement.finished and
                (not isinstance(self._measurement_thread, ExceptionThread) or 
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
        except StopProgram:
            pass
        except Exception as e:
            self._handleErrorWhileProgramIsRunning(e)
        
        self.stopProgramLoop()

        if not running and raise_error_when_not_started:
            raise RuntimeError("Cannot wait for the program if the program " + 
                               "has not started or has already finished.")
    
    def _handleErrorWhileProgramIsRunning(self, error: Exception) -> None:
        """Stop the program, set the microscope and camera to emergency and 
        display the error with possible fixes.

        Parameters
        ----------
        error : Exception
            The error
        """

        if isinstance(error, StopProgram):
            self.stopProgramLoop()
        else:
            try:
                # stop before the error, mostly the view raises the python 
                # error too so the program would not end then
                print("Controller._handleErrorWhileProgramIsRunning(): Error " + 
                      "detected:", error.__class__.__name__, error)
                self.stopProgramLoop()
                self._setEmergency()
                self.view.showError(error, self._getFixForError(error))
            except StopProgram:
                self.stopProgramLoop()
    
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
                    if not isinstance(error, StopProgram):
                        print("Controller.raiseThreadErrors(): Raising error from thread '{}'".format(thread.name))
                    raise error
    
    def _setEmergency(self) -> None:
        """Set the microscope and the camera to be in emergency state."""

        try:
            self.microscope.resetToEmergencyState()
        except BlockedFunctionError:
            # emergency event is called, microscope goes in emergency state by 
            # itself
            pass

        try:
            self.camera.resetToEmergencyState()
        except BlockedFunctionError:
            # emergency event is called, camera goes in emergency state by 
            # itself
            pass
    
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
        elif isinstance(error, DeviceImportError):
            fix = ("The file is not importable. Either the file does not " + 
                   "exist or cannot be read because of missing reading " + 
                   "permissions. Make sure that the file exists and that " + 
                   "it can be opened by the python interpreter. " + 
                   "\n" + 
                   "To change the file visit the 'devices.ini' file where " + 
                   "this device is defined in.")
        elif isinstance(error, DeviceClassNotDefined):
            fix = ("The file does not define the class name so add the " + 
                   "class definition to the loaded file or change the class " + 
                   "name to the name the file defines.")
        elif isinstance(error, DeviceCreationError):
            fix = ("The class object probably has some errors probably in " + 
                   "its constructor or in a method or function called in " + 
                   "the constructor. To fix simply fix those errors.")
                   
        return fix
    
    def stopProgramLoop(self) -> None:
        """Stop the program loop.

        This funciton will also wait for all threads to join.
        """

        if (isinstance(self.measurement, Measurement) and 
            self.measurement.running):
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
        
        self._measurement_thread = None
        self._running_thread = None
    
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

        # import after program is running, loader may be added files before 
        # starting the program
        from . import loader
        # import as late as possible to allow changes by extensions        
        from .config import PROGRAM_NAME
        from .config import DEFAULT_DEVICE_INI_PATHS

        descr = ("The {kind} to use for the measurement. All microscopes " + 
                 "and cameras defined in one or more `devices.ini` files. " + 
                 "To add new microscopes or cameras they have to be " + 
                 "registered in this file (or at runtime in the " + 
                 "`pylo.loader`). The `devices.ini` files can be in one of " + 
                 "the following directories: \n" +  
                 "\n".join(map(lambda x: "- '{}'".format(x), 
                               DEFAULT_DEVICE_INI_PATHS)) + 
                 "\n")
        
        # add the option for the microscope module
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, 
            "microscope", 
            datatype=Datatype.options(loader.getInstalledDeviceNames("microscope")), 
            description=descr.format(kind="microscope"),
            restart_required=True
        )
        # add the option for the camera module
        configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, 
            "camera", 
            datatype=Datatype.options(loader.getInstalledDeviceNames("camera")),
            description=descr.format(kind="camera"),
            restart_required=True
        )