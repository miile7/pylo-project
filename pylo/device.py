import re
import typing

class Device:
    """This class wraps a device, e.g. a camera or a microscope.

    Attributes
    ----------
    kind : str
        The kind, at the moment "camera" and "microscope" are supported
    name : str
        The name to show in the GUI and to use to load this device
    configuration_group : str
        The group name this device should use to save persistent values in the 
        configuration
    configuration_defaults : dict
        The default values that this device has which can be used internally,
        optiona, default: {}
    description : str
        A description for this device, currently not used, default: ""
    """

    def __init__(self, kind: str, name: typing.Optional[str]=None, 
                 configuration_group: typing.Optional[str]=None, 
                 configuration_defaults: typing.Optional[dict]={}, 
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
        configuration_group : str, optional
            The group name this device should use to save persistent values in
            the configuration, if not a str the `name` is used where camel case
            is converted to minuses, default: None
        configuration_defaults : dict, optional
            The default values that this device has which can be used internally,
            optiona, default: {}
        description : str, optional
            A description for this device, currently not used, default: ""
        """
        super(Device, self).__init__()
        self.kind = kind

        if not isinstance(name, str):
            name = str(self.__class__.__name__)
        self.name = name
        
        if not isinstance(configuration_group, str):
            # split by upper case letters, and join with minus
            configuration_group = "-".join(map(lambda x: x.lower(), 
                re.findall(r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", name)))
        self.configuration_group = configuration_group

        self.configuration_defaults = configuration_defaults
        self.description = description