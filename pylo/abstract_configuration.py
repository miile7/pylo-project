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
                "datatype": str
                "default_value": "default",
                "ask_if_not_present": True
                "description": "The description of the value to set",
                "restart_required": True
            }
        }
    }
    ```

    Attributes
    ----------
    configuration : dict with dicts with dicts
        The configuration as a dict, outer dict contains the groups, the inner 
        dict contains the key, the value is another dict with the "value", the
        "datatype", the "default_value", the "ask_if_not_present" and the 
        "description" indices
    """

    def __init__(self) -> None:
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
                "default_value" in self.configuration[group][key])
    
    def setValue(self, group: str, key: str, value: Savable,
                 **kwargs: typing.Union[type, Savable, bool, str]) -> None:
        """Set the value to the group and key.

        Raises
        ------
        KeyError
            When the kwarg key is not defined
        TypeError
            When the kwarg value is of the wrong type

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        value : str, int, float, bool or None
            The value

        Keyword Args
        ------------
        datatype : type, optional
            Any valid type, this is used for defining this value so it can be 
            asked and saved by the view, if given this will overwite the 
            datatype if it exists already, if it does not exist and is not 
            given the type of the value will be used, default: *not-set*
        default_value : str, int, float, bool or None, optional
            The default value to use if the value is not given, 
            default: *not-set*
        ask_if_not_present : bool, optional
            Whether to ask the user for the value if it is not saved, if given 
            this will overwite the ask_if_not_present if it exists already, if 
            it does not exist and is not given False will be used, default: 
            *not-set*
        description : str, optional
            The description to save in the ini file or to show to the user as 
            explenation what he is putting int, if given this will overwite the 
            description if it exists already, default: ""
        restart_required : bool, optional
            Whether a restart is required that the changes will apply, default: 
            *not-set*
        """
        
        self.addConfigurationOption(group, key, **kwargs)

        self.configuration[group][key]["value"] = [value]
    
    def addConfigurationOption(self, group: str, key: str, 
                               **kwargs: typing.Union[type, Savable, bool, str]) -> None:
        """Define the property for the given group and key.

        This is for the configuration and the view to know what to expect and 
        what to ask for.

        Raises
        ------
        KeyError
            When the kwarg key is not defined
        TypeError
            When the kwarg value is of the wrong type

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value

        Keyword Args
        ------------
        datatype : type, optional
            Any valid type, this is used for defining this value so it can be 
            asked and saved by the view, if given this will overwite the 
            datatype if it exists already, if it does not exist and is not 
            given the type of the value will be used, default: *not-set*
        default_value : str, int, float, bool or None, optional
            The default value to use if the value is not given, 
            default: *not-set*
        ask_if_not_present : bool, optional
            Whether to ask the user for the value if it is not saved, if given 
            this will overwite the ask_if_not_present if it exists already, if 
            it does not exist and is not given False will be used, default: 
            False
        description : str, optional
            The description to save in the ini file or to show to the user as 
            explenation what he is putting int, if given this will overwite the 
            description if it exists already, default: ""
        restart_required : bool, optional
            Whether a restart is required that the changes will apply, default: 
            False
        """

        if not group in self.configuration:
            self.configuration[group] = {}
        if not key in self.configuration[group]:
            self.configuration[group][key] = {}
        
        if not "value" in self.configuration[group][key]:
            self.configuration[group][key]["value"] = []

        supported_args = {
            "datatype": type,
            "default_value": typing.Any,
            "ask_if_not_present": bool,
            "description": str,
            "restart_required": bool
        }
        
        default_kwargs = {
            "ask_if_not_present": False,
            "restart_required": False
        }
        
        for k, v in default_kwargs.items():
            if k not in kwargs:
                kwargs[k] = v

        for k, v in kwargs.items():
            if k not in supported_args:
                raise KeyError(("The key '{}' is not supported as a keyword " + 
                                "argument").format(k))
            elif (supported_args[k] != typing.Any and 
                  not isinstance(v, supported_args[k])):
                    raise TypeError(("The key '{}' in the kwargs has to be of " + 
                                     "type {} but it is {}.").format(
                                         k, supported_args[k], type(v)))
            else:
                self.configuration[group][key][k] = kwargs[k]
    
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
            return self.configuration[group][key]["default_value"]
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
        elif ("datatype" not in self.configuration[group][key] or
              self.configuration[group][key]["datatype"] == None):
            raise KeyError(
                "There is no type for the key {} with the group {}.".format(key, group)
            )
        else:
            return self.configuration[group][key]["datatype"]
    
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
        
        if callable(datatype):
            return datatype(value)
        else:
            return value
    
    def _getIndexValue(self, group: str, key: str, index: str) -> typing.Any:
        """Get the value at the index.

        This is for internal use only.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no index in it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        index : str
            The index to get the value of

        Returns
        -------
        any
            The value at the index in the group and key
        """

        if not self._keyExists(group, key):
            raise KeyError(
                ("The key {} does not exist in the group {}.").format(key, 
                                                                      group)
            )
        elif index not in self.configuration[group][key]:
            raise KeyError(
                ("There is no index '{}' for the key {} in the " + 
                 "group {}.").format(index, key, group)
            )
        else:
            return self.configuration[group][key][index]
    
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
        try:
            return self._getIndexValue(group, key, "default_value")
        except KeyError:
            raise
    
    def getDatatype(self, group: str, key: str) -> type:
        """Get the datatype for the group and key.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no datatype for it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value

        Returns
        -------
        type
            The datatype
        """
        try:
            return self._getIndexValue(group, key, "datatype")
        except KeyError:
            raise
    
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
        try:
            return self._getIndexValue(group, key, "ask_if_not_present")
        except KeyError:
            raise
    
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
        try:
            return self._getIndexValue(group, key, "description")
        except KeyError:
            raise
    
    def getRestartRequired(self, group: str, key: str) -> bool:
        """Get whether a restart is required that the changes apply or not.

        Raises
        ------
        KeyError
            When the group and key are not found or there is no 
            restart_required for it.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value

        Returns
        -------
        bool
            Whether a restart is required that the changes apply
        """
        try:
            return self._getIndexValue(group, key, "restart_required")
        except KeyError:
            raise
    
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
    
    def removeValue(self, group: str, key: str) -> None:
        """Remove the value only for the given group and key.

        This will make the group and key stay initialized but without a value.
        This is equal to the state when calling 
        `AbstractConfiguration::addConfigurationOption()`

        If the group and key do not exist, nothing will happen.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        """

        if self._keyExists(group, key):
            self.configuration[group][key]["value"] = []
    
    def removeElement(self, group: str, key: str) -> None:
        """Remove the everything for the given group and key.

        This will remove the key completely including the value, the datatype
        and all the other settings. If the group is empty, it will be removed
        too.

        If the group and key do not exist, nothing will happen.

        Parameters
        ----------
        group : str
            The name of the group
        key : str
            The key name for the value
        """

        if self._keyExists(group, key):
            del self.configuration[group][key]

            if len(self.configuration[group]):
                # group is empty, delete it too
                del self.configuration[group]
    
    def saveConfiguration(self) -> None:
        """Save the configuration to be persistant."""

        raise NotImplementedError()
    
    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        raise NotImplementedError()