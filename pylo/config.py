"""The backend configuration file.

This file should be touched only once to set up your environmnet. Configuring
everything else works by settinsg in the configuration.

This file is only for the programming defaults that have to be present before 
the configuration is loaded.
"""

import os

# The name of the program to use
# Default: "PyLo"
PROGRAM_NAME = "PyLo"

# The hexadecimal entry for tiff images where to save the tags as a json to
# Default: 0x010e (The image description)
TIFF_IMAGE_TAGS_INDEX = 0x010e

# The path to save the images to if the user does not change it
# Default: os.path.join(os.path.expanduser("~"), "pylo-measurements")
DEFAULT_SAVE_DIRECTORY = os.path.join(os.path.expanduser("~"), "pylo-measurements")

# The name to use for each file if the user does not change it
# Default: "{counter}_{time:%Y-%m-%d_%H-%M-%S}_lorenz-measurement.dm4" (Needs 
# Digital Micrograph extension)
DEFAULT_SAVE_FILE_NAME = "{counter}_{time:%Y-%m-%d_%H-%M-%S}_lorenz-measurement.dm4"