import os
import typing
import logging
import textwrap
import configparser

from .logginglib import do_log
from .logginglib import log_error
from .pylolib import path_like
from .logginglib import get_logger
from .pylolib import human_concat_list
from .pylolib import get_datatype_human_text
from .datatype import Datatype
from .datatype import OptionDatatype
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
        
        # logger has to be present for the file opening but super() will 
        # overwrite self._logger, super() cannot be called here because it
        # loads the config which is not possible without the file
        logger = get_logger(self)

        if isinstance(file_path, path_like):
            if not os.path.isdir(os.path.dirname(file_path)):
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                except OSError:
                    file_path = None
            
        if not isinstance(file_path, path_like):
            from .config import DEFAULT_INI_PATH
            file_path = DEFAULT_INI_PATH

            if do_log(logger, logging.DEBUG):
                logger.debug("Using file path '{}' from config".format(file_path))

            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            except OSError as e:
                log_error(logger, e)
                raise e
        
        if os.path.exists(os.path.dirname(file_path)):
            self.file_path = file_path
        else:
            err = FileNotFoundError(("The parent directory '{}' of the ini " +
                                     "file was not found and could not be " + 
                                     "created.").format(os.path.dirname(file_path)))
            log_error(logger, err)
            raise err

        super().__init__()
        self._logger = logger
    
    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Loading configuration from ini file '{}'".format(
                               self.file_path))
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.file_path)

        for section in config.sections():
            for key in config[section]:
                value = config[section][key]

                try:
                    datatype = self.getDatatype(section, key)
                except KeyError:
                    datatype = None
                
                if datatype == bool:
                    if isinstance(value, str):
                        value = value.lower()
                    
                    if value in ["no", "n", "false", "f", "off", "0"]:
                        value = False
                    elif value in ["yes", "y", "true", "t", "on", "1"]:
                        value = True
                    else:
                        value = bool(value)
                elif callable(datatype):
                    value = datatype(value)

                self.setValue(section, key, value)
    
    def saveConfiguration(self) -> None:
        """Save the configuration to be persistant."""

        config = configparser.ConfigParser(allow_no_value=True, 
                                           interpolation=None)
        
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
                        datatype = self.getDatatype(group, key)
                        comment.append("Type: '{}'".format(
                            get_datatype_human_text(datatype)
                        ))

                        if isinstance(datatype, OptionDatatype):
                            comment.append("Allowed values: {}".format(
                                human_concat_list(datatype.options)
                            ))
                    except KeyError:
                        datatype = str

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
                    elif isinstance(datatype, Datatype):
                        val = datatype.format(val)
                    
                    # save the value, adding new line for better looks
                    config[group][key] = str(val) + "\n"
        
        if do_log(self._logger, logging.DEBUG):
            self._logger.debug("Saving ini configuration to file '{}'".format(
                               self.file_path))
        with open(self.file_path, 'w+') as configfile:
            config.write(configfile)