import os
import sys
import copy
import typing
import importlib
import configparser

from .errors import DeviceImportError
from .errors import DeviceCreationError
from .errors import DeviceClassNotDefined

from .device import Device
from .device import device_kinds
from .pylolib import path_like
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
    ; The kind, can either be "camera" or "microscope" (others are loaded too
    ; and can be used by plugins ect.)
    kind=microscope 
    ; The path of the python file, can be absolute or relative to this
    ; file location by using "./", use "~" for current user directory, 
    ; path variables are allowed (for windows e.g. %PROGRAMDATA%, ...)
    ; Unix and Windows paths are supported
    file=./path/to/device.py
    ; The name of the class to initialize, has to be defined in the file
    class=DeviceClassName
    ; Whether this device is disabled or not, default is false
    disabled=No
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
        self.device_ini_files = list(ini_file)
        self._device_class_files = []
        self._device_objects = []
    
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
        self._device_class_files.append({
            "kind": kind, 
            "name": name, 
            "file_path": file_path, 
            "class_name": class_name, 
            "config_defaults": config_defaults, 
            "description": description
        })

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
        self._device_objects.append({
            "kind": kind, 
            "name": name, 
            "object": device,
            "config_defaults": config_defaults, 
            "description": description
        })
    
    def _getDeviceDefinitionsFromInis(self) -> typing.List[dict]:
        """Get the devices dicts from the ini files.

        Returns
        -------
        list of dict
            The list of devices that are defined in one of the ini files
        """

        devices = []
        required_keys = {"kind": str, "file": str, "class": str}
        optional_keys = {"description": str, "disabled": bool}

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
                        t = None
                        if key in required_keys:
                            t = required_keys[key]
                        elif key in optional_keys:
                            t = optional_keys[key]
                        elif key.startswith("config-default."):
                            key = key.replace("config-default.", "")
                            dev["config_defaults"][key] = value
                            continue
                        
                        if t == str:
                            dev[key] = value
                        elif t == int:
                            dev[key] = config.getint(name, key)
                        elif t == float:
                            dev[key] = config.getfloat(name, key)
                        elif t == bool:
                            dev[key] = config.getboolean(name, key)

                    # check if all required keys exist and the device is not 
                    # disabled
                    if (len(set(required_keys.keys()) - set(dev.keys())) == 0 and 
                        ("disabled" not in dev or not dev["disabled"])):
                        devices.append(dev)
        
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
    
    def getDevice(self, name: str, controller: typing.Optional["Controller"]=None,
                  *constructor_args: typing.Any, **constructor_kwargs: typing.Any) -> typing.Union["Device", object]:
        """Get the device with the given `name`.

        If the `name` does not exist a ValueError is raised. The available 
        device names can be retrieved by the 
        `DeviceLoader.getInstalledDeviceNames()`.

        This function will look in the `DeviceLoader._device_objects` at first,
        then in the `DeviceLoader._device_class_files` and then in the 
        `DeviceLoader.device_ini_files` to get the correct object. If the 
        object is a `Device` it will be set to the correct name, and 
        configuration defaults.

        Raises
        ------
        ValueError
            When there is no device with the given `name`
        DeviceImportError
            When class is loaded from the file and the file is not importable
        DeviceClassNotDefined
            When class is loaded from the file and the module does not define 
            the `class_name`
        DeviceCreationError
            When class is loaded from the file and the `class_name` object 
            could not be created
        StopProgram
            When class is loaded from the file and the class raises a 
            `StopProgram` exception anywhere
        
        Parameters
        ----------
        name : str
            The name of the device
        constructor_args : any
            The arguments that are passed to the construcor if the device is 
            created
        constructor_kwargs : any
            The keyword arguments that are passed to the constructor if the 
            device is created
        
        Returns
        -------
        Device or object
            The device object if the defined device extends the Device class 
            (should be the case but is not guaranteed) or the object
        """

        for device in self._device_objects:
            try:
                if ("name" in device and device["name"] == name and 
                    "object" in device):
                    if isinstance(device["object"], Device):
                        if "kind" in device:
                            device["object"].kind = device["kind"]
                        if "name" in device:
                            device["object"].name = device["name"]
                        if "config_defaults" in device:
                            device["object"].config_defaults = device["config_defaults"]
                        if "description" in device:
                            device["object"].description = device["description"]
                    return device["object"]
            except (TypeError, AttributeError):
                pass
        
        load_device = None
        for device in self._device_class_files + self._getDeviceDefinitionsFromInis():
            try:
                if ("name" in device and device["name"] == name and 
                    ("class_name" in device or "class" in device) and 
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
                    
                    load_device = device
                    break
            except TypeError:
                pass
        
        if load_device is not None:
            return self._loadClass(load_device, controller, *constructor_args,
                                   **constructor_kwargs)
        else:
            return None
    
    def _loadClass(self, device: typing.Mapping, 
                   controller: typing.Optional["Controller"]=None,
                   *constructor_args: typing.Any, 
                   **constructor_kwargs: typing.Any) -> typing.Union["Device", object]:
        """
        Load the class defined by the `device`.

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
        
        name = device["name"]
        file_path = device["file_path"]
        class_name = device["class_name"]
        
        file_path = os.path.realpath(os.path.expanduser(file_path))
        if os.path.isfile(file_path):
            dir_path = not os.path.dirname(file_path)
            if dir_path in sys.path:
                sys.path.append(dir_path)
            module_name = os.path.basename(file_path)
        else:
            module_name = file_path
            file_path = None
        
        # import the file
        try:
            if file_path is not None:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                module = importlib.import_module(module_name)
        except StopProgram as e:
            raise e
        except Exception as e:
            raise DeviceImportError(("Could not import the device '{}' " + 
                                    "because importing '{}' raised a {} " + 
                                    "with the message '{}'.").format(name, 
                                    module_name, e.__class__.__name__, str(e))) from e

        # get the class
        try:
            class_ = getattr(module, class_name)
        except StopProgram as e:
            raise e
        except Exception as e:
            raise DeviceClassNotDefined(("Could not create the device '{}' " + 
                                         "because the class name '{}' could " + 
                                         "not be found in the module '{}'. " + 
                                         "Retrieving it raised a '{}' error " + 
                                         "with the message '{}'.").format(
                                         name, class_name, module_name, 
                                         e.__class__.__name__, str(e))) from e
        
        # define the configuration options if there are some
        config_keys = None
        if (isinstance(controller, Controller) and 
            hasattr(class_, "defineConfigurationOptions") and 
            callable(class_.defineConfigurationOptions)):
            state_id = controller.configuration.markState()

            class_.defineConfigurationOptions(controller.configuration)

            config_keys = controller.configuration.getAdditions(state_id, True)
            controller.configuration.dropStateMark(state_id)

            # ask all non-existing but required configuration values
            controller.askIfNotPresentConfigurationOptions()
        
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

        # create the object
        try:
            obj = class_(*constructor_args, **constructor_kwargs)
        except StopProgram as e:
            raise e
        except Exception as e:
            # unset the added config keys
            if config_keys is not None and isinstance(controller, Controller):
                for group, key in config_keys:
                    controller.configuration.removeElement(group, key)
            
            raise DeviceCreationError(("Could not create the '{}' class " + 
                                       "for the device '{}' from '{}', " + 
                                       "creating raised a '{}' error with " + 
                                       "the message '{}'.").format(class_name,
                                       name, module_name, e.__class__.__name__,
                                       str(e))) from e
        
        return obj
        