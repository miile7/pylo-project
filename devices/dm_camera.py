import sys
import copy
import math
import typing

import numpy as np

# python <3.6 does not define a ModuleNotFoundError, use this fallback
from pylo import FallbackModuleNotFoundError

from pylo import DMImage
from pylo import CameraInterface
from pylo import ExecutionOutsideEnvironmentError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
    DM = None

if DM is not None:
    # for development only, execdmscript is another module that is developed
    # separately
    try:
        import dev_constants
        load_from_dev = True
    except (FallbackModuleNotFoundError, ImportError) as e:
        load_from_dev = False

    if load_from_dev:
        if hasattr(dev_constants, "execdmscript_path"):
            if not dev_constants.execdmscript_path in sys.path:
                sys.path.insert(0, dev_constants.execdmscript_path)
            
    import execdmscript
else:
    raise ExecutionOutsideEnvironmentError("Could not load module execdmscript.")

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

    def __init__(self, *args, **kwargs) -> None:
        """Create a new dm camera object."""

        super(DMCamera, self).__init__(*args, **kwargs)

        self.show_images = None
        self.exposure_time = None
        self.binning_x = None
        self.binning_y = None
        self.process_level = None
        self.ccd_area = None
        self.tags = {}

        from pylo.config import OFFLINE_MODE

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
            (self.config_group_name, "show-images"),
            (self.config_group_name, "exposure-time"),
            (self.config_group_name, "binning-x"),
            (self.config_group_name, "binning-y"),
            (self.config_group_name, "process-level"),
            (self.config_group_name, "ccd-readout-area-top"),
            (self.config_group_name, "ccd-readout-area-right"),
            (self.config_group_name, "ccd-readout-area-bottom"),
            (self.config_group_name, "ccd-readout-area-left"),
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

            # reset shown images if a new workspace is created
            DMImage.shown_images_counter = 0
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

        from pylo.config import PROGRAM_NAME

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
    def defineConfigurationOptions(configuration: "AbstractConfiguration", 
                                   config_group_name: typing.Optional[str]="dm-camera",
                                   config_defaults: typing.Optional[dict]={}) -> None:
        """Define which configuration options this class requires.

        Parameters
        ----------
        configuration : AbstractConfiguration
            The configuration to define the required options in
        config_group_name : str, optional
            The group name this device should use to save persistent values in
            the configuration, this is given automatically when loading this
            object as a device, default: "dm-camera"
        config_defaults : dict, optional
            The default values to use, this is given automatically when loading
            this object as a device, default: {}
        """

        if "show-images" not in config_defaults:
            config_defaults["show-images"] = False
        configuration.addConfigurationOption(
            config_group_name, "show-images", 
            datatype=bool, 
            default_value=config_defaults["show-images"], 
            description="Whether to show all acquired images (in a new " + 
            "workspace) or not, they will be saved to a file in both cases."
        )
        
        # the exposure time
        if "exposure-time" not in config_defaults:
            config_defaults["exposure-time"] = 0.5
        configuration.addConfigurationOption(
            config_group_name, "exposure-time", 
            datatype=float, 
            default_value=config_defaults["exposure-time"], 
            description="The exposure time in seconds."
        )
        
        # the binning
        if "binning-x" not in config_defaults:
            config_defaults["binning-x"] = 1
        configuration.addConfigurationOption(
            config_group_name, "binning-x", 
            datatype=int, 
            default_value=config_defaults["binning-x"], 
            description="The hardware binning of pixels in x direction."
        )
        
        # the binning
        if "binning-y" not in config_defaults:
            config_defaults["binning-y"] = 1
        configuration.addConfigurationOption(
            config_group_name, "binning-y", 
            datatype=int, 
            default_value=config_defaults["binning-y"], 
            description="The hardware binning of pixels in y direction."
        )
        
        # the process level
        if "process-level" not in config_defaults:
            config_defaults["process-level"] = 3
        configuration.addConfigurationOption(
            config_group_name, "process-level", 
            datatype=int, 
            default_value=config_defaults["process-level"], 
            description=("The process level, use 1 for 'unprocessed', 2 for " + 
            "'dark subtracted' and 3 for 'gain normalized'.")
        )
        
        # the ccd readout area
        if "ccd-readout-area-top" not in config_defaults:
            config_defaults["ccd-readout-area-top"] = 0
        if "ccd-readout-area-right" not in config_defaults:
            config_defaults["ccd-readout-area-right"] = 4096
        if "ccd-readout-area-left" not in config_defaults:
            config_defaults["ccd-readout-area-left"] = 0
        if "ccd-readout-area-bottom" not in config_defaults:
            config_defaults["ccd-readout-area-bottom"] = 4096
        configuration.addConfigurationOption(
            config_group_name, "ccd-readout-area-top", 
            datatype=int, 
            default_value=config_defaults["ccd-readout-area-top"], 
            description="The top coordinate of the CCD readout area"
        )
        configuration.addConfigurationOption(
            config_group_name, "ccd-readout-area-right", 
            datatype=int, 
            default_value=config_defaults["ccd-readout-area-right"], 
            description="The right coordinate of the CCD readout area"
        )
        configuration.addConfigurationOption(
            config_group_name, "ccd-readout-area-bottom", 
            datatype=int, 
            default_value=config_defaults["ccd-readout-area-bottom"], 
            description="The bottom coordinate of the CCD readout area"
        )
        configuration.addConfigurationOption(
            config_group_name, "ccd-readout-area-left", 
            datatype=int, 
            default_value=config_defaults["ccd-readout-area-left"], 
            description="The left coordinate of the CCD readout area"
        )