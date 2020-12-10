import re
import typing
import logging

from .logginglib import do_log
from .logginglib import get_logger

if hasattr(typing, "Literal"):
    device_kinds = typing.Literal["camera", "microscope"]
else:
    device_kinds = str
class Device:
    """This class wraps a device, e.g. a camera or a microscope.

    Attributes
    ----------
    kind : str
        The kind, at the moment "camera" and "microscope" are supported
    name : str
        The name to show in the GUI and to use to load this device
    config_group_name : str
        The group name this device should use to save persistent values in the 
        configuration
    config_defaults : dict
        The default values that this device has which can be used internally,
        optiona, default: {}
    description : str
        A description for this device, currently not used, default: ""
    """

    def __init__(self, kind: device_kinds, name: typing.Optional[str]=None, 
                 config_group_name: typing.Optional[str]=None, 
                 config_defaults: typing.Optional[dict]={}, 
                 description: typing.Optional[str]="") -> None:
        """Create a new device.

        Parameters
        ----------
        kind : str
            The kind, at the moment "camera" and "microscope" are supported
        name : str, optional
            The name to show in the GUI and to use to load this device, if not 
            a str the class name of the `self` is used (which is the child 
            instance if this is called from a child instance)
        config_group_name : str, optional
            The group name this device should use to save persistent values in
            the configuration, if not a str the `name` is used where camel case
            is converted to minuses, default: None
        config_defaults : dict, optional
            The default values that this device has which can be used internally,
            optiona, default: {}
        description : str, optional
            A description for this device, currently not used, default: ""
        """
        super(Device, self).__init__()
        self.kind = kind

        if not isinstance(name, str) or name == "":
            name = Device.getNameOfObject(self)
        self.name = name
        
        if not isinstance(config_group_name, str):
            config_group_name = Device.convertToSnakeCase(self.name)
        self.config_group_name = config_group_name

        self.config_defaults = config_defaults
        self.description = description
        self._logger = get_logger(self)
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Creating device '{}'".format(self))

    @staticmethod
    def getNameOfObject(obj: object) -> str:
        """Get the name of the object which is the class name.

        Parameters
        ----------
        obj : object
            The object
        
        Returns
        -------
        str
            The class name
        """
        return str(obj.__class__.__name__)
    
    @staticmethod
    def convertToSnakeCase(text: str) -> str:
        """Convert the given `text` to be snake-case (with minus).

        Parameters
        ----------
        text : str
            The text to convert, e.g. CamelCase
        
        Returns
        -------
        str
            The snake-cased text
        """
        if not isinstance(text, str):
            return ""
        
        # split by upper case letters, and join with minus
        return "-".join(map(lambda x: x.lower(), 
                        re.findall(r"[A-Z0-9](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", 
                                   text)))