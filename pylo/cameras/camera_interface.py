from ..vulnerable_machine import VulnerableMachine

class CameraInterface(VulnerableMachine):
    """This class represents the camera.

    Attributes
    ----------
    tags : dict
        Any values that should be saved for the camera
    """

    def __init__(self) -> None:
        """Create a new camera interface object."""
        self.tags = {}
    
    def recordImage(self) -> "Image":
        """Get the image of the current camera.

        Returns
        -------
        Image
            The image object
        """

        raise NotImplementedError()