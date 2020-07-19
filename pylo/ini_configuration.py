import os
import typing
import configparser

from .abstract_configuration import AbstractConfiguration

class IniConfiguration(AbstractConfiguration):
    def __init__(self, file_path=None) -> None:
        """Create a new abstract configuration."""
        
        if isinstance(file_path, str):
            if not os.path.isdir(os.path.dirname(file_path)):
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                except OSError:
                    file_path = None
            
        if not isinstance(file_path, str):
            from .config import DEFAULT_INI_PATH
            file_path = DEFAULT_INI_PATH

            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            except OSError:
                raise
        
        if os.path.exists(os.path.dirname(file_path)):
            self.file_path = file_path
        else:
            raise FileNotFoundError(("The parent directory '{}' of the ini " +
                                     "file was not found and could not be " + 
                                     "created.").format(os.path.dirname(file_path)))

        super().__init__()
    
    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        config = configparser.ConfigParser()
        config.read(self.file_path)

        for section in config.sections():
            for key in config[section]:
                self.setValue(section, key, config[section][key])
    
    def saveConfiguration(self) -> None:
        """Save the configuration to be persistant."""

        config = configparser.ConfigParser()
        
        for group in self.getGroups():
            for key in self.getKeys(group):
                if self.valueExists(group, key):
                    if not group in config:
                        config[group] = {}
                    
                    val = self.getValue(group, key, False)
                    if isinstance(val, bool) and val == True:
                        val = "yes"
                    elif isinstance(val, bool) and val == False:
                        val = "no"
                    
                    config[group][key] = str(val)
        
        with open(self.file_path, 'w+') as configfile:
            config.write(configfile)


