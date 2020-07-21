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
    
    def recordImage(self) -> "Image":
        """Get the image of the current camera.

        Returns
        -------
        Image
            The image object
        """

        raise NotImplementedError()