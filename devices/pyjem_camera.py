import typing

from PIL import Image as PILImage
import numpy as np

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

# for development only
try:
    import dev_constants
    load_from_dev = True
except (ModuleNotFoundError, ImportError) as e:
    load_from_dev = False

if load_from_dev:
    import sys
    if hasattr(dev_constants, "pyjem_path"):
        if not dev_constants.pyjem_path in sys.path:
            sys.path.insert(0, dev_constants.pyjem_path)

from ..config import OFFLINE_MODE
error = None
if OFFLINE_MODE != True:
    try:
        from PyJEM.detector import Detector
        from PyJEM.detector.function import get_attached_detector
    except ImportError as e:
        error = e
if OFFLINE_MODE == True or error is not None:
    from PyJEM.offline.detector import Detector
    from PyJEM.offline.detector.function import get_attached_detector

from pylo import CameraInterface
from pylo import Image

CONFIG_PYJEM_CAMERA_GROUP = "pyjem-camera"

class PyJEMCamera(CameraInterface):
    """This class represents the camera.

    Attributes
    ----------
    tags : dict
        Any values that should be saved for the camera
    """

    def __init__(self, *args, **kwargs) -> None:
        """Create a new camera interface object."""
        super().__init__(*args, **kwargs)

        self._detector_name = None
        self._detector = None
        self._image_size = None
    
    def _loadSettings(self) -> None:
        """Load the settings from the configuration."""

        self._detector_name = self.controller.configuration.getValue(
            CONFIG_PYJEM_CAMERA_GROUP, "detector-name"
        )
        self._image_size = self.controller.configuration.getValue(
            CONFIG_PYJEM_CAMERA_GROUP, "image-size"
        )
        self._detector = Detector(self._detector_name)
    
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

        if None in (self._detector, self._detector_name, self._image_size):
            self._loadSettings()
        
        if isinstance(additional_tags, dict):
            tags = copy.deepcopy(additional_tags)
        else:
            tags = {}

        stream = self._detector.snapshot_rawdata()
        image_data = PILImage.frombytes(
            'L', (self._image_size, self._image_size), stream, 'raw'
        )
        image_data = np.array(image_data)

        return Image(image_data, tags)
    
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