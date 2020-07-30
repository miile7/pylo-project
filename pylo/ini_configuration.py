import os
import typing
import textwrap
import configparser

from .pylolib import path_like
from .pylolib import get_datatype_name
from .abstract_view import AbstractView
from .abstract_configuration import AbstractConfiguration

class IniConfiguration(AbstractConfiguration):
    def __init__(self, file_path: typing.Optional[typing.Union[path_like]] = None) -> None:
        """Create a new abstract configuration.

        Raises
        ------
        FileNotFoundError
            When the file could not be created
        
        Parameters
        ----------
        file_path : str, pathlib.PurePath, os.PathLike
            The file path (including the extension) to use, if not given the 
            `DEFAULT_INI_PATH` form the `config` will be used, parent 
            directories are created if they do not exist (and if possible),
            default: None
        """
        
        if isinstance(file_path, path_like):
            if not os.path.isdir(os.path.dirname(file_path)):
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                except OSError:
                    file_path = None
            
        if not isinstance(file_path, path_like):
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

        config = configparser.ConfigParser(allow_no_value=True)
        
        for group in self.getGroups():
            for key in self.getKeys(group):
                if self.valueExists(group, key):
                    if not group in config:
                        config[group] = {}
                    # prepare the comment
                    comment = []
                    try:
                        comment.append(str(self.getDescription(group, key)))
                    except KeyError:
                        pass
                    
                    try:
                        comment.append("Type: '{}'".format(
                            get_datatype_name(self.getDatatype(group, key))
                        ))
                    except KeyError:
                        pass

                    try:
                        comment.append("Default: '{}'".format(self.getDefault(group, key)))
                    except KeyError:
                        pass

                    # save the comment
                    if len(comment) > 0:
                        w = 79
                        c = "; "
                        comment_text = []
                        for l in comment:
                            comment_text += textwrap.wrap(l, w)
                        comment = ("\n" + c).join(comment_text)
                        config[group][c + comment] = None
                    
                    # prepare the value
                    val = self.getValue(group, key, False)
                    if isinstance(val, bool) and val == True:
                        val = "yes"
                    elif isinstance(val, bool) and val == False:
                        val = "no"
                    
                    # save the value, adding new line for better looks
                    config[group][key] = str(val) + "\n"
        
        with open(self.file_path, 'w+') as configfile:
            config.write(configfile)