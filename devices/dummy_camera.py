import copy
import typing
import random
import numpy as np

from pylo import Image
from pylo import CameraInterface

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
    use_dummy_images : bool
        Whether to use image objects created from the `DummyImage` class or 
        normal `pylo.Image` objects
    """

    def __init__(self, *args, **kwargs) -> None:
        """Create a new camera interface object."""
        super(DummyCamera, self).__init__(*args, **kwargs)
        self.imagesize = (32, 32)
        self.tags = {"Camera": "Dummy Camera"}
        self.use_dummy_images = False
    
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

        image_data = np.random.rand(self.imagesize[0], self.imagesize[1])
        image_data = (image_data * 255).astype(dtype=np.uint8)

        if isinstance(additional_tags, dict):
            image_tags = copy.deepcopy(additional_tags)
        else:
            image_tags = {}

        for i in range(random.randint(2, 6)):
            if random.randint(0, 1) == 0:
                image_tags[chr(i + 65)] = random.randint(0, 65535)
            else:
                image_tags[chr(i + 65)] = "Test value {}".format(i)
        
        if self.use_dummy_images:
            return DummyImage(image_data, image_tags)
        else:
            return Image(image_data, image_tags)

    
    def resetToSafeState(self) -> None:
        pass

class DummyImage(Image):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    """An image object that cannot save itself."""
    def saveTo(self, *args, **kwargs):
        pass