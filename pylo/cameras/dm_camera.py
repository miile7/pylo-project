import sys
import copy
import math
import typing

import numpy as np

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
    DM = None

if DM is not None:
    # for development only, execdmscript is another module that is developed
    # separately
    try:
        import dev_constants
        load_from_dev = True
    except (ModuleNotFoundError, ImportError) as e:
        load_from_dev = False

    if load_from_dev:
        if hasattr(dev_constants, "execdmscript_path"):
            if not dev_constants.execdmscript_path in sys.path:
                sys.path.insert(0, dev_constants.execdmscript_path)
            
    import execdmscript
else:
    raise ModuleNotFoundError("Could not load module execdmscript.")

from .camera_interface import CameraInterface
from ..dm_image import DMImage

CONFIG_DM_CAMERA_GROUP = "dm-camera"

class DMCamera(CameraInterface):
    """This class represents a camera that can only be used in Gatan 
    Microscopy Suite.

    Attributes
    ----------
    exposure_time : float
        The exposure time in seconds
    binning_x, binning_y : int
        The x and y hardware binning
    process_level : int
        The process level, 1 for 'unprocessed', 2 for 'dark subtracted' and 3 
        for 'gain normalized'
    ccd_area : tuple of ints
        The area on the ccd chip to use as the image, index 0 is the top 
        coordinate, index 1 the right, index 2 the bottom and index 3 the 
        left coordinate
    show_images : bool, optional
        Whether to show all recorded images in a new workspace or not, 
        default: False
    """

    def __init__(self, controller: "Controller") -> None:
        """Create a new dm camera object.
        
        Parameters
        ----------
        controller : Controller
            The controller
        """

        (self.show_images, self.exposure_time, self.binning_x, self.binning_y, 
            self.process_level, *self.ccd_area) = controller.getConfigurationValuesOrAsk(
            (CONFIG_DM_CAMERA_GROUP, "show-images"),
            (CONFIG_DM_CAMERA_GROUP, "exposure-time"),
            (CONFIG_DM_CAMERA_GROUP, "binning-x"),
            (CONFIG_DM_CAMERA_GROUP, "binning-y"),
            (CONFIG_DM_CAMERA_GROUP, "process-level"),
            (CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-top"),
            (CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-right"),
            (CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-bottom"),
            (CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-left"),
            fallback_default=True, save_if_not_exists=True
        )

        super(DMCamera, self).__init__(controller)

        self.tags = {
            "exposureTime": self.exposure_time,
            "binning": {"x": self.binning_x, "y": self.binning_y},
            "processLevel": self.process_level,
            "ccdArea": {"top": self.ccd_area[0], "right": self.ccd_area[1], 
                        "bottom": self.ccd_area[2], "left": self.ccd_area[3]}
        }

        from ..config import OFFLINE_MODE

        if DM is not None and not OFFLINE_MODE:
            self.camera = DM.GetActiveCamera()
            self.camera.PrepareForAcquire()
        else:
            self.camera = None
        
        # the workspace id to show the images in if they should be displayed
        self._workspace_id = None
        if self.show_images:
            self._createNewWorkspace()
    
    def recordImage(self) -> "DMImage":
        """Get the image of the current camera.

        Returns
        -------
        DMImage
            The image object
        """
        
        camera_tags = {"camera": copy.deepcopy(self.tags)}

        image = self.camera.AcquireImage(
            self.exposure_time, self.binning_x, self.binning_y, 
            self.process_level, self.ccd_area[0], self.ccd_area[3],
            self.ccd_area[2], self.ccd_area[1])
        
        image = DMImage.fromDMPyImageObject(image, camera_tags)
        image.show_image = self.show_images
        image.workspace_id = self._workspace_id

        return image
    
    def resetToSafeState(self) -> None:
        pass
    
    def _createNewWorkspace(self, activate: typing.Optional[bool]=True) -> None:
        """Create a new workspace and save the workspace id.
        
        Parameters
        ----------
        activate : bool, optional
            Whether to set the new workspace as the active one, default: True
        """

        from ..config import PROGRAM_NAME

        dmscript = [
            "number wsid = WorkspaceAdd(0);",
            "WorkspaceSetName(wsid, \"{}\");".format(PROGRAM_NAME),
        ]

        if activate:
            dmscript.append("WorkspaceSetActive(wsid);")
        
        dmscript = "\n".join(dmscript)

        readvars = {
            "wsid": int
        }

        with execdmscript.exec_dmscript(dmscript, readvars=readvars) as script:
            self._workspace_id = script["wsid"]

    @staticmethod
    def defineConfigurationOptions(configuration: "AbstractConfiguration") -> None:
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        """

        # import as late as possible to allow changes by extensions
        from ..config import DEFAULT_DM_SHOW_IMAGES
        from ..config import DEFAULT_DM_CAMERA_EXPOSURE_TIME
        from ..config import DEFAULT_DM_CAMERA_BINNING_X
        from ..config import DEFAULT_DM_CAMERA_BINNING_Y
        from ..config import DEFAULT_DM_PROCESS_LEVEL
        from ..config import DEFAULT_DM_CCD_READOUT_AREA_TOP
        from ..config import DEFAULT_DM_CCD_READOUT_AREA_RIGHT
        from ..config import DEFAULT_DM_CCD_READOUT_AREA_BOTTOM
        from ..config import DEFAULT_DM_CCD_READOUT_AREA_LEFT

        configuration.addConfigurationOption(
            DEFAULT_DM_SHOW_IMAGES, "show-images", 
            datatype=bool, 
            default_value=DEFAULT_DM_SHOW_IMAGES, 
            description="Whether to show all acquired images (in a new " + 
            "workspace) or not, they will be saved to a file in both cases."
        )
        
        # the exposure time
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "exposure-time", 
            datatype=float, 
            default_value=DEFAULT_DM_CAMERA_EXPOSURE_TIME, 
            description="The exposure time in seconds."
        )
        
        # the binning
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "binning-x", 
            datatype=int, 
            default_value=DEFAULT_DM_CAMERA_BINNING_X, 
            description="The hardware binning of pixels in x direction."
        )
        
        # the binning
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "binning-y", 
            datatype=int, 
            default_value=DEFAULT_DM_CAMERA_BINNING_Y, 
            description="The hardware binning of pixels in y direction."
        )
        
        # the process level
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "process-level", 
            datatype=int, 
            default_value=DEFAULT_DM_PROCESS_LEVEL, 
            description=("The process level, use 1 for 'unprocessed', 2 for " + 
            "'dark subtracted' and 3 for 'gain normalized'.")
        )
        
        # the ccd readout area
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-top", 
            datatype=int, 
            default_value=DEFAULT_DM_CCD_READOUT_AREA_TOP, 
            description="The top coordinate of the CCD readout area"
        )
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-right", 
            datatype=int, 
            default_value=DEFAULT_DM_CCD_READOUT_AREA_RIGHT, 
            description="The right coordinate of the CCD readout area"
        )
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-bottom", 
            datatype=int, 
            default_value=DEFAULT_DM_CCD_READOUT_AREA_BOTTOM, 
            description="The bottom coordinate of the CCD readout area"
        )
        configuration.addConfigurationOption(
            CONFIG_DM_CAMERA_GROUP, "ccd-readout-area-left", 
            datatype=int, 
            default_value=DEFAULT_DM_CCD_READOUT_AREA_LEFT, 
            description="The left coordinate of the CCD readout area"
        )
