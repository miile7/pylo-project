import sys
import copy
import math
import typing
import logging

import numpy as np

# python <3.6 does not define a ModuleNotFoundError, use this fallback
from pylo import FallbackModuleNotFoundError

from pylo import DMImage
from pylo import logginglib
from pylo import CameraInterface
from pylo import ExecutionOutsideEnvironmentError
from pylo import pylolib

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
    
    Class Attributes
    ----------------
    workspace_number : int
        The number of workspaces that were created
    """

    workspace_number = 0

    def __init__(self, *args, **kwargs) -> None:
        """Create a new dm camera object."""

        super(DMCamera, self).__init__(*args, **kwargs)

        self._logger = logginglib.get_logger(self)
        self.show_images = None
        self.annotations_height_fraction = None
        self.exposure_time = None
        self.binning_x = None
        self.binning_y = None
        self.process_level = None
        self.ccd_area = None
        self.tags = {}

        from pylo.config import OFFLINE_MODE

        if DM is not None and not OFFLINE_MODE:
            logginglib.log_debug(self._logger, "Getting active DigitalMicrograph.Py_Camera")
            self.camera = DM.GetActiveCamera()
            
            logginglib.log_debug(self._logger, "Preparing camera")
            self.camera.PrepareForAcquire()
        else:
            self.camera = None
        
        DMCamera.workspace_number = DMCamera.getNumberOfWorkspaces()
        
        # the workspace id to show the images in if they should be displayed
        self._workspace_id = None
        # self._ensureWorkspace()
    
    def _loadSettings(self) -> None:
        """Load the settings from the configuration."""
        
        logginglib.log_debug(self._logger, "Loading settings from configuration and " + 
                               "preparing tags")
        
        (self.show_images, self.annotations_height_fraction, self.exposure_time, 
            self.binning_x, self.binning_y, self.process_level, 
            *self.ccd_area) = self.controller.getConfigurationValuesOrAsk(
            (self.config_group_name, "show-images"),
            (self.config_group_name, "annotations-height"),
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

    def recordImage(self, additional_tags: typing.Optional[dict]=None,
                    **annotation_kwargs) -> "DMImage":
        """Get the image of the current camera.

        Parameters
        ----------
        additional_tags : dict, optional
            Additonal tags to add to the image, note that they will be 
            overwritten by other tags if there are set tags in this method
        annotation_kwargs : dict, optional
            The annotation kwargs, those are used for the 
            `pylolib.expand_vars()` function, note that the 'tags' and the 
            'controller' will be overwritten, default: None

        Returns
        -------
        DMImage
            The image object
        """

        if (None in (self.show_images, self.exposure_time, self.binning_x, 
                     self.binning_y, self.process_level, self.ccd_area, 
                     self.tags, self.annotations_height_fraction)):
            self._loadSettings()
        
        if isinstance(additional_tags, dict):
            tags = copy.deepcopy(additional_tags)
        else:
            tags = {}
        
        tags["camera"] = copy.deepcopy(self.tags)

        logginglib.log_debug(self._logger, ("Acquiring image with exposure " + 
                                            "time '{}', binning '{}', process " + 
                                            "level '{}' and ccd area " + 
                                            "'{}'").format(self.exposure_time, 
                                            (self.binning_x, self.binning_y), 
                                            self.process_level, self.ccd_area))
        
        image = self.camera.AcquireImage(
            self.exposure_time, self.binning_x, self.binning_y, 
            self.process_level, self.ccd_area[0], self.ccd_area[3],
            self.ccd_area[2], self.ccd_area[1])
        
        logginglib.log_debug(self._logger, "Getting image tags, converting " + 
                                           "from DigitalMicrograph.Py_TagGroup "+ 
                                           "to dict")
        
        # save the image tags
        tags.update(execdmscript.convert_from_taggroup(image.GetTagGroup()))

        logginglib.log_debug(self._logger, ("Image tags are now '{}'").format(tags))
        
        # make sure the workspace exists before creating the image
        if self.show_images:
            self._ensureWorkspace()

        logginglib.log_debug(self._logger, ("Creating image object for " + 
                                            "DigitalMicrograph.Py_Image " + 
                                            "object"))
        
        annotations = self.controller.configuration.getValue(
            self.config_group_name, "image-annotations")
        
        if isinstance(annotations, str):
            logginglib.log_debug(self._logger, "Adding annotations '{}'".format(
                                                annotations))
            if not isinstance(annotation_kwargs, dict):
                annotation_kwargs = {}
            
            annotation_kwargs["tags"] = tags
            annotation_kwargs["controller"] = self.controller

            try:
                annotations = list(filter(lambda a: a != "", 
                                pylolib.expand_vars(*annotations.split("|"), 
                                        **annotation_kwargs)))
            except ValueError as e:
                err = ValueError("The annotations cannot be set because they " + 
                                 "are not formatted properly: '{}'".format(annotations))
                logginglib.log_debug(self._logger, err)
                raise err from e
            
            logginglib.log_debug(self._logger, ("Processing annotations to " + 
                                                "'{}'").format(annotations))
        else:
            logginglib.log_debug(self._logger, "No annotations found, no " + 
                                               "annotations are added")
        
        image = DMImage.fromDMPyImageObject(image, tags)
        image.show_image = self.show_images
        image.workspace_id = self._workspace_id
        image.annotations = annotations
        image.annotations_height_fraction = self.annotations_height_fraction

        logginglib.log_debug(self._logger, "Image is now '{}'".format(image))

        return image
    
    def resetToSafeState(self) -> None:
        """Move the camera to a safe state by retracting it."""
        
        logginglib.log_debug(self._logger, "Trying to retract the camera")
        if self.camera.IsRetractable():
            self.camera.SetInserted(False)
            logginglib.log_debug(self._logger, "Retracted camera")
        else:
            logginglib.log_debug(self._logger, "Retracting camera is not " + 
                                               "allowed by this camera")

    def _ensureWorkspace(self, name: typing.Optional[str]=None,
                         activate_new: typing.Optional[bool]=True, 
                         force_active: typing.Optional[bool]=False) -> None:
        """Ensure that the `DMCamera._workspace_id` exists.

        If the workspace does not exist, it is created.
        
        Parameters
        ----------
        name : str, optional
            The workspace name, if not given the `config.PROGRAM_NAME` with a
            trailing number is used, default: None
        activate_new : bool, optional
            Whether to set the workspace new as the active one, default: True
        force_active : bool, optional
            Whether to set the workspace as active also if it already exists,
            default: False
        """

        logginglib.log_debug(self._logger, ("Checking if workspace id '{}' " + 
                                            "is valid").format(self._workspace_id))

        if (not isinstance(self._workspace_id, int) or 
            DM.WorkspaceCountWindows(self._workspace_id) == 0):
            # either the workspace id does not exist or it exists but the user 
            # closed the workspace already
            logginglib.log_debug(self._logger, ("Workspace with id '{}' does " + 
                                                "not exist, creating a new " + 
                                                "one.").format(self._workspace_id))

            self._createNewWorkspace(activate_new)

            # reset shown images if a new workspace is created
            DMImage.shown_images_counter = 0
        elif force_active:
            setvars = {
                "wsid": self._workspace_id
            }
            dmscript = "WorkspaceSetActive(wsid);"

            logginglib.log_debug(self._logger, ("Forcing workspace to be " + 
                                                "active by executing " + 
                                                "dmscript '{}' with setvars " + 
                                                "'{}'").format(dmscript, setvars))

            with execdmscript.exec_dmscript(dmscript, setvars=setvars):
                pass
    
    def _createNewWorkspace(self, name: typing.Optional[str]=None,
                            activate: typing.Optional[bool]=True) -> typing.Tuple[int, str]:
        """Create a new workspace and save the workspace id.
        
        Parameters
        ----------
        name : str, optional
            The workspace name, if not given the `config.PROGRAM_NAME` with a
            trailing number is used, default: None
        activate : bool, optional
            Whether to set the new workspace as the active one, default: True
        
        Returns
        -------
        int, str
            The id of the new workspace and the name
        """

        from pylo.config import PROGRAM_NAME

        if not isinstance(name, str) or name == "":
            name = "{} {}".format(PROGRAM_NAME, DMCamera.workspace_number + 1)

        dmscript = [
            "number wsid = WorkspaceAdd(0);",
            "WorkspaceSetName(wsid, \"{}\");".format(
                execdmscript.escape_dm_string(name)),
        ]

        if activate:
            dmscript.append("WorkspaceSetActive(wsid);")
        
        dmscript = "\n".join(dmscript)

        readvars = {
            "wsid": int
        }

        logginglib.log_debug(self._logger, ("Creating new workspace by " + 
                                            "executing dmscript '{}' with " + 
                                            "readvars '{}'").format(dmscript, 
                                                                    readvars))

        with execdmscript.exec_dmscript(dmscript, readvars=readvars) as script:
            self._workspace_id = script["wsid"]
            DMCamera.workspace_number += 1

        logginglib.log_debug(self._logger, ("New workspace with id '{}' and " + 
                                            "name '{}'.").format(self._workspace_id,
                                                                 name))

        return self._workspace_id, name
    
    @staticmethod
    def getNumberOfWorkspaces() -> int:
        """Get the number of 'Pylo <number>' workspaces

        Returns
        -------
        int
            The number of workspaces whose name starts with the program name
            and ends with a number
        """

        from pylo.config import PROGRAM_NAME

        dmscript = "\n".join((
            "number workspace_number = 0;",
            "for(number i = 0; i < WorkspaceGetCount(); i++){",
                "number wsid = WorkspaceGetFromIndex(i);",
                "string name = WorkspaceGetName(wsid);",
                "if(name.left({}) == \"{}\"){{".format(len(PROGRAM_NAME), execdmscript.escape_dm_string(PROGRAM_NAME)),
                    "name = name.right(name.len() - 1 - {});".format(len(PROGRAM_NAME)),
                    "if(name.val() > workspace_number){",
                        "workspace_number = name.val()",
                    "}",
                "}",
            "}",
        ))

        readvars = {
            "workspace_number": int
        }

        with execdmscript.exec_dmscript(dmscript, readvars=readvars) as script:
            return script["workspace_number"]
        
        return 0

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

        default_camera_settings = DM.GetActiveCamera().GetDefaultParameters()
        # default_camera_settings[0]: exposure: Exposure time in seconds  
        # default_camera_settings[1]: xBin: Hardware binning of pixels in x 
        # direction  
        # default_camera_settings[2]: yBin: Hardware binning of pixels in y 
        # direction  
        # default_camera_settings[3]: processing: Processing level 
        # (unprocessed, dark subtracted, gain normalized) as number  
        # default_camera_settings[4]: top: Top coordinate of the CCD readout 
        # area  
        # default_camera_settings[5]: left: Left coordinate of the CCD readout 
        # area  
        # default_camera_settings[6]: bottom: Bottom coordinate of the CCD 
        # readout area  
        # default_camera_settings[7]: right: Right coordinate of the CCD 
        # readout area  

        if "show-images" not in config_defaults:
            config_defaults["show-images"] = False
        configuration.addConfigurationOption(
            config_group_name, "show-images", 
            datatype=bool, 
            default_value=config_defaults["show-images"], 
            description="Whether to show all acquired images (in a new " + 
            "workspace) or not, they will be saved to a file in both cases."
        )

        if "annotations-height" not in config_defaults:
            from pylo.config import DM_IMAGE_ANNOTATION_HEIGHT_FRACTION
            config_defaults["annotations-height"] = DM_IMAGE_ANNOTATION_HEIGHT_FRACTION
        configuration.addConfigurationOption(
            config_group_name, "annotations-height", 
            datatype=float, 
            default_value=config_defaults["annotations-height"], 
            description=("The height fraction of the annotations shown in the " + 
                         "image, 0 < value <= 1.\n\n" + 
                         "The 'annotations-height' tells how big the " + 
                         "annotations are in the vertical direction. The value " + 
                         "is multiplied with the image height and then used " + 
                         "as the font size and as the height of the scale bar. " + 
                         "To decrease the font size, decrease this value. " + 
                         "The default value is 0.05.")
        )
        
        # the exposure time
        if "exposure-time" not in config_defaults:
            config_defaults["exposure-time"] = default_camera_settings[0]
        configuration.addConfigurationOption(
            config_group_name, "exposure-time", 
            datatype=float, 
            default_value=config_defaults["exposure-time"], 
            description="The exposure time in seconds."
        )
        
        # the binning
        if "binning-x" not in config_defaults:
            config_defaults["binning-x"] = default_camera_settings[1]
        configuration.addConfigurationOption(
            config_group_name, "binning-x", 
            datatype=int, 
            default_value=config_defaults["binning-x"], 
            description="The hardware binning of pixels in x direction."
        )
        
        # the binning
        if "binning-y" not in config_defaults:
            config_defaults["binning-y"] = default_camera_settings[2]
        configuration.addConfigurationOption(
            config_group_name, "binning-y", 
            datatype=int, 
            default_value=config_defaults["binning-y"], 
            description="The hardware binning of pixels in y direction."
        )
        
        # the process level
        if "process-level" not in config_defaults:
            config_defaults["process-level"] = default_camera_settings[3]
        configuration.addConfigurationOption(
            config_group_name, "process-level", 
            datatype=int, 
            default_value=config_defaults["process-level"], 
            description=("The process level, use 1 for 'unprocessed', 2 for " + 
            "'dark subtracted' and 3 for 'gain normalized'.")
        )
        
        # the ccd readout area
        if "ccd-readout-area-top" not in config_defaults:
            config_defaults["ccd-readout-area-top"] = default_camera_settings[4]
        if "ccd-readout-area-right" not in config_defaults:
            config_defaults["ccd-readout-area-right"] = default_camera_settings[7]
        if "ccd-readout-area-left" not in config_defaults:
            config_defaults["ccd-readout-area-left"] = default_camera_settings[5]
        if "ccd-readout-area-bottom" not in config_defaults:
            config_defaults["ccd-readout-area-bottom"] = default_camera_settings[6]
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

        configuration.addConfigurationOption(
            config_group_name, "image-annotations", 
            datatype=str, 
            default_value=("scalebar|{?H={humanstep[ol-current]}, ?}" + 
                           "{?F={humanstep[focus]}, ?}" + 
                           "{?xt={humanstep[x-tilt]}, ?}" + 
                           "{?yt={humanstep[y-tilt]}?}"), 
            description=("The annotations to show in the image, use the pipe " + 
                         "('|') to separate multiple annotations. Use " + 
                         "'scalebar' to add a scalebar. Anything else will " + 
                         "be added as text to the image. " + 
                         pylolib.get_expand_vars_text())
        )
