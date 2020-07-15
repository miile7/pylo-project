import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import typing
import pytest
import pylo

###############################################################################
###                                                                         ###
###         Change only this for testing a different microscope             ###
###                                                                         ###
###############################################################################

# How to use
# **********
#
# 1. Create a new function `create_your_configuration()` that returns a tuple 
#    with 
#    - the configuration object (which is inheriting from pylo.AbstractConfiguration) 
#      at index 0
#    - arguments for the <YourConfiguration>::loadConfiguration() function at 
#      index 1, if not a tuple it is not passed to the load function
#    - arguments for the <YourConfiguration>::saveConfiguration() function at 
#      index 2, if not a tuple it is not passed to the save function
# 2. Add your `create_your_configuration()` to the configurations tuple
# 
# For an example check the commented code below. Also note the return type of 
# the `create_abstract_configuration()` which defines the return type formally.

# def create_abstract_configuration() -> typing.Tuple[pylo.AbstractConfiguration, typing.Union[tuple, None], typing.Union[tuple, None]]:
#     return plyo.AbstractConfiguration(), None, None

configurations = (
    # create_abstract_configuration
)

######################## general test code starts here ########################

example_data = (
    ("group-1", "key-1", "value-1", {}),
    ("group-1", "key-2", "value-2", {"datatype": str, "default_value": "Default",
     "ask_if_not_present": True, "restart_required": True}),
    ("group-1", "key-3", 1, {"datatype": int, "default_value": 5,
     "ask_if_not_present": True}),
    ("group-1", "key-4", False, {"datatype": bool, "default_value": None}),
    ("group-5", "key-1", 1.1, {"datatype": float}),
    ("group-5", "key-2", -1.1, {}),
)

@pytest.mark.skipif(len(configurations) == 0, reason="There is no configuration, the 'configurations' tuple is empty.")
class TestConfigurationPersistantSave:
    @pytest.mark.parametrize("create_configuration", configurations)
    def test_save_and_load(self, create_configuration):
        """Test if values that are set, then the configuration is saved and 
        then loaded again, are the same."""

        global example_data
        configuration, load_args, save_args = create_configuration()

        for group, key, value, args in example_data:
            configuration.setValue(group, key, value, **args)
        
        if isinstance(save_args, (list, tuple)):
            configuration.saveConfiguration(*save_args)
        else:
            configuration.saveConfiguration()
        
        configuration.configuration = {}
        
        if isinstance(load_args, (list, tuple)):
            configuration.loadConfiguration(*load_args)
        else:
            configuration.loadConfiguration()
        
        for group, key, value, args in example_data:
            assert configuration.getValue(group, key) == value
