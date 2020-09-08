"""The backend configuration file.

This file should be touched only once to set up your environmnet. Configuring
everything else works by settinsg in the configuration.

This file is only for the programming defaults that have to be present before 
the configuration is loaded.

For modifying simply change the value of the constant. The __config_docs__ is 
only for creating the help file. It can be ignored completely
"""

import os
import datetime

__path_time = "{:%Y-%m-%d_%H-%M-%S}".format(datetime.datetime.now())

from . import __Docs
__config_docs__ = __Docs()

__config_docs__("PROGRAM_NAME",
"""The name of the program to use
Default: "PyLo"
""")
PROGRAM_NAME = "PyLo"

__config_docs__("OFFLINE_MODE",
"""Use True to ignore cameras and microscopes and use dummy objects instead, 
use False to force using the provided cameras and microscopes. If there are 
none, an error is raised. Use None for using the offline mode as fallback if 
the online mode does not work.

On your microscope computer you should set this to True. For developing you can
either use None or False. If you are devloping on your microscope computer you 
may want to use False.

Note that the implementation depends on the microscope class!
Default: None
""")
OFFLINE_MODE = True

__config_docs__("TIFF_IMAGE_TAGS_INDEX",
"""The hexadecimal entry for tiff images where to save the tags as a json to
Default: 0x010e (The image description)
""")
TIFF_IMAGE_TAGS_INDEX = 0x010e

__config_docs__("DEFAULT_SAVE_DIRECTORY",
"""The path to save the images to if the user does not change it
Default: os.path.join(os.path.expanduser("~"), "pylo", "measurements")
""")
DEFAULT_SAVE_DIRECTORY = os.path.join(os.path.expanduser("~"), "pylo", "measurements", __path_time)

__config_docs__("DEFAULT_SAVE_FILE_NAME",
"""The name to use for each file if the user does not change it
Default: "{counter}_{time:%Y-%m-%d_%H-%M-%S}_lorentz-measurement.dm4" 
    (Needs DM-extension for the file extension, use .tif otherwise)
""")
DEFAULT_SAVE_FILE_NAME = "{counter}_{time:%Y-%m-%d_%H-%M-%S}_lorentz-measurement.dm4"

__config_docs__("DEFAULT_LOG_PATH",
"""The default path to save the log to.
Default: os.path.join(DEFAULT_SAVE_DIRECTORY, "measurement.log")
""")
DEFAULT_LOG_PATH = os.path.join(DEFAULT_SAVE_DIRECTORY, "measurement.log")

__config_docs__("DEFAULT_INI_PATH",
"""The path to save the ini configuration to, if used.
Default: os.path.join(os.path.expanduser("~"), "pylo", "configuration.ini")
""")
DEFAULT_INI_PATH = os.path.join(os.path.expanduser("~"), "pylo", "configuration.ini")

__config_docs__("CONFIGURATION",
"""The configuration object to use
Default: DMConfiguration (Needs Digital Micrograph extension)
""")
CONFIGURATION = None

__config_docs__("VIEW",
"""The view object to use
Default: DMView (Needs Digital Micrograph extension)
""")
VIEW = None

__config_docs__("DEFAULT_MICROSCOPE_TO_SAFE_STATE_AFTER_MEASUREMENT",
"""Whether to set the microscope to the safe state after the measurement has 
finished or not.
Default: False
""")
DEFAULT_MICROSCOPE_TO_SAFE_STATE_AFTER_MEASUREMENT = False

__config_docs__("DEFAULT_CAMERA_TO_SAFE_STATE_AFTER_MEASUREMENT",
"""Whether to set the camera to the safe state after the measurement has 
finished or not.
Default: False
""")
DEFAULT_CAMERA_TO_SAFE_STATE_AFTER_MEASUREMENT = False

__config_docs__("DEFAULT_RELAXATION_TIME",
"""The time in seconds to wait after the microscope has been set to the 
lorentz mode and before starting the measurement.
Default: 10
""")
DEFAULT_RELAXATION_TIME = 0

__config_docs__("DM_CONFIGURATION_PERSISTENT_TAG_NAME",
"""The tag name in the persistent tags to use to save all the settings in.
Default: "pylo"
""")
DM_CONFIGURATION_PERSISTENT_TAG_NAME = "pylo"

__config_docs__("DEFAULT_DM_CAMERA_EXPOSURE_TIME",
"""The exposure time of the camera in seconds.
Default: 0.1
""")
DEFAULT_DM_CAMERA_EXPOSURE_TIME = 0.1

__config_docs__("DEFAULT_DM_CAMERA_BINNING_X",
"""The hardware binning of pixels in x direction.
Default: 1
""")
DEFAULT_DM_CAMERA_BINNING_X = 1

__config_docs__("DEFAULT_DM_CAMERA_BINNING_Y",
"""The hardware binning of pixels in y direction.
Default: 1
""")
DEFAULT_DM_CAMERA_BINNING_Y = 1

__config_docs__("DEFAULT_DM_PROCESS_LEVEL",
"""The process level, use 1 for 'unprocessed', 2 for 'dark subtracted' and 3 
for 'gain normalized'.
Default: 1
""")
DEFAULT_DM_PROCESS_LEVEL = 1

__config_docs__("DEFAULT_DM_CCD_READOUT_AREA_TOP",
"""The top coordinate of the CCD readout area.
Default: 0
""")
DEFAULT_DM_CCD_READOUT_AREA_TOP = 0

__config_docs__("DEFAULT_DM_CCD_READOUT_AREA_RIGHT",
"""The right coordinate of the CCD readout area.
Default: 4096
""")
DEFAULT_DM_CCD_READOUT_AREA_RIGHT = 4096

__config_docs__("DEFAULT_DM_CCD_READOUT_AREA_BOTTOM",
"""The bottom coordinate of the CCD readout area.
Default: 4096
""")
DEFAULT_DM_CCD_READOUT_AREA_BOTTOM = 4096

__config_docs__("DEFAULT_DM_CCD_READOUT_AREA_LEFT",
"""The left coordinate of the CCD readout area.
Default: 0
""")
DEFAULT_DM_CCD_READOUT_AREA_LEFT = 0
