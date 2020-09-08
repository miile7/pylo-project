import random
import numpy as np

from .camera_interface import CameraInterface
from ..image import Image

class DummyCamera(CameraInterface):
    """This class represents a dummy camera that records images with random 
    data.

    Attributes
    ----------
    tags : dict
        Any values that should be saved for the camera
    controller : Controller
        The controller
    imagesize : tuple of int
        The image size
    """

    def __init__(self, controller: "Controller") -> None:
        """Create a new camera interface object.
        
        Parameters
        ----------
        controller : Controller
            The controller
        """
        self.imagesize = (32, 32)
        self.tags = {}
        self.controller = controller
    
    def recordImage(self) -> "Image":
        """Get the image of the current camera.

        Returns
        -------
        Image
            The image object
        """

        image_data = np.random.rand(self.imagesize[0], self.imagesize[1])
        image_data = (image_data * 255).astype(dtype=np.uint8)

        image_tags = {}

        for i in range(random.randint(2, 6)):
            if random.randint(0, 1) == 0:
                image_tags[chr(i + 65)] = random.randint(0, 65535)
            else:
                image_tags[chr(i + 65)] = "Test value {}".format(i)
        
        return Image(image_data, image_tags)
    
    def resetToSafeState(self) -> None:
        pass