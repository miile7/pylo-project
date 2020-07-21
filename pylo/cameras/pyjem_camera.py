try:
    from PyJEM.detector import Detector
    from PyJEM.detector.function import get_attached_detector
except Exception:
    from PyJEM.offline.detector import Detector
    from PyJEM.offline.detector.function import get_attached_detector

from PIL import Image as PILImage
import numpy as np

from .camera_interface import CameraInterface
from ..image import Image

CONFIG_PYJEM_CAMERA_GROUP = "pyjem-camera"

class PyJEMCamera(CameraInterface):
    """This class represents the camera.

    Attributes
    ----------
    tags : dict
        Any values that should be saved for the camera
    """

    def __init__(self, controller: "Controller") -> None:
        """Create a new camera interface object."""
        self.tags = {}

        self.controller = controller

        self._detector_name = self.controller.configuration.getValue(
            CONFIG_PYJEM_CAMERA_GROUP, "detector-name"
        )
        self._image_size = self.controller.configuration.getValue(
            CONFIG_PYJEM_CAMERA_GROUP, "image-size"
        )
        self._detector = Detector(self._detector_name)

        super().__init__()
    
    def recordImage(self) -> "Image":
        """Get the image of the current camera.

        Returns
        -------
        Image
            The image object
        """

        stream = self._detector.snapshot_rawdata()
        image_data = PILImage.frombytes(
            'L', (self._image_size, self._image_size), stream, 'raw'
        )
        image_data = np.array(image_data)

        return Image(image_data)
    
    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration"):
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        """
        
        configuration.addConfigurationOption(
            CONFIG_PYJEM_CAMERA_GROUP, 
            "detector-name",
            # datatype=get_attached_detector(),
            datatype=str,
            ask_if_not_present=True,
            description=("The detector to use to acquire the image."), 
            restart_required=True
        )
        
        configuration.addConfigurationOption(
            CONFIG_PYJEM_CAMERA_GROUP, 
            "image-size",
            datatype=int,
            ask_if_not_present=True,
            description=("The size (width has to be equal to height) of the " + 
                         "image the detector makes in px."), 
            restart_required=True
        )