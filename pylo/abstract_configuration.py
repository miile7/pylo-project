import copy
import typing

from .datatype import Datatype

Savable = typing.Union[str, int, float, bool, None]

class AbstractConfiguration:
    """This class is the base class for configurations.

    The implementing class only sets the way how the data is saved persistantly.
    For this overwrite the `AbstractConfiguration::loadConfiguration()` and the 
    `AbstractConfiguration::saveConfiguration()`. The load function should use 
    the `AbstractConfiguration::setValue()` function to set the values. Note
    that only the value is required. Other properties (datatype, default, ...)
    are defined by the program itself.

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
        self.marked_states = {}
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
        datatype : type or Datatype, optional
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

        if len(self.marked_states) > 0:
            for state_id in self.marked_states:
                self.marked_states[state_id]["set"][(group, key)] = self.getValue(group, key)

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
        datatype : type or Datatype, optional
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
        
            if len(self.marked_states) > 0:
                for state_id in self.marked_states:
                    if (group, key) in self.marked_states[state_id]["del"]:
                        # remove deleting if the key was deleted and then added
                        # in this state
                        del self.marked_states[state_id]["del"][(group, key)]
                    else:
                        self.marked_states[state_id]["add"].append((group, key))

        
        if not "value" in self.configuration[group][key]:
            self.configuration[group][key]["value"] = []

        supported_args = {
            "datatype": (type, Datatype),
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
        
        if datatype == bool:
            if isinstance(value, str):
                value = value.lower()
            
            if value in ("yes", "y", "true", "t", "on"):
                value = True
            elif value in ("no", "n", "false", "f", "off"):
                value = False
            else:
                try:
                    value = int(value)

                    if value == 0:
                        value = False
                    elif value == 1:
                        value = True
                except ValueError:
                    pass
        
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
    
    def getDatatype(self, group: str, key: str) -> typing.Union[type, Datatype]:
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
            if len(self.marked_states) > 0:
                for state_id in self.marked_states:
                    if (group, key) not in self.marked_states[state_id]["add"]:
                        # do not save if the value was added and then deleted
                        # in this state mark
                        self.marked_states[state_id]["del"][(group, key)] = copy.deepcopy(self.configuration[group][key])

            del self.configuration[group][key]

            if len(self.configuration[group]):
                # group is empty, delete it too
                del self.configuration[group]
    
    def markState(self) -> int:
        """Mark the current state of the configuration.

        This will allow to observe all changes that are made after this state.
        The returned number is the state id to find the saved state.

        Note that only the final change can be generated. So this is not a 
        history of all changes but only a comparism between this marked state
        and the state when the other state functions are called.

        Make sure to drop marks after they are not needed anymore. They will 
        add a lot of values to the internal memory.

        See Also
        --------
        AbstractConfiguration.dropStateMark()

        Returns
        -------
        int
            The state id to identify the marked position
        """
        for i in range(len(self.marked_states) + 1):
            if not i in self.marked_states:
                state_id = i
                break
        
        self.marked_states[state_id] = {
            "add": [],
            "del": {},
            "set": {}
        }
        return state_id
    
    def getChanges(self, state_id: int) -> typing.List[typing.Tuple[str, str]]:
        """Get the keys and groups that changed their value sice the `state_id`.

        This will return a list of tuples where each tuple defines the element 
        that changed. The tuple contains the group at index 0 and the key at 
        index 1.

        This will only contain the keys and when the values changed. If an 
        element is added, this will not be shown here.

        Raises
        ------
        KeyError
            When the `state_id` does not exist
        
        Parameters
        ----------
        state_id : int
            The state id that is returned by `AbstractConfiguration.markState()`
        
        Returns
        -------
        list of tuples
            The changed elements where the list contains tuples with the group 
            at index 0 and the key at index 1
        """
        if not state_id in self.marked_states:
            raise KeyError("The state '{}' does not exist.".format(state_id))

        return list(self.marked_states[state_id]["set"].keys())
    
    def getAdditions(self, state_id: int) -> typing.List[typing.Tuple[str, str]]:
        """Get the keys and groups were added sice the `state_id`.

        This will return a list of tuples where each tuple defines the element 
        that was added. The tuple contains the group at index 0 and the key at 
        index 1.

        Raises
        ------
        KeyError
            When the `state_id` does not exist
        
        Parameters
        ----------
        state_id : int
            The state id that is returned by `AbstractConfiguration.markState()`
        
        Returns
        -------
        list of tuples
            The added elements where the list contains tuples with the group at
            index 0 and the key at index 1
        """
        if not state_id in self.marked_states:
            raise KeyError("The state '{}' does not exist.".format(state_id))

        return copy.deepcopy(self.marked_states[state_id]["add"])
    
    def getDeletions(self, state_id: int) -> typing.List[typing.Tuple[str, str]]:
        """Get the keys and groups were deleted sice the `state_id`.

        This will return a list of tuples where each tuple defines the element 
        that was deleted. The tuple contains the group at index 0 and the key 
        at index 1.

        Raises
        ------
        KeyError
            When the `state_id` does not exist
        
        Parameters
        ----------
        state_id : int
            The state id that is returned by `AbstractConfiguration.markState()`
        
        Returns
        -------
        list of tuples
            The deleted elements where the list contains tuples with the group at
            index 0 and the key at index 1
        """
        if not state_id in self.marked_states:
            raise KeyError("The state '{}' does not exist.".format(state_id))

        return list(self.marked_states[state_id]["add"].keys())
    
    def resetChanges(self, state_id: int) -> None:
        """Reset all the changes since the `state_id`.

        This will add all the deleted elements, remove all the added elements
        and rewind all the changed elements.

        Make sure to drop marks after they are not needed anymore. They will 
        add a lot of values to the internal memory.

        Raises
        ------
        KeyError
            When the `state_id` does not exist
        
        Parameters
        ----------
        state_id : int
            The state id that is returned by `AbstractConfiguration.markState()`
        """
        if not state_id in self.marked_states:
            raise KeyError("The state '{}' does not exist.".format(state_id))

        for group, key in self.marked_states[state_id]["add"]:
            self.removeElement(group, key)
        
        for group, key, value in self.marked_states[state_id]["set"].items():
            self.setValue(group, key, value)
        
        for group, key, config in self.marked_states[state_id]["del"].items():
            if not group in self.configuration:
                self.configuration[group] = {}
            
            self.configuration[group][key] = config
    
    def dropStateMark(self, state_id: int) -> None:
        """Delete all saved changes for the `state_id`.

        The `state_id` can no longer be used. Note that state ids will be
        re-used, so once a mark is deleted using the `state_id` creates
        unexcepcted behaviour.

        Raises
        ------
        KeyError
            When the `state_id` does not exist
        
        Parameters
        ----------
        state_id : int
            The state id that is returned by `AbstractConfiguration.markState()`
        """
        if not state_id in self.marked_states:
            raise KeyError("The state '{}' does not exist.".format(state_id))

        del self.marked_states[state_id]
    
    def getGroups(self) -> typing.Tuple[str]:
        """Get all groups that exist.

        Returns
        -------
        tuple of str
            All group names as strings
        """
        return tuple(self.configuration.keys())
    
    def getKeys(self, group: str) -> typing.Tuple[str]:
        """Get all keys for a group that exist.

        Raises
        ------
        KeyError
            When the `group` does not exist.

        Returns
        -------
        tuple of str
            All key names as strings
        """
        if not group in self.configuration:
            raise KeyError("The group '{}' does not exist.".format(group))
        
        return tuple(self.configuration[group].keys())
    
    def groupsAndKeys(self) -> typing.Generator[typing.Tuple[str, str], None, None]:
        """Get all group-key-pairs to iterate over.

        Returns
        -------
        generator of tuples
            A list of tuples where each tuple contains the group at index 0 and 
            the key at index 1
        """

        for group in self.getGroups():
            for key in self.getKeys(group):
                yield (group, key)
    
    def items(self) -> typing.Generator[typing.Tuple[str, str, Savable, type, Savable, bool, str, bool], None, None]:
        """Get the items to iterate over.

        The returned tuple contains the following values in the following order:
        - str, group
        - str, key
        - Savable, value (the current value only, if not set None is returned)
        - type, datatype (if not set None is returned)
        - Savable, default_value (if not set None is returned, Note that the 
          default can be `None` as a value, for this use 
          `AbstractConfiguration::defaultExists()`)
        - bool, ask_if_not_present (if not set None is returned)
        - str, description (if not set None is returned)
        - bool, restart_required (if not set None is returned)
        """
        for group in self.configuration:
            for key in self.configuration[group]:
                row = [group, key]

                try:
                    row.append(self.getValue(group, key))
                except KeyError:
                    row.append(None)

                try:
                    row.append(self.getDatatype(group, key))
                except KeyError:
                    row.append(None)

                try:
                    row.append(self.getDefault(group, key))
                except KeyError:
                    row.append(None)

                try:
                    row.append(self.getAskIfNotPresent(group, key))
                except KeyError:
                    row.append(None)

                try:
                    row.append(self.getDescription(group, key))
                except KeyError:
                    row.append(None)

                try:
                    row.append(self.getRestartRequired(group, key))
                except KeyError:
                    row.append(None)

                yield tuple(row)
    
    def __len__(self) -> int:
        """Get the length of the configuration.

        Note that all elements are counted, also if they do not have a value.

        Returns
        -------
        int
            The number of all configuration definitions
        """
        l = 0
        for group in self.configuration:
            l += len(self.configuration[group])
        return l
    
    def __getitem__(self, key: typing.Union[typing.Tuple[str, str], typing.Tuple[str, str]]) -> Savable:
        """Get the item.

        The `key` can either be `("group", "key")` or one of the following:
        - `("group", "key", "value")`
        - `("group", "key", "datatype")`
        - `("group", "key", "default_value")`
        - `("group", "key", "ask_if_not_present")`
        - `("group", "key", "description")`
        - `("group", "key", "restart_required")`

        Raises
        ------
        TypeError
            When the `key` is not a tuple of length 2 or length 3.

        Parameters
        ----------
        key : tuple
            The Key
        
        Returns
        -------
        Savable
            The value
        """
        if not isinstance(key, tuple) or (len(key) != 2 and len(key) != 3):
            raise TypeError("Only tuples of the form 'group, key' or " + 
                            "'group, key, type' are supported.")
        
        if len(key) == 2 or (len(key) == 3 and key[2] == "value"):
            return self.getValue(key[0], key[1], False)
        elif len(key) == 3:
            if key[2] == "datatype":
                return self.getDatatype(key[0], key[1])
            elif key[2] == "default_value":
                return self.getDefault(key[0], key[1])
            elif key[2] == "ask_if_not_present":
                return self.getAskIfNotPresent(key[0], key[1])
            elif key[2] == "description":
                return self.getDescription(key[0], key[1])
            elif key[2] == "restart_required":
                return self.getRestartRequired(key[0], key[1])
            else:
                raise KeyError("The key '{}' does not exist.".format(key[2]))
    
    def __setitem__(self, key: typing.Union[typing.Tuple[str, str], typing.Tuple[str, str]], value: typing.Any) -> Savable:
        """Set the item.

        The `key` can either be `("group", "key")` or one of the following:
        - `("group", "key", "value")`
        - `("group", "key", "datatype")`
        - `("group", "key", "default_value")`
        - `("group", "key", "ask_if_not_present")`
        - `("group", "key", "description")`
        - `("group", "key", "restart_required")`

        Raises
        ------
        TypeError
            When the `key` is not a tuple of length 2 or length 3.

        Parameters
        ----------
        key : tuple
            The Key
        
        Returns
        -------
        Savable
            The value
        """
        if not isinstance(key, tuple) or (len(key) != 2 and len(key) != 3):
            raise TypeError("Only tuples of the form 'group, key' or " + 
                            "'group, key, type' are supported.")
        
        if len(key) == 2 or (len(key) == 3 and key[2] == "value"):
            return self.setValue(key[0], key[1], value)
        elif len(key) == 3:
            args = {key[2]: value}
            self.addConfigurationOption(key[0], key[1], **args)
    
    def __delitem__(self, key: typing.Tuple[str, str]) -> Savable:
        """Set the item.

        The `key` must be `("group", "key")`.

        Raises
        ------
        TypeError
            When the `key` is not a tuple of length 2.

        Parameters
        ----------
        key : tuple
            The Key
        """
        if not isinstance(key, tuple) or len(key) != 2:
            raise TypeError("Only tuples of the form 'group, key' are supported.")
        
        self.removeElement(key[0], key[1])
    
    def __iter__(self) -> typing.Iterator[typing.Tuple[str, str]]:
        """Iterate over the groups and keys."""
        for group in self.configuration:
            for key in self.configuration[group]:
                yield group, key
    
    def __contains__(self, key: typing.Tuple[str, str]) -> bool:
        """Whether the configuration contains the group and key defined at 
        index 0 and 1 in the `key`.
        """
        if not isinstance(key, tuple) or len(key) != 2:
            raise TypeError("Only tuples of the form 'group, key' are supported.")
        
        return self._keyExists(key[0], key[1])
    
    def asDict(self) -> dict:
        """Get the configuration values as a dict.

        Returns
        -------
        dict
            A 2d-dict representing the current configuration values, the outer 
            keys are the group names, the inner keys are the keys
        """

        config_dict = {}
        for group in self.getGroups():
            if not group in config_dict:
                config_dict[group] = {}
            
            for key in self.getKeys(group):
                config_dict[group][key] = self.getValue(group, key)
        
        return config_dict
    
    def loadFromMapping(self, config: typing.Mapping) -> None:
        """Load the given `config` dict.

        The `config` has to be a mapping where each key is the group name and 
        each value is another mapping containing the key name as the key and 
        the value as the value to set.

        Parameters
        ----------
        config : mapping
            A 2d-mapping containing the groups, keys and values to set
        """

        for group in config:
            for key in config[group]:
                self.setValue(group, key, config[group][key])
        
    def saveConfiguration(self) -> None:
        """Save the configuration to be persistant."""

        # This should be implemented by child classes, otherwise there is no 
        # persistant storage
        pass
    
    def loadConfiguration(self) -> None:
        """Load the configuration from the persistant data."""

        # This should be implemented by child classes, otherwise there is no 
        # persistant storage
        pass