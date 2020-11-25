import typing

from ..vulnerable_machine import VulnerableMachine

class CameraInterface(VulnerableMachine):
    """This class represents the camera.

    Attributes
    ----------
    tags : dict
        Any values that should be saved for the camera
    controller : Controller
        The controller
    """

    def __init__(self, controller: "Controller") -> None:
        """Create a new camera interface object.
        
        Parameters
        ----------
        controller : Controller
            The controller
        """
        self.tags = {}
        self.controller = controller
    
    def recordImage(self, additional_tags: typing.Optional[dict]=None) -> "Image":
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