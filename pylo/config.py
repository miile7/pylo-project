"""The backend configuration file.

This file should be touched only once to set up your environmnet. Configuring
everything else works by settinsg in the configuration.

This file is only for the programming defaults that have to be present before 
the configuration is loaded.

For modifying simply change the value of the constant. The __config_docs__ is 
only for creating the help file. It can be ignored completely
"""

import os
import logging
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
OFFLINE_MODE = None

__config_docs__("MAX_LOOP_COUNT",
"""The number of times the user is asked for the input, this is for avoiding
infinite loops that are caused by any error.
Default: 500
""")
MAX_LOOP_COUNT = 100

__config_docs__("MEASUREMENT_START_TIME",
"""The maximum time in seconds that can pass between the program order to start 
the measurement (in the controller) and the measurement actually starting (in 
the measurement thread). 

This time has nothing to do with pyhsical waiting times but is only for thread 
synchronization. The controller thread starts the measurement thread and the 
goes into an "idle" state where it waits for the measurement to end checking
the measurement status. But creating the measurement thread and then starting
it takes longer than the controller waiting for it. This means the controller 
checks the measurement status before the measurement has started. That again 
leads to starting the measurement without surveilling it. The measurement can 
then not be aborted.
Default: 1
""")
MEASUREMENT_START_TIMEOUT = 1

__config_docs__("TIFF_IMAGE_TAGS_INDEX",
"""The hexadecimal entry for tiff images where to save the tags as a json to
Default: 0x010e (The image description)
""")
TIFF_IMAGE_TAGS_INDEX = 0x010e

__config_docs__("DEFAULT_USER_DIRECTORY",
"""The path to save program data in.
Default: os.path.join(os.path.expanduser("~"), PROGRAM_NAME.lower())
""")
DEFAULT_USER_DIRECTORY = os.path.join(os.path.expanduser("~"), PROGRAM_NAME.lower())

__config_docs__("PROGRAM_LOG_FILE",
"""The path to the log file to log all program events. This is for debugging
only.
Default: os.path.join(DEFAULT_USER_DIRECTORY, "{:%Y-%m-%d_%H-%M-%S}.log.csv".format(datetime.datetime.now()))
""")
PROGRAM_LOG_FILE = os.path.join(DEFAULT_USER_DIRECTORY, "{:%Y-%m-%d_%H-%M-%S}.log.csv".format(datetime.datetime.now()))

__config_docs__("ENABLED_PROGRAM_LOG_LEVELS",
"""The log levels defined in the `logging` module to log. Note that DEBUG logs 
go in a csv log file. All other logs go in the same csv file and into the
current output.

This value should only be changed for debugging!

For debugging use the tuple `(logging.CRITICAL, logging.ERROR, logging.WARNING, 
logging.INFO, logging.DEBUG, logging.NOTSET)`. For normal use use the default

Default: (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO)
""")
ENABLED_PROGRAM_LOG_LEVELS = (logging.CRITICAL, logging.ERROR, logging.WARNING, 
                              logging.INFO, logging.DEBUG, logging.NOTSET)

__config_docs__("DEFAULT_SAVE_DIRECTORY",
"""The path to save the images to if the user does not change it
Default: os.path.join(os.path.expanduser("~"), "pylo", "measurements")
""")
DEFAULT_SAVE_DIRECTORY = os.path.join(DEFAULT_USER_DIRECTORY, "measurements", __path_time)

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
Default: os.path.join(DEFAULT_USER_DIRECTORY, "configuration.ini")
""")
DEFAULT_INI_PATH = os.path.join(DEFAULT_USER_DIRECTORY, "configuration.ini")

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
Default: PROGRAM_NAME.lower()
""")
DM_CONFIGURATION_PERSISTENT_TAG_NAME = PROGRAM_NAME.lower()

__config_docs__("DEFAULT_DM_SHOW_IMAGES_ROW_COUNT",
"""The number of rows of images if the `DEFAULT_DM_SHOW_IMAGES` is True, the 
columns will be calculated automatically.
Default: 2
""")
DEFAULT_DM_SHOW_IMAGES_ROW_COUNT = 2

__config_docs__("PROGRAM_DATA_DIRECTORIES",
"""Paths where program data is expected.
""")
PROGRAM_DATA_DIRECTORIES = {
    os.path.expanduser("~"),
    DEFAULT_USER_DIRECTORY,
    os.getcwd()
}
try:
    # /pylo/
    PROGRAM_DATA_DIRECTORIES.add(os.path.dirname(__file__))
    # /
    PROGRAM_DATA_DIRECTORIES.add(os.path.dirname(os.path.dirname(__file__)))
except NameError:
    # __file__ does not exist
    pass

__config_docs__("CUSTOM_TAGS_GROUP_NAME",
"""The group name to save the custom tags with in the configuration.
Default: "custom-tags"
""")
CUSTOM_TAGS_GROUP_NAME = "custom-tags"

__config_docs__("KEEP_REMOVED_DIVICE_SETTINGS",
"""When the camera or the microscope change, this defines whether the 
corresponding configuration group is kept (True) or removed (False). If 
multiple microscopes or cameras are used, this may be useful to prevent setting
settings over and over again. On the other hand this may lead to unexpected 
pre-sets and clutter up the configuration and image tags.
Default: True
""")
KEEP_REMOVED_DIVICE_SETTINGS = True

__config_docs__("DM_IMAGE_ANNOTATION_COLOR",
"""The foreground color to use for annotations in dm images as an rgb tuple 
where each color is defined with a value between [0..1].
Default: (0, 1, 0)
""")
DM_IMAGE_ANNOTATION_COLOR = (0, 1, 0)

__config_docs__("DM_IMAGE_ANNOTATION_PADDING_FRACTION",
"""The padding to use for annotations as a fraction. For vertical paddings the
`DM_IMAGE_ANNOTATION_PADDING_FRACTION` will be multiplied with the image height,
for horizontal paddings with the image width
Default: 1/50
""")
DM_IMAGE_ANNOTATION_PADDING_FRACTION = 1/50

__config_docs__("DM_IMAGE_ANNOTATION_SCALEBAR_LENGTH_FRACTION",
"""The length of the scalebar as a fraction of the image width.
Default: 1/5
""")
DM_IMAGE_ANNOTATION_SCALEBAR_LENGTH_FRACTION = 1/5

__config_docs__("DM_IMAGE_ANNOTATION_HEIGHT_FRACTION",
"""The height of the annotations as a fraction of the image height
Default: 1/20
""")
DM_IMAGE_ANNOTATION_HEIGHT_FRACTION = 1/20

__config_docs__("DM_IMAGE_DISABLE_PYTHON_ANNOTATIONS",
"""Whether to add the image annotations by hybrid scripting only if the images 
are shown. This has to be True at the moment since adding annotations does not 
work at all in python. For more details check out DMImage._addAnnotations()
Default: True
""")
DM_IMAGE_DISABLE_PYTHON_ANNOTATIONS = True