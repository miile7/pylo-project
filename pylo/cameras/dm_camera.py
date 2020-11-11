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

from .camera_interface import CameraInterface
from ..dm_image import DMImage
from ..execution_outside_environment_error import ExecutionOutsideEnvironmentError

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
    raise ExecutionOutsideEnvironmentError("Could not load module execdmscript.")

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

        super(DMCamera, self).__init__(controller)

        self.show_images = None
        self.exposure_time = None
        self.binning_x = None
        self.binning_y = None
        self.process_level = None
        self.ccd_area = None
        self.tags = {}

        from ..config import OFFLINE_MODE

        if DM is not None and not OFFLINE_MODE:
            self.camera = DM.GetActiveCamera()
            self.camera.PrepareForAcquire()
        else:
            self.camera = None
        
        # the workspace id to show the images in if they should be displayed
        self._workspace_id = None
    
    def _loadSettings(self) -> None:
        """Load the settings from the configuration."""
        
        (self.show_images, self.exposure_time, self.binning_x, self.binning_y, 
            self.process_level, *self.ccd_area) = self.controller.getConfigurationValuesOrAsk(
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

        self.tags = {
            "exposureTime": self.exposure_time,
            "binning": {"x": self.binning_x, "y": self.binning_y},
            "processLevel": self.process_level,
            "ccdArea": {"top": self.ccd_area[0], "right": self.ccd_area[1], 
                        "bottom": self.ccd_area[2], "left": self.ccd_area[3]}
        }

    
    def recordImage(self, additional_tags: typing.Optional[dict]=None) -> "DMImage":
        """Get the image of the current camera.

        Parameters
        ----------
        additional_tags : dict, optional
            Additonal tags to add to the image, note that they will be 
            overwritten by other tags if there are set tags in this method

        Returns
        -------
        DMImage
            The image object
        """

        if (None in (self.show_images, self.exposure_time, self.binning_x, 
                     self.binning_y, self.process_level, self.ccd_area, 
                     self.tags)):
            self._loadSettings()
        
        if isinstance(additional_tags, dict):
            tags = copy.deepcopy(additional_tags)
        else:
            tags = {}
        
        tags["camera"] = copy.deepcopy(self.tags)

        image = self.camera.AcquireImage(
            self.exposure_time, self.binning_x, self.binning_y, 
            self.process_level, self.ccd_area[0], self.ccd_area[3],
            self.ccd_area[2], self.ccd_area[1])
        
        # save the image tags
        tags.update(execdmscript.convert_from_taggroup(image.GetTagGroup()))

        # make sure the workspace exists before creating the image
        if self.show_images:
            self._ensureWorkspace()
        
        image = DMImage.fromDMPyImageObject(image, tags)
        image.show_image = self.show_images
        image.workspace_id = self._workspace_id

        return image
    
    def resetToSafeState(self) -> None:
        pass

    def _ensureWorkspace(self, activate_new: typing.Optional[bool]=True, 
                         force_active: typing.Optional[bool]=False) -> None:
        """Ensure that the DMCamera._workspace_id exists.

        If the workspace does not exist, it is created.
        
        Parameters
        ----------
        activate_new : bool, optional
            Whether to set the workspace new as the active one, default: True
        force_active : bool, optional
            Whether to set the workspace as active also if it already exists,
            default: False
        """

        if (not isinstance(self._workspace_id, int) or 
            DM.WorkspaceCountWindows(self._workspace_id) == 0):
            # either the workspace id does not exist or it exists but the user 
            # closed the workspace already
            self._createNewWorkspace(activate_new)
        elif force_active:
            setvars = {
                "wsid": self._workspace_id
            }
            dmscript = "WorkspaceSetActive(wsid);"

            with execdmscript.exec_dmscript(dmscript, setvars=setvars):
                pass
    
    def _createNewWorkspace(self, activate: typing.Optional[bool]=True) -> None:
        """Create a new workspace and save the workspace id.
        
        Parameters
        ----------
        activate : bool, optional
            Whether to set the new workspace as the active one, default: True
        """

        from ..config import PROGRAM_NAME

        # try to find the workspace with the program name, if there is none 
        # create a new one
        dmscript = [
            "number wsid;",
            "number found = 0;",
            "for(number i = 0; i < WorkspaceGetCount(); i++){",
                "wsid = WorkspaceGetFromIndex(i);",
                "string name = WorkspaceGetName(wsid);",
                "if(name == \"{}\"){{".format(execdmscript.escape_dm_string(PROGRAM_NAME)),
                    "found = 1;",
                    "break;",
                "}",
            "}",
            "if(!found){",
                "wsid = WorkspaceAdd(0);",
                "WorkspaceSetName(wsid, \"{}\");".format(execdmscript.escape_dm_string(PROGRAM_NAME)),
            "}",
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
            CONFIG_DM_CAMERA_GROUP, "show-images", 
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
