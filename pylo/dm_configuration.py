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

# for development only
try:
    import dev_constants
    load_from_dev = True
except (ModuleNotFoundError, ImportError) as e:
    load_from_dev = False

if load_from_dev:
    import sys
    if hasattr(dev_constants, "execdmscript_path"):
        if not dev_constants.execdmscript_path in sys.path:
            sys.path.insert(0, dev_constants.execdmscript_path)

import execdmscript

from .abstract_configuration import AbstractConfiguration

class DMConfiguration(AbstractConfiguration):
    delimiter = ";"

    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        from .config import DM_CONFIGURATION_PERSISTENT_TAG_NAME
        
        try:
            tags = execdmscript.get_persistent_tag(DM_CONFIGURATION_PERSISTENT_TAG_NAME)
        except KeyError:
            tags = {}

        self.loadFromMapping(tags)
    
    def saveConfiguration(self) -> None:
        """Save the configuration to be persistant."""

        from .config import DM_CONFIGURATION_PERSISTENT_TAG_NAME

        if DM is not None:
            keys = {}
            
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
                            
                            DM.GetPersistentTagGroup().SetTagAsString(path, value)
                        
                        if not group in keys:
                            keys[group] = []
                        
                        keys[group].append(key)