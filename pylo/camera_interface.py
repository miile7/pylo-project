import typing

from .device import Device
from .vulnerable_machine import VulnerableMachine

class CameraInterface(Device, VulnerableMachine):
    """This class represents the camera.

    Attributes
    ----------
    tags : dict
        Any values that should be saved for the camera
    controller : Controller
        The controller
    """

    def __init__(self, controller: "Controller", name: typing.Optional[str]=None, 
                 config_group_name: typing.Optional[str]=None, 
                 config_defaults: typing.Optional[dict]={}, 
                 description: typing.Optional[str]="") -> None:
        """Create a new camera interface object.

        Parameters
        ----------
        controller : Controller
            The controller
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
        super(CameraInterface, self).__init__(kind="camera", 
            name=name, config_group_name=config_group_name,
            config_defaults=config_defaults, description=description)
        
        self.tags = {}
        self.controller = controller
    
    def recordImage(self, additional_tags: typing.Optional[dict]=None, **kwargs) -> "Image":
        """Get the image of the current camera.

        Parameters
        ----------
        additional_tags : dict, optional
            Additonal tags to add to the image, note that they will be 
            overwritten by other tags if there are set tags in this method

        Returns
        -------
        Image
            The image object
        """

        raise NotImplementedError()