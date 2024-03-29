import os
import sys
import copy
import typing
import inspect
import logging
import importlib
import configparser

from .errors import DeviceImportError
from .errors import DeviceCreationError
from .errors import DeviceClassNotDefined

from .device import Device
from .logginglib import log_debug
from .logginglib import log_error
from .logginglib import get_logger
from .pylolib import path_like
from .device import device_kinds
from .controller import Controller
from .stop_program import StopProgram
from .camera_interface import CameraInterface
from .microscope_interface import MicroscopeInterface

class DeviceLoader:
    """A class to load devices.
    
    Devices can either be set directly as an object, via a python file with 
    the corresponding class or via ini files. The ini files are the common way.
    The ini file has the following format:
    
    ```ini
    [Device Name]
    ; The kind, can either be "camera" or "microscope" (others are loaded 
    ; too and can be used by plugins ect.)
    kind=microscope 
    ; The path of the python file, can be absolute or relative to this
    ; file location by using "./", use "~" for current user directory, 
    ; path variables are allowed (for windows e.g. %PROGRAMDATA%, ...)
    ; Unix and Windows paths are supported
    file=./path/to/device.py
    ; The name of the class to initialize, has to be defined in the file
    class=DeviceClassName
    ; Optional keys:
    ; ~~~~~~~~~~~~~
    ; Whether this device is disabled or not, default is false
    disabled=No
    ; Default keys of other devices to inherit from, use a pipe character 
    ; ("|") as separator of multiple ones, spaces are not removed (spaces 
    ; matter!), overwriting is from left to right, own `config-default`s 
    ; overwrite inherited values
    inherit-config-defaults-from=Other Device Name|Yet another device name
    ; Default settings for this device, they are available in the 
    ; created object (if the object extends the `pylo.Device` class) in
    ; the `object.config_defaults` dict, note that they are strings 
    ; always, the key is the part after `config-default.`
    config-default.key1=
    config-default.key2=12
    config-default.key3=False
    config-default.key4=Test text
    ```
    """

    def __init__(self, *ini_file: typing.Union[path_like]) -> None:
        """Create a new device loader."""
        self.device_ini_files = set(ini_file)
        self._device_class_files = []
        self._device_objects = []
        self._logger = get_logger(self)
    
    def addDeviceFromFile(self, kind: device_kinds, name: str, 
                          file_path: typing.Union[path_like], 
                          class_name: str, 
                          config_defaults: typing.Optional[dict]={}, 
                          description: typing.Optional[str]="") -> None:
        """Add a device that is loadable from a python file.

        Parameters
        ----------
        kind : str
            The kind, at the moment "camera" and "microscope" are supported
        name : str
            The name to show in the GUI and to use to load this device
        file_path : path-like
            The path to the python file where the device is defined in
        class_name : str
            The name of the class to generate
        config_defaults : dict of str, optional
            Configuration defaults that can be used by the class, default: {}
        description : str, optional
            A description of the device, currently not used, default: ""
        """
        device_definition = {
            "kind": kind, 
            "name": name, 
            "file_path": file_path, 
            "class_name": class_name, 
            "config_defaults": config_defaults, 
            "description": description
        }
        self._device_class_files.append(device_definition)
        log_debug(self._logger, ("Registering device from single file " + 
                                "'{}'").format(device_definition))

    def addDeviceObject(self, kind: device_kinds, name: str, device: "Device", 
                        config_defaults: typing.Optional[dict]={}, 
                        description: typing.Optional[str]="") -> None:
        """Add a device.

        Parameters
        ----------
        kind : str
            The kind, at the moment "camera" and "microscope" are supported
        name : str
            The name to show in the GUI and to use to load this device
        device : Device
            The device object to add
        config_defaults : dict of str, optional
            Configuration defaults that can be used by the class, default: {}
        description : str, optional
            A description of the device, currently not used, default: ""
        """
        device_definition = {
            "kind": kind, 
            "name": name, 
            "object": device,
            "config_defaults": config_defaults, 
            "description": description
        }
        self._device_objects.append(device_definition)
        log_debug(self._logger, ("Registering device from object " + 
                                "'{}'").format(device_definition))
    
    def _resolveConfigDefaultsInheritance(self, device_definition: dict,
                                          devices: typing.Sequence[dict],
                                          prevent_list: typing.Optional[list]=[]) -> typing.Tuple[dict, typing.Sequence[dict]]:
        """Resolve the inheritance of `config_defaults`.

        If the `device_definition` contains a list at the key 
        "inherit-config-defaults-from", all `devices` will be travelled through
        and the `config_defaults` of the devices with the corresponding names 
        are copied to the current `device_definition`s `config_defaults`.

        If the parent also has an inheritance given, this inheritance will be 
        resolved. Note that circular dependencies will result in unexpected 
        behaviour where it gets resolved to a specific "random" point but not 
        further.

        Inheritance goes from 0 to the end in the inheritance list. The own 
        `config_defaults` will always overwrite all parent values.

        Parameters
        ----------
        device_definition : dict
            The device definition as a dict
        devices : list of dict
            All the devices that exist (in the same ini) and are used to 
            resolve the inheritance
        prevent_list : list of str, optional
            The names to prevent inheriting for, this is used for preventing
            circular dependencies by adding the current name to the list, this
            should be left empty when using this function, default: set()
        
        Returns
        -------
        dict, list of dict
            The `device_definition` with the updated `config_defaults` and the 
            `devices` list with resolved inheritance if the inheritance is used
            by this `device_definition`
        """

        if ("inherit-config-defaults-from" in device_definition and 
            isinstance(device_definition["inherit-config-defaults-from"], list)):
            # save current defaults
            if (not "config_defaults" in device_definition or 
                not isinstance(device_definition["config_defaults"], dict)):
                config_defaults = None
            else:
                config_defaults = copy.deepcopy(device_definition["config_defaults"])
            
            # set to an empty list to prevent overwriting
            device_definition["config_defaults"] = {}
            
            # go through the inheritance list
            for parent_name in device_definition["inherit-config-defaults-from"]:
                if parent_name not in prevent_list:
                    # prevent self inheritance and circular inheritance
                    prevent_list.append(parent_name)
                    parent_device = None

                    # go through devices and find parent
                    for i, device in enumerate(devices):
                        if "name" in device and device["name"] == parent_name:
                            if "inherit-config-defaults-from" in device:
                                # resolve the inheritance of the parent
                                parent_device, devices = self._resolveConfigDefaultsInheritance(
                                    device, devices, prevent_list)
                                # if the inheritance is resolved, the 
                                # "inherit-config-defaults-from" is removed so 
                                # update the devices to save travelling through
                                # the same devices over and over again
                                devices[i] = parent_device
                            else:
                                parent_device = device
                            
                            break
                    
                    if (isinstance(parent_device, dict) and 
                        "config_defaults" in parent_device and 
                        isinstance(parent_device["config_defaults"], dict)):
                        # add the parent config defaults
                        device_definition["config_defaults"].update(
                            parent_device["config_defaults"])

            # overwrite all settings with the original ones to prevent parents 
            # overwriting the child settings
            if isinstance(config_defaults, dict):
                device_definition["config_defaults"].update(config_defaults)

            # save that the inheritance is done
            del device_definition["inherit-config-defaults-from"]

        return device_definition, devices
    
    def _getDeviceDefinitionsFromInis(self) -> typing.List[dict]:
        """Get the devices dicts from the ini files.

        Returns
        -------
        list of dict
            The list of devices that are defined in one of the ini files
        """

        devices = []
        needs_class = ("microscope", "camera")
        required_keys = {"kind": str, "file": str}
        optional_keys = {"description": str, "disabled": bool, "class": str,
                         "inherit-config-defaults-from": str}
        synonyms = {"file_path": "file", "class_name": "class"}

        for ini_file in self.device_ini_files:
            with open(ini_file, "r") as f:
                config = configparser.ConfigParser(interpolation=None)
                config.read_file(f, ini_file)

                for name in config.sections():
                    dev = {
                        "name": name,
                        "__relpath": os.path.dirname(os.path.realpath(ini_file)),
                        "config_defaults": {}
                    }
                    for key, value in config.items(name):
                        config_key = key
                        
                        if key in synonyms:
                            key = synonyms[key]
                        
                        t = None
                        if key in required_keys:
                            t = required_keys[key]
                        elif key in optional_keys:
                            t = optional_keys[key]
                        elif key.startswith("config-default."):
                            key = key.replace("config-default.", "")
                            dev["config_defaults"][key] = value
                            continue
                            
                        if key == "inherit-config-defaults-from":
                            value = list(map(lambda x: x.strip(), 
                                             value.split("|")))
                        
                        if t == str:
                            dev[key] = value
                        elif t == int:
                            dev[key] = config.getint(name, config_key)
                        elif t == float:
                            dev[key] = config.getfloat(name, config_key)
                        elif t == bool:
                            dev[key] = config.getboolean(name, config_key)

                    # check if all required keys exist and the device is not 
                    # disabled
                    if (len(set(required_keys.keys()) - set(dev.keys())) == 0 and 
                        (dev["kind"] not in needs_class or "class" in dev) and
                        ("disabled" not in dev or not dev["disabled"])):
                        devices.append(dev)

        # resolve inheritance
        for i, device in enumerate(devices):
            if "inherit-config-defaults-from" in device:
                device, devices = self._resolveConfigDefaultsInheritance(
                                    device, devices, prevent_list=[])
                devices[i] = device

        return devices
    
    def getInstalledDeviceNames(self, kind: typing.Optional[device_kinds]=None) -> typing.List[str]:
        """Get all installed names for the given `kind`.

        The names will be loaded from all ini files and from the added objects
        and the added device files.

        Parameters
        ----------
        kind : str
            The kind to get all available devices of, "microscope" and "camera"
            are supported
        
        Returns
        -------
        list of str
            The names for the device that can be used
        """

        installed_names = []
        for device in (self._getDeviceDefinitionsFromInis() + 
                       self._device_objects + self._device_class_files):
            try:
                if ((("kind" in device and device["kind"] == kind) or 
                     kind is None) and "name" in device):
                    installed_names.append(device["name"])
            except TypeError:
                pass
        
        return installed_names
    
    def _getDeviceDefinition(self, name: str) -> typing.Union[dict, None]:
        """Get the device definition dict.

        Go through all the saved device sources and find the device with the 
        `name`. Then return the dict that is found.

        This will start with the `DeviceLoader._device_objects`, then the 
        `DeviceLoader._device_class_files` and then load definitions from the 
        `DeviceLoader.device_ini_files`. The first match with the same name
        will be returned.

        Parameters
        ----------
        name : str
            The name of the device

        Returns
        -------
        dict or None
            The definition dict or None if the `name` is not found
        """
        found_device = None
        for device in self._device_objects:
            if ("name" in device and device["name"] == name and 
                "object" in device):
                found_device = device
                log_debug(self._logger, ("Getting device '{}' from object list: " + 
                                        "'{}'").format(name, found_device))
                break
        
        if found_device is None:
            for device in self._device_class_files + self._getDeviceDefinitionsFromInis():
                if ("name" in device and device["name"] == name and 
                    # ("class_name" in device or "class" in device) and 
                    ("file_path" in device or "file" in device)):
                    if "class" in device:
                        if "class_name" not in device:
                            device["class_name"] = device["class"]
                        del device["class"]
                    
                    if "file" in device:
                        if "file_path" not in device:
                            device["file_path"] = device["file"]
                        del device["file"]
                    
                    # make ./ relative to the ini file if this comes from the 
                    # ini file
                    if ("__relpath" in device and
                        (device["file_path"].startswith("./") or
                            device["file_path"].startswith(r".\\"))):
                        device["file_path"] = os.path.join(device["__relpath"], 
                                                            device["file_path"])

                    # resolve all variables and links, ect.
                    device["file_path"] = os.path.expandvars(device["file_path"])
                    device["file_path"] = os.path.expanduser(device["file_path"])
                    device["file_path"] = os.path.realpath(device["file_path"])
                    device["file_path"] = os.path.abspath(device["file_path"])
                    
                    found_device = device
                    log_debug(self._logger, ("Getting device '{}' from file or " + 
                                            "ini list: '{}'").format(name, found_device))
                    break
        
        if found_device is not None:
            if "config_group_name" not in found_device:
                found_device["config_group_name"] = Device.convertToSnakeCase(
                    found_device["name"])
            
            if "config_defaults" not in found_device:
                found_device["config_defaults"] = {}
            
            if "description" not in found_device:
                found_device["description"] = ""
        
        return found_device
    
    def getDeviceFile(self, name: str, 
                      find_object_file: typing.Optional[bool]=False) -> typing.Union[str, None]:
        """Get the absolute file path of the file where the device object for 
        the given `name` is defined in.

        If the device is not found or it is an object and `find_object_file` is
        False, None is returned.

        This will start with the `DeviceLoader._device_objects`, then the 
        `DeviceLoader._device_class_files` and then load definitions from the 
        `DeviceLoader.device_ini_files`. The first match with the same name
        will be returned.

        Parameters
        ----------
        name : str
            The name of the device
        find_object_file : bool, optional
            Whether to return the file also when the device is added as the 
            object directly, default: False

        Returns
        -------
        str or None
            The absolute path of the python class definition file or None if 
            not found or an object and `find_object_file` is False
        """

        device_definition = self._getDeviceDefinition(name)

        if device_definition is None:
            return None
        elif "file_path" in device_definition:
            return device_definition["file_path"]
        elif "object" in device_definition and find_object_file:
            return inspect.getfile(device_definition["object"].__class__)
        else:
            return None
    
    def getDeviceClass(self, name: str, 
                       controller: typing.Optional["Controller"]=None) -> typing.Union[type, None]:
        """Get the device class.

        Note that this is not the class name!
        
        Parameters
        ----------
        name : str
            The name of the device
        controller : Controller, optional
            The controller object to handle configuration options and to set 
            as the first parameter for microscopes and cameras, default: None
        
        Returns
        -------
        type or None
            The class or None if the device is not found
        """

        device_definition = self._getDeviceDefinition(name)

        if device_definition is None:
            log_debug(self._logger, "Could not find device '{}'".format(name))
            return None
        elif "object" in device_definition:
            class_ = device_definition["object"].__class__
            log_debug(self._logger, ("Returning class '{}' for device '{}' from " + 
                                    "object device list").format(class_, name))
            return class_
        else:
            class_, *_ = self._loadClass(device_definition, controller)
            log_debug(self._logger, ("Returning class '{}' for device '{}' from " + 
                                    "file device").format(class_, name))
            return class_
    
    def importPlugins(self, controller: typing.Optional["Controller"]=None,
                      *constructor_args: typing.Any, 
                      **constructor_kwargs: typing.Any) -> None:
        """Import all elements where the kind is plugin.

        Raises
        ------
        DeviceImportError
            When the file is not importable
        DeviceClassNotDefined
            When a class is loaded from the file and the module does not define 
            the `class_name`
        DeviceCreationError
            When a class is loaded from the file and the `class_name` object 
            could not be created
        StopProgram
            When the loaded code raises a `StopProgram` exception anywhere
        
        Parameters
        ----------
        name : str
            The name of the device
        controller : Controller, optional
            The controller object to handle configuration options, 
            default: None
        constructor_args : any
            The arguments that are passed to the construcor if the device is 
            created and a `Device` object
        constructor_kwargs : any
            The keyword arguments that are passed to the constructor if the 
            device is created and a `Device` object
        """

        log_debug(self._logger, "Importing plugins")
        plugin_names = self.getInstalledDeviceNames("plugin")

        log_debug(self._logger, "Found plugins '{}'".format(plugin_names))

        for plugin in plugin_names:
            log_debug(self._logger, "Loading plugin '{}'".format(plugin))

            self.getDevice(plugin, controller, *constructor_args, 
                           **constructor_kwargs)
    
    def getDevice(self, name: str, 
                  controller: typing.Optional["Controller"]=None,
                  *constructor_args: typing.Any, 
                  **constructor_kwargs: typing.Any) -> typing.Union["Device", "module", object, None]:
        """Get the device with the given `name`.

        If the `name` does not exist None is returned. The available device 
        names can be retrieved by the `DeviceLoader.getInstalledDeviceNames()`.

        This function will look in the `DeviceLoader._device_objects` at first,
        then in the `DeviceLoader._device_class_files` and then in the 
        `DeviceLoader.device_ini_files` to get the correct object. If the 
        object is a `Device` it will be set to the correct name, and 
        configuration defaults.

        Raises
        ------
        DeviceImportError
            When a class is loaded from the file and the file is not importable
        DeviceClassNotDefined
            When a class is loaded from the file and the module does not define 
            the `class_name`
        DeviceCreationError
            When a class is loaded from the file and the `class_name` object 
            could not be created
        StopProgram
            When a class is loaded from the file and the class raises a 
            `StopProgram` exception anywhere
        
        Parameters
        ----------
        name : str
            The name of the device
        controller : Controller, optional
            The controller object to handle configuration options and to set 
            as the first parameter for microscopes and cameras, default: None
        constructor_args : any
            The arguments that are passed to the construcor if the device is 
            created and a `Device` object
        constructor_kwargs : any
            The keyword arguments that are passed to the constructor if the 
            device is created and a `Device` object
        
        Returns
        -------
        Device or object or None
            The device object if the defined device extends the Device class 
            (should be the case but is not guaranteed) or the object or the 
            module if there is no class_name given for the device or None if
            no element with the `name` can be found
        """

        device_definition = self._getDeviceDefinition(name)

        if device_definition is None:
            return None
        elif "object" in device_definition:
            device = device_definition["object"]

            if isinstance(device_definition["object"], Device):
                if "kind" in device_definition:
                    device.kind = device_definition["kind"]
                if "name" in device_definition:
                    device.name = device_definition["name"]
                if "config_group_name" in device_definition:
                    device.config_defaults = device_definition["config_group_name"]
                if "config_defaults" in device_definition:
                    device.config_defaults = device_definition["config_defaults"]
                if "description" in device_definition:
                    device.description = device_definition["description"]
            
            log_debug(self._logger, ("Returning device '{}' for name '{}' from " + 
                                    "object list").format(device, name))

            return device
        if "class_name" in device_definition:
            return self._loadObject(device_definition, controller, 
                                    *constructor_args, **constructor_kwargs)
        else:
            return self._loadFile(device_definition)
    
    def _loadFile(self, device: typing.Mapping) -> "module":
        """
        Load the file defined by the `device`.

        The device has to have a "file_path" and a "name" index.

        Raises
        ------
        DeviceImportError
            When the file is not importable
        StopProgram
            When the a StopProgram is raised anywhere

        Parameters
        ----------
        device : mapping
            The device definition with the file path at the "file_path" index, 
            the class name at "class_name" and the device name at "device"
        
        Returns
        -------
        module
            The module thatis loaded
        """
        
        name = device["name"]
        file_path = device["file_path"]
        
        file_path = os.path.realpath(os.path.expanduser(file_path))
        if os.path.isfile(file_path):
            module_name = os.path.basename(file_path)
        else:
            module_name = file_path
            file_path = None
        
        # import the file
        try:
            if file_path is not None:
                log_debug(self._logger, ("Trying to load module '{}' from file " + 
                                        "'{}' by loading the spec from the file").format(
                                        module_name, file_path))
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                
                log_debug(self._logger, "Trying to load the module from the spec")
                module = importlib.util.module_from_spec(spec)
                
                log_debug(self._logger, "Executing module '{}'".format(module))
                spec.loader.exec_module(module)
            else:
                log_debug(self._logger, ("Loading module '{}' with the importlib " + 
                                        "import_module function").format(module_name))
                module = importlib.import_module(module_name)
        except StopProgram as e:
            log_debug(self._logger, "Stopping program", exc_info=e)
            raise e
        except Exception as e:
            err = DeviceImportError(("Could not import the device '{}' " + 
                                     "because importing '{}' raised a {} " + 
                                     "with the message '{}'.").format(name, 
                                     module_name, e.__class__.__name__, str(e))).with_traceback(e.__traceback__)
            log_error(self._logger, err)
            raise err
        
        return module
    
    def _loadClass(self, device: typing.Mapping, 
                   controller: typing.Optional["Controller"]=None) -> typing.Tuple[type, "module", typing.Union[typing.List[typing.Tuple[str, str]], None]]:
        """
        Load the class (not the object!) defined by the `device`.

        The device has to have a "file_path", "class_name" and "name" index 
        where the first one contains the path to the file to import (either as 
        a string or as a path), the middle one has to contain the class name as
        a string and the last one the name to use for the device.
        
        If the `class_name` class has a `defineConfigurationOptions()` class 
        method and the `controller` is given, the `defineConfigurationOptions()`
        method will be executed with the controllers configuration object. Also
        the `Controller.askIfNotPresentConfigurationOptions()` function will be 
        executed to set all required configuration options if needed.

        Raises
        ------
        DeviceImportError
            When the file is not importable
        DeviceClassNotDefined
            When the module does not define the `class_name`
        StopProgram
            When the class raises a `StopProgram` exception anywhere

        Parameters
        ----------
        device : mapping
            The device definition with the file path at the "file_path" index, 
            the class name at "class_name" and the device name at "device"
        controller : Controller, optional
            The controller object to handle configuration options
        
        Returns
        -------
        type, module, list of tuples or None
            The class, the module and the configuration groups and keys as 
            a list of tuples or None if the `controller` is not given or the 
            class does not define configuration keys
        """
        
        name = device["name"]
        file_path = device["file_path"]
        class_name = device["class_name"]
        
        module = self._loadFile(device)

        # get the class
        try:
            log_debug(self._logger, "Getting class '{}' from module '{}'".format(
                                class_name, module))
            class_ = getattr(module, class_name)
            log_debug(self._logger, "Found class '{}'".format(class_))
        except StopProgram as e:
            log_debug(self._logger, "Stopping program", exc_info=e)
            raise e
        except Exception as e:
            err = DeviceClassNotDefined(("Could not create the device '{}' " + 
                                         "because the class name '{}' could " + 
                                         "not be found in the module '{}'. " + 
                                         "Retrieving it raised a '{}' error " + 
                                         "with the message '{}'.").format(
                                         name, class_name, module, 
                                         e.__class__.__name__, str(e))).with_traceback(e.__traceback__)
            log_error(self._logger, err)
            raise err
        
        # define the configuration options if there are some
        config_keys = None
        if (isinstance(controller, Controller) and 
            hasattr(class_, "defineConfigurationOptions") and 
            callable(class_.defineConfigurationOptions)):
            state_id = controller.configuration.markState()

            log_debug(self._logger, "Defining configuration options of '{}'".format(
                                class_))
            class_.defineConfigurationOptions(controller.configuration,
                                              device["config_group_name"],
                                              device["config_defaults"])

            config_keys = controller.configuration.getAdditions(state_id, True)
            controller.configuration.dropStateMark(state_id)

            # ask all non-existing but required configuration values
            controller.askIfNotPresentConfigurationOptions()
        
        return class_, module, config_keys
    
    def _loadObject(self, device: typing.Mapping, 
                    controller: typing.Optional["Controller"]=None,
                    *constructor_args: typing.Any, 
                    **constructor_kwargs: typing.Any) -> typing.Union["Device", object]:
        """
        Load the object from the `device`.

        The device has to have a "file_path", "class_name" and "name" index 
        where the first one contains the path to the file to import (either as 
        a string or as a path), the middle one has to contain the class name as
        a string and the last one the name to use for the device.

        Additional device values are set to the returned device if the created
        object inherits the `Device` class.

        The `constructor_args` and the `constructor_kwargs` are arguments to 
        pass to the constructor when creating the object.

        If the created object is an instance of the `MicroscopeInterface` or 
        the `CameraInterface`, the first parameter will always be the 
        `controller`.

        Note that this does not necessarily return a `Device` object. That
        depends on whether the loaded class implements the `Device` class or 
        not. The convention is to do so but there may be exceptions.

        Raises
        ------
        DeviceImportError
            When the file is not importable
        DeviceClassNotDefined
            When the module does not define the `class_name`
        DeviceCreationError
            When the `class_name` object could not be created
        StopProgram
            When the class raises a `StopProgram` exception anywhere

        Parameters
        ----------
        device : mapping
            The device definition with the file path at the "file_path" index, 
            the class name at "class_name" and the device name at "device"
        controller : Controller, optional
            The controller object to handle configuration options
        constructor_args : any
            The arguments for the object that is created, if the object is a 
            `MicroscopeInterface` or `CameraInterface` the `controller` will 
            automatically be set to the first argument if the `controller` is 
            given
        constructor_kwargs : any
            The arguments for the object that is created, if the object is a 
            `Device` the `device` dict will automatically be added to the 
            `constructor_kwargs` (and will overwrite same values)
        
        Returns
        -------
        device or object
            The created object
        """

        log_debug(self._logger, "Trying to load object for device '{}'".format(device))
        class_, module, config_keys = self._loadClass(device, controller)
        
        # add the kwargs of the device if the class is a device
        if Device in class_.__mro__:
            allowed_kwargs = ("kind", "name", "config_group_name", 
                              "config_defaults", "description")
            device_kwargs = copy.deepcopy(device)
            keys = tuple(device_kwargs.keys())
            for k in keys:
                if k not in allowed_kwargs:
                    del device_kwargs[k]
            constructor_kwargs.update(device_kwargs)
            log_debug(self._logger, ("Adding '{}' to constructor kwargs because " + 
                                    "device is an instance of the Device class").format(
                                    device_kwargs))

        # add the controller to the args if it is a microscope or camera
        if ((MicroscopeInterface in class_.__mro__ or 
             CameraInterface in class_.__mro__) and 
             isinstance(controller, Controller)):
            constructor_args = list(constructor_args)
            constructor_args.insert(0, controller)

            # microscope and camera interface force the kind to the correct 
            # kind and don't support setting it
            if "kind" in constructor_kwargs:
                del constructor_kwargs["kind"]
            
            log_debug(self._logger, ("Adding controller '{}' to the constructor " + 
                                    "args because device is an instance of " + 
                                    "the MicroscopeInterface or CameraInterface " + 
                                    "class").format(controller))

        # create the object
        try:
            log_debug(self._logger, ("Creating object of class '{}' with args " + 
                                    "'{}' and kwargs '{}'").format(class_,
                                    repr(constructor_args), repr(constructor_kwargs)))
            obj = class_(*constructor_args, **constructor_kwargs)
        except StopProgram as e:
            log_debug(self._logger, "Stopping program", exc_info=e)
            raise e
        except Exception as e:
            # unset the added config keys
            if config_keys is not None and isinstance(controller, Controller):
                log_debug(self._logger, "Removing added configuration keys '{}'".format(
                                    config_keys))
                for group, key in config_keys:
                    controller.configuration.removeElement(group, key)
            
            err = DeviceCreationError(("Could not create the '{}' class " + 
                                       "for the device '{}' from '{}', " + 
                                       "creating raised a '{}' error with " + 
                                       "the message '{}'.").format(
                                            class_.__name__, device["name"], 
                                            module, e.__class__.__name__, 
                                            str(e))).with_traceback(e.__traceback__)
            log_error(self._logger, err)
            raise err
        
        log_debug(self._logger, "Returning created device instance '{}'".format(obj))
        return obj
        