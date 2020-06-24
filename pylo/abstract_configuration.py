import typing

Savable = typing.Union[str, int, float, bool, None]

class AbstractConfiguration:
    """This class is the base class for configurations.

    The implementing class only sets the way how the data is saved persistantly.

    The internal configuration may look like this:
    ```
    {
        "group": {
            "key": {
                "value": ["init val", "1st overwrite val", "2nd overwrite val"],
                "type": str
                "default": "default",
                "ask_if_not_present": True
                "description": "The description of the value to set"
            }
        }
    }
    ```

    Attributes
    ----------
    configuration : dict with dicts with dicts
        The configuration as a dict, outer dict contains the groups, the inner 
        dict contains the key, the value is another dict with the "value", the
        "type", the "default", the "ask_if_not_present" and the "description" 
        indices
    """

    def __init__(self):
        """Create a new abstract configuration.
        
        This calls the loadConfiguration() function automatically."""
        self.configuration = {}
        self.loadConfiguration()
    
    def _keyExists(self, group: str, key: str) -> bool:
        """Get whether there is the key and the group.

        This does not check if there is a value!

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        
        Returns
        -------
        bool
            Whether the key exists within the group or not
        """

        return (group in self.configuration and 
                isinstance(self.configuration[group], dict) and
                key in self.configuration[group])
    
    def valueExists(self, group: str, key: str) -> bool:
        """Get whether there is a value for the group and the key.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        
        Returns
        -------
        bool
            Whether the value exists or not
        """
        return (self._keyExists(group, key) and 
                "value" in self.configuration[group][key] and 
                isinstance(self.configuration[group][key]["value"], list) and
                len(self.configuration[group][key]["value"]) > 0)
    
    def defaultExists(self, group: str, key: str) -> bool:
        """Get whether there is a *default* value for the group and the key. 

        This will not check if the value exists!

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        
        Returns
        -------
        bool
            Whether the default value exists or not
        """
        return (self._keyExists(group, key) and 
                "default" in self.configuration[group][key])
    
    def setValue(self, group: str, key: str, value: Savable, 
                 datatype: typing.Optional[type]=None, 
                 default_value: typing.Optional[Savable]=None, 
                 ask_if_not_present: typing.Optional[bool]=None, 
                 description: typing.Optional[str]=None) -> None:
        """Set the value to the group and key.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        value : str, int, float, bool or None
            The value
        datatype : type
            Any valid type, this is used for defining this value so it can be 
            asked and saved by the view, if given this will overwite the 
            datatype if it exists already, if it does not exist and is not 
            given the type of the value will be used
        default_value : str, int, float, bool or None
            The default value to use if the value is not given
        ask_if_not_present : bool
            Whether to ask the user for the value if it is not saved, if given 
            this will overwite the ask_if_not_present if it exists already, if 
            it does not exist and is not given False will be used
        description : str
            The description to save in the ini file or to show to the user as 
            explenation what he is putting int, if given this will overwite the 
            description if it exists already
        """

        if datatype is None and value is not None:
            datatype = type(value)

        self.addConfigurationOption(group, key, datatype, default_value, 
                                    ask_if_not_present, description)

        self.configuration[group][key]["value"] = [value]
    
    def addConfigurationOption(self, group: str, key: str, 
                 datatype: typing.Optional[type]=None, 
                 default_value: typing.Optional[Savable]=None, 
                 ask_if_not_present: typing.Optional[bool]=None, 
                 description: typing.Optional[str]=None) -> None:
        """Define the property for the given group and key.

        This is for the configuration and the view to know what to expect and 
        what to ask for.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        datatype : type
            Any valid type, this is used for defining this value so it can be 
            asked and saved by the view, if given this will overwite the 
            datatype if it exists already
        default_value : str, int, float, bool or None
            The default value to use if the value is not given
        ask_if_not_present : bool
            Whether to ask the user for the value if it is not saved, if given 
            this will overwite the ask_if_not_present if it exists already, if 
            it does not exist and is not given False will be used
        description : str
            The description to save in the ini file or to show to the user as 
            explenation what he is putting int, if given this will overwite the 
            description if it exists already
        """

        if not group in self.configuration:
            self.configuration[group] = {}
        if not key in self.configuration[group]:
            self.configuration[group][key] = {}
        
        if not "value" in self.configuration[group][key]:
            self.configuration[group][key]["value"] = []

        if (datatype is not None or 
            "type" not in self.configuration[group][key]):
            self.configuration[group][key]["type"] = datatype

        if (default_value is not None or 
            "default" not in self.configuration[group][key]):
            self.configuration[group][key]["default"] = default_value

        if ask_if_not_present is not None: 
            self.configuration[group][key]["ask_if_not_present"] = ask_if_not_present
        elif "ask_if_not_present" not in self.configuration[group][key]:
            self.configuration[group][key]["ask_if_not_present"] = False

        if (description is not None or 
            "description" not in self.configuration[group][key]):
            self.configuration[group][key]["description"] = description
    
    def getValue(self, group: str, key: str, 
                 fallback_default: typing.Optional[bool]=True) -> Savable:
        """Get the value for the given group and key.

        Raises
        ------
        KeyError
            When the group and key are not found and either there is no default
            or the fallback_default is False

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        fallback_default : bool
            Whether to use the default value if there is a default value but 
            no value
        
        Returns
        -------
        any
            The value
        """

        if self.valueExists(group, key):
            return self._parseValue(group, key, self.configuration[group][key]["value"][-1])
        elif fallback_default and self.defaultExists(group, key):
            return self.configuration[group][key]["default"]
        else:
            raise KeyError(
                ("The value for the key {} within the group {} has not been " + 
                "found.").format(key, group)
            )
    
    def _getType(self, group: str, key: str) -> type:
        """Get the type for the group and the key.

        Raises
        ------
        KeyError
            When the group and key are not found or when there is no type for 
            it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name

        Returns
        -------
        type
            The datatype
        """

        if not self._keyExists(group, key):
            raise KeyError(
                ("The key {} does not exist in the group {}, therefore it " + 
                 "cannot be overwritten.").format(key, group)
            )
        elif ("type" not in self.configuration[group][key] or
              self.configuration[group][key]["type"] == None):
            raise KeyError(
                "There is no type for the key {} with the group {}.".format(key, group)
            )
        else:
            return self.configuration[group][key]["type"]
    
    def _parseValue(self, group: str, key: str, value: Savable) -> Savable:
        """Parse the value to the datatype defined by the group and key, if 
        there is no datatype the original value will be returned.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name
        value : str, int, float, bool or None
            The value to parse

        Returns
        -------
        Savable
            The parsed value or the value if there is no datatype defined at
            the group and key
        """

        try:
            datatype = self._getType(group, key)
        except KeyError:
            datatype = None
        
        if datatype == int:
            return int(value)
        elif datatype == float:
            return float(value)
        elif datatype == str:
            return str(value)
        elif datatype == bool:
            return bool(value)
        else:
            return value
    
    def getDefault(self, group: str, key: str) -> Savable:
        """Get the default value for the group and key.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no default for it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value

        Returns
        -------
        str, int, float bool or None
            The default value
        """

        if not self._keyExists(group, key):
            raise KeyError(
                ("The key {} does not exist in the group {}.").format(key, group)
            )
        elif "default" not in self.configuration[group][key]:
            raise KeyError(
                ("There is no default for the key {} in the group {}.").format(key, group)
            )
        else:
            return self.configuration[group][key]["default"]
    
    def getAskIfNotPresent(self, group: str, key: str) -> bool:
        """Get whether to ask if the value for the given group and key is not 
        present.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no 
            `ask_if_not_present` value for it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value

        Returns
        -------
        bool
            Whether to ask if the value is not present
        """

        if not self._keyExists(group, key):
            raise KeyError(
                ("The key {} does not exist in the group {}.").format(key, group)
            )
        elif "ask_if_not_present" not in self.configuration[group][key]:
            raise KeyError(
                ("There is no ask_if_not_present for the key {} in the group {}.").format(key, group)
            )
        else:
            return self.configuration[group][key]["ask_if_not_present"]
    
    def getDescription(self, group: str, key: str) -> str:
        """Get the description for the group and key.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no description for it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value

        Returns
        -------
        str
            The description
        """

        if not self._keyExists(group, key):
            raise KeyError(
                ("The key {} does not exist in the group {}.").format(key, group)
            )
        elif "description" not in self.configuration[group][key]:
            raise KeyError(
                ("There is no description for the key {} in the group {}.").format(key, group)
            )
        else:
            return self.configuration[group][key]["description"]
    
    def temporaryOverwriteValue(self, group: str, key: str, value: Savable) -> None:
        """Temporary overwrite the given value of the group and key.

        This is not saved presistantly. Also this is lost when the setValue() 
        function is executed. This can be undone again by calling the 
        resetValue() function.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no value for it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        value : str, int, float, bool or None
            The value
        """

        if not self._keyExists(group, key):
            raise KeyError(
                ("The key {} does not exist in the group {}, therefore it " + 
                 "cannot be overwritten.").format(key, group)
            )
        elif not self.valueExists(group, key):
            raise KeyError(
                ("There is no value for the key {} with the group {}, " + 
                 "therefore cannot be overwritten temporarily. Set an initial " + 
                 "value before overwriting temporarily.").format(key, group)
            )
        
        self.configuration[group][key]["value"].append(value)
    
    def resetValue(self, group: str, key: str, count: typing.Optional[int]=1) -> None:
        """Removes count times the overwriting of the value for the given 
        group and key.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no value for it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        count : int, optional
            How many temporary overwritings to undo, if less than 0 or more 
            than overwrite operations the value will be reset to its inital 
            state, default: 1
        """

        if not self._keyExists(group, key):
            raise KeyError(
                ("The key {} does not exist in the group {}, therefore it " + 
                 "cannot be overwritten.").format(key, group)
            )
        elif not self.valueExists(group, key):
            raise KeyError(
                ("There is no value for the key {} with the group {}, " + 
                 "therefore cannot be overwritten temporarily. Set an initial " + 
                 "value before overwriting temporarily.").format(key, group)
            )

        if count == 0 or len(self.configuration[group][key]) <= 1:
            return

        # do not allow to delete item 0, this is the initial value
        max_length = len(self.configuration[group][key]["value"]) - 1

        if count < 0 or count > max_length:
            count = max_length
        
        # taken from https://stackoverflow.com/a/15715924/5934316
        del self.configuration[group][key]["value"][-count:]
    
    def saveConfiguration(self) -> None:
        """Save the configuration to be persistant."""

        raise NotImplementedError()
    
    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        raise NotImplementedError()