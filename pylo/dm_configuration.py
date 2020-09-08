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

from .abstract_configuration import AbstractConfiguration

class DMConfiguration(AbstractConfiguration):
    delimiter = ";"

    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        from .config import DM_CONFIGURATION_PERSISTENT_TAG_NAME
        
        if DM is not None:
            s, groups = DM.GetPersistentTagGroup().GetTagAsString(
                "{}:{{{{groups}}}}".format(
                    DM_CONFIGURATION_PERSISTENT_TAG_NAME
                )
            )

            if s:
                groups = groups.split(DMConfiguration.delimiter)

                for group in groups:
                    s, keys = DM.GetPersistentTagGroup().GetTagAsString(
                        "{}:{}:{{{{keys}}}}".format(
                            DM_CONFIGURATION_PERSISTENT_TAG_NAME, group
                        )
                    )

                    if s:
                        keys = keys.split(DMConfiguration.delimiter)

                        for key in keys:
                            s, value = DM.GetPersistentTagGroup().GetTagAsString(
                                "{}:{}:{}".format(
                                    DM_CONFIGURATION_PERSISTENT_TAG_NAME, 
                                    group, key
                                )
                            )

                            if s:
                                self.setValue(group, key, value)
    
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
        
        for group in keys:
            DM.GetPersistentTagGroup().SetTagAsString("{}:{}:{{{{keys}}}}".format(
                DM_CONFIGURATION_PERSISTENT_TAG_NAME, group
            ), DMConfiguration.delimiter.join(keys[group]))
        
        DM.GetPersistentTagGroup().SetTagAsString("{}:{{{{groups}}}}".format(
            DM_CONFIGURATION_PERSISTENT_TAG_NAME
        ), DMConfiguration.delimiter.join(list(keys.keys())))