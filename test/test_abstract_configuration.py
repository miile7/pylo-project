if __name__ == "__main__":
    # For direct call only
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest
import pylo

class DummyConfiguration(pylo.AbstractConfiguration):
    def __init__(self, dummy_config):
        self.dummy_config = dummy_config
        super().__init__()
    
    def loadConfiguration(self):
        for group in self.dummy_config:
            for key in self.dummy_config[group]:
                self.setValue(group, key, self.dummy_config[group][key])

complete_test_configuration = [
    # group, key, set-value, arguments, expected, 
    # expected is merged with {"value": <value>} and the arguments
    ("dummy-group", "value1", 1, {}, {}),
    ("dummy-group", "value2", True, {}, {}),
    ("dummy-group", "value3", "Test", {}, {}),
    ("dummy-group", "value4", -83332.34983, {}, {}),
    ("dummy-group-2", "value1", "Test Two", {}, {}),
    ("dummy-group-2", "value2", False, {}, {}),
    ("dummy-group-2", "value3", None, {}, {}),
    ("set-group", "value1", 123, {"datatype": int, "default_value": -1, 
        "ask_if_not_present": False, "description": "Value 1", 
        "restart_required": True}, {}),
    ("set-group", "value2", 98923.9882, {"default_value": "Not Set"}, {}),
    ("set-group", "value3", "Test string", {"ask_if_not_present": True}, {}),
    ("set-group", "value4", 0, {"datatype": bool, "restart_required": True}, 
        {"value": False}),
    ("set-group", "value5", "-1.787898922", {"datatype": float}, 
        {"value": -1.787898922}),
    ("options-group", "value1", None, {"datatype": int, "default_value": 0,
        "ask_if_not_present": False, "description": "Value 1"}, {}),
    ("options-group", "value2", None, {"datatype": float,
        "ask_if_not_present": True, "description": "Value 2"}, {}),
    ("options-group", "value3", None, {"datatype": bool, 
        "default_value": True, "restart_required": True}, {}),
    ("options-group", "value4", None, {"datatype": str, 
        "default_value": "Default"}, {}),
    ("options-group", "value5", None, {}, {}),
]

    # normalize the expected
for i, (group, key, value, args, expected) in enumerate(complete_test_configuration):
    if not "value" in expected:
        expected["value"] = value

    if not "datatype" in expected:
        if "datatype" in args:
            expected["datatype"] = args["datatype"]
        else:
            expected["datatype"] = type(value)

    if not "default_value" in expected:
        if "default_value" in args:
            expected["default_value"] = args["default_value"]

    if not "ask_if_not_present" in expected:
        if "ask_if_not_present" in args:
            expected["ask_if_not_present"] = args["ask_if_not_present"]
        else:
            expected["ask_if_not_present"] = False

    if not "restart_required" in expected:
        if "restart_required" in args:
            expected["restart_required"] = args["restart_required"]
        else:
            expected["restart_required"] = False

    if not "description" in expected:
        if "description" in args:
            expected["description"] = args["description"]

    complete_test_configuration[i] = (group, key, value, args, expected)
    
# prepare decorator arrays
# test configuration without the "otpions-group" (which does not have 
# values), set in setup_method()
test_configuration_without_option_groups = list(
    filter(lambda y: y[0] != "options-group", 
    complete_test_configuration))

if len(test_configuration_without_option_groups) == 0:
    print("Warning: There are no parameters given for " + 
          "test_configuration_without_option_groups")
    assert False

# the group at index 0 and the key at index 1 of all the configs that have
# values, set up in setup_method()
all_groups_and_keys_having_values = [
    (x[0], x[1]) for x in 
    test_configuration_without_option_groups]

if len(all_groups_and_keys_having_values) == 0:
    print("Warning: There are no parameters given for " + 
          "all_groups_and_keys_having_values")
    assert False

# test configuration with only the "otpions-group", set in setup_method()
options_group_test_configuration = list(
    filter(lambda y: y[0] == "options-group", 
    complete_test_configuration))

if len(options_group_test_configuration) == 0:
    print("Warning: There are no parameters given for " + 
          "options_group_test_configuration")
    assert False

# the group at index 0 and the key at index 1 of only the "options-group", 
# # set up in setup_method()
options_groups_and_keys = [
    (x[0], x[1]) for x in 
    options_group_test_configuration]

if len(options_groups_and_keys) == 0:
    print("Warning: There are no parameters given for " + 
          "options_groups_and_keys")
    assert False
        
# test configuration with only the configs that have defaults set, set up
# in setup_method()
complete_test_configuration_with_defaults = list(
    filter(lambda y: "default_value" in y[4], 
    complete_test_configuration))

if len(complete_test_configuration_with_defaults) == 0:
    print("Warning: There are no parameters given for " + 
          "complete_test_configuration_with_defaults")
    assert False
        
# test configuration withonly the configs that have descriptions set, set 
# up in setup_method()
complete_test_configuration_width_description = list(
    filter(lambda y: "description" in y[4], 
    complete_test_configuration))

if len(complete_test_configuration_width_description) == 0:
    print("Warning: There are no parameters given for " + 
          "complete_test_configuration_width_description")
    assert False
        
# group at index 0 and key at index 1 of values that do not exist
non_existing_groups_and_keys = [
    ("dummy-group", "value-does-not-exist"),
    ("group-does-not-exist", "value1")
]

if len(non_existing_groups_and_keys) == 0:
    print("Warning: There are no parameters given for " + 
          "non_existing_groups_and_keys")
    assert False

class TestConfiguration:
    def setup_method(self):
        # prepare config for autoload
        dummy_config = {}
        for group, key, value, args, expected in complete_test_configuration:
            if group.startswith("dummy"):
                if not group in dummy_config:
                    dummy_config[group] = {}
                
                dummy_config[group][key] = value
        self.configuration = DummyConfiguration(dummy_config)

        # load some values manually
        for group, key, value, args, expected in complete_test_configuration:
            if group == "set-group":
                self.configuration.setValue(group, key, value, **args)
        
        # set some configuration options
        for group, key, value, args, expected in complete_test_configuration:
            if group == "options-group":
                self.configuration.addConfigurationOption(group, key, **args)
        
        # set value to overwrite
        self.configuration.setValue("overwrite-group", "value1", "first")
        self.configuration.temporaryOverwriteValue("overwrite-group", "value1", "second")

        self.configuration.setValue("overwrite-group", "value2", 1)
        self.configuration.temporaryOverwriteValue("overwrite-group", "value2", 2)
        self.configuration.temporaryOverwriteValue("overwrite-group", "value2", 3)
        self.configuration.temporaryOverwriteValue("overwrite-group", "value2", 4)
        self.configuration.temporaryOverwriteValue("overwrite-group", "value2", 5)
        self.configuration.temporaryOverwriteValue("overwrite-group", "value2", 6)

    @pytest.mark.parametrize("group,key", all_groups_and_keys_having_values)
    def test_keys_exist(self, group, key):
        """Test whether the groups and keys exist."""
        assert self.configuration._keyExists(group, key)
    
    @pytest.mark.parametrize("group,key", non_existing_groups_and_keys)
    def test_invalid_keys_do_not_exist(self, group, key):
        """Test whether invalid keys do not exist."""
        assert not self.configuration._keyExists(group, key)

    @pytest.mark.parametrize("group,key", all_groups_and_keys_having_values)
    def test_values_exist(self, group, key):
        """Test whether the values exist."""
        assert self.configuration.valueExists(group, key)

    @pytest.mark.parametrize("group,key", non_existing_groups_and_keys)
    def test_invalid_values_do_not_exist(self, group, key):
        """Test whether invalid values do not exist."""
        assert not self.configuration.valueExists(group, key)

    @pytest.mark.parametrize("group,key", options_groups_and_keys)
    def test_configuration_option_value_does_not_exist(self, group, key):
        """Test configuration options do not have values."""
        assert not self.configuration.valueExists(group, key)

    @pytest.mark.parametrize("group,key", options_groups_and_keys)
    def test_configuration_option_value_raises_error(self, group, key):
        """Test configuration options raise an error when trying to get the 
        value."""
        with pytest.raises(KeyError):
            self.configuration.getValue(group, key, False)

    @pytest.mark.parametrize("group,key", [
        ("options-group", "value1"),
        ("options-group", "value3"),
        ("options-group", "value4"),
    ])
    def test_default_exist(self, group, key):
        """Test the set default exist."""
        assert self.configuration.defaultExists(group, key)

    @pytest.mark.parametrize("group,key,value,args,expected", test_configuration_without_option_groups)
    def test_values_are_correct(self, group, key, value, args, expected):
        """Test whether the values are correct."""
        assert (self.configuration.getValue(group, key, False) == expected["value"])

    @pytest.mark.parametrize("group,key,value,args,expected", complete_test_configuration_with_defaults)
    def test_values_default_fallback(self, group, key, value, args, expected):
        """Test whether the default is returned if there is no value are correct."""
        assert (self.configuration.valueExists(group, key) or 
                    self.configuration.getValue(group, key, True) == expected["default_value"])

    @pytest.mark.parametrize("group,key,value,args,expected", test_configuration_without_option_groups)
    def test_value_types_are_correct(self, group, key, value, args, expected):
        """Test whether the value types are correct."""
        assert (type(self.configuration.getValue(group, key)) == expected["datatype"])

    @pytest.mark.parametrize("group,key,value,args,expected", complete_test_configuration_with_defaults)
    def test_default_is_correct(self, group, key, value, args, expected):
        """Test whether the defaults are correct."""
        assert (self.configuration.getDefault(group, key) == expected["default_value"])

    @pytest.mark.parametrize("group,key,value,args,expected", complete_test_configuration)
    def test_ask_if_not_present_is_correct(self, group, key, value, args, expected):
        """Test whether the ask if not peresent value correct."""
        if not "ask_if_not_present" in expected:
            expected["ask_if_not_present"] = False
            
        assert (self.configuration.getAskIfNotPresent(group, key) == 
                expected["ask_if_not_present"])

    @pytest.mark.parametrize("group,key,value,args,expected", complete_test_configuration)
    def test_restart_required_is_correct(self, group, key, value, args, expected):
        """Test whether the restart required value is correct."""
        if not "restart_required" in expected:
            expected["restart_required"] = False
            
        assert (self.configuration.getRestartRequired(group, key) == 
                expected["restart_required"])

    @pytest.mark.parametrize("group,key,value,args,expected", complete_test_configuration_width_description)
    def test_description_is_correct(self, group, key, value, args, expected):
        """Test whether the defaults are correct."""
        assert (self.configuration.getDescription(group, key) == 
                    expected["description"])

    def test_single_overwriting_value_is_correct(self):
        """Test if value is overwritten correctly and correctly be reset."""
        # check if value exists
        assert self.configuration.valueExists("overwrite-group", "value1")

        # check if value is the overwritten value
        assert (self.configuration.getValue("overwrite-group", "value1") ==
                "second")
        
        # check if resetting returns the initial value again
        self.configuration.resetValue("overwrite-group", "value1")
        assert (self.configuration.getValue("overwrite-group", "value1") == 
                "first")

    def test_multi_overwriting_value_is_correct(self):
        """Test if value is overwritten correctly and correctly be reset."""
        # check if value exists
        assert self.configuration.valueExists("overwrite-group", "value2")

        # check if value is the overwritten value
        assert (self.configuration.getValue("overwrite-group", "value2") == 6)
        
        # check if resetting 2 times returns the correct value
        self.configuration.resetValue("overwrite-group", "value2", 2)
        assert (self.configuration.getValue("overwrite-group", "value2") == 4)
        
        # check if resetting to inital value works
        self.configuration.resetValue("overwrite-group", "value2", -1)
        assert (self.configuration.getValue("overwrite-group", "value2") == 1)