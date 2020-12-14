# python <3.6 does not define a ModuleNotFoundError, use this fallback
from .errors import FallbackModuleNotFoundError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
    DM = None

# for development only
try:
    import dev_constants
    load_from_dev = True
except (FallbackModuleNotFoundError, ImportError) as e:
    load_from_dev = False

if load_from_dev:
    import sys
    if hasattr(dev_constants, "execdmscript_path"):
        if not dev_constants.execdmscript_path in sys.path:
            sys.path.insert(0, dev_constants.execdmscript_path)

import logging
import execdmscript

from .logginglib import log_debug
from .logginglib import get_logger
from .abstract_configuration import AbstractConfiguration

class DMConfiguration(AbstractConfiguration):
    delimiter = ";"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._logger = get_logger(self)

    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        from .config import DM_CONFIGURATION_PERSISTENT_TAG_NAME
        log_debug(self._logger, ("Starting to load configuration from persistent " + 
                                "tag '{}'").format(DM_CONFIGURATION_PERSISTENT_TAG_NAME))
        try:
            tags = execdmscript.get_persistent_tag(DM_CONFIGURATION_PERSISTENT_TAG_NAME)
        except KeyError:
            tags = None

        if isinstance(tags, dict):
            # old saving causes problems when loading, remove values
            if "{{groups}}" in tags:
                del tags["{{groups}}"]
            
            for group in tags:
                if isinstance(tags[group], dict):
                    if "{{keys}}" in tags[group]:
                        del tags[group]["{{keys}}"]
                else:
                    del tags[group]

            log_debug(self._logger, "Loading tags '{}' in abstract configuration".format(
                                tags))
            self.loadFromMapping(tags)
        else:
            log_debug(self._logger, ("Skipping loading because tags are not a " + 
                                "dict but '{}' (type {})").format(tags, type(tags)))
    
    def saveConfiguration(self) -> None:
        """Save the configuration to be persistant."""

        from .config import DM_CONFIGURATION_PERSISTENT_TAG_NAME
        log_debug(self._logger, ("Starting to save configuration to persistent " + 
                                "tag '{}'").format(DM_CONFIGURATION_PERSISTENT_TAG_NAME))

        if DM is not None:
            for group in self.getGroups():
                for key in self.getKeys(group):
                    if self.valueExists(group, key):
                        try:
                            datatype = self.getDatatype(group, key)
                        except KeyError:
                            datatype = str
                        
                        path = "{}:{}:{}".format(
                            DM_CONFIGURATION_PERSISTENT_TAG_NAME, group, key
                        )
                        value = self.getValue(group, key)

                        log_debug(self._logger, ("Saving value '{}' for key '{}' " + 
                                                "in group '{}' with path '{}' " + 
                                                "as a '{}'").format(value, key, 
                                                group, path, datatype))

                        if datatype == int:
                            DM.GetPersistentTagGroup().SetTagAsLong(path, value)
                        elif datatype == float:
                            DM.GetPersistentTagGroup().SetTagAsFloat(path, value)
                        elif datatype == bool:
                            DM.GetPersistentTagGroup().SetTagAsBoolean(path, value)
                        else:
                            if (datatype != str and callable(datatype) and 
                                hasattr(datatype, "format") and 
                                callable(datatype.format)):
                                value = datatype.format(value)
                            
                            DM.GetPersistentTagGroup().SetTagAsString(path, str(value))