import DigitalMicrograph as DM

print("Initializing DigitalMicrograph environmnet...")

# the name of the tag is used, this is deleted so it shouldn't matter anyway
file_tag_name = "__python__file__"
# the dm-script to execute, double curly brackets are used because of the 
# python format function
script = ("\n".join((
    "DocumentWindow win = GetDocumentWindow(0);",
    "if(win.WindowIsvalid()){{",
        "if(win.WindowIsLinkedToFile()){{",
            "TagGroup tg = GetPersistentTagGroup();",
            "if(!tg.TagGroupDoesTagExist(\"{tag_name}\")){{",
                "number index = tg.TagGroupCreateNewLabeledTag(\"{tag_name}\");",
                "tg.TagGroupSetIndexedTagAsString(index, win.WindowGetCurrentFile());",
            "}}",
            "else{{",
                "tg.TagGroupSetTagAsString(\"{tag_name}\", win.WindowGetCurrentFile());",
            "}}",
        "}}",
    "}}"
))).format(tag_name=file_tag_name)

# execute the dm script
DM.ExecuteScriptString(script)

# read from the global tags to get the value to the python script
if DM.GetPersistentTagGroup():
    s, __file__ = DM.GetPersistentTagGroup().GetTagAsString(file_tag_name);
    if s:
        # delete the created tag again
        DM.ExecuteScriptString(
            "GetPersistentTagGroup()." + 
            "TagGroupDeleteTagWithLabel(\"{}\");".format(file_tag_name)
        )
    else:
        del __file__

try:
    __file__
except NameError:
    # set a default if the __file__ could not be received
    __file__ = ""

if __file__ != "":
    import os
    import sys
    
    base_path = str(os.path.dirname(os.path.dirname(__file__)))
    
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

import pprint
import traceback
import matplotlib.pyplot as plt

try:
    print("Importing pylo...")
    import pylo
    
    print("Creating configuration...")
    configuration = pylo.DMConfiguration()

    example_data = (
        ("group-1", "key-1", "value-1", {}),
        ("group-1", "key-2", "value-2", {"datatype": str, "default_value": "Default",
        "ask_if_not_present": True, "restart_required": True, 
        "description": "Test description"}),
        ("group-1", "key-3", 1, {"datatype": int, "default_value": 5,
        "ask_if_not_present": True}),
        ("group-1", "key-4", False, {"datatype": bool, "default_value": None}),
        ("group-5", "key-1", 1.1, {"datatype": float}),
        ("group-5", "key-2", "-1.1", {}),
    )
    
    print("Setting values...")
    # set the values
    for group, key, value, args in example_data:
        configuration.setValue(group, key, value, **args)
    
    print("Saving...")
    # save
    configuration.saveConfiguration()

    print("Creating new empty configuration...")
    # create new empty configuration
    configuration = pylo.DMConfiguration()

    print("Defining types...")
    # define the types without values
    for group, key, value, args in example_data:
        configuration.addConfigurationOption(group, key, **args)
    
    print("Loading values...")
    # load the values
    configuration.loadConfiguration()
    
    print("Checking:")
    # check the values
    for group, key, value, args in example_data:
        equal = configuration.getValue(group, key) == value
        print("Value for", group, "and", key, "is equal:", equal)
        assert equal
    
    print("")
    print("")
    print("=" * 80)
    print("All tests successfully")

except Exception as e:
    # dm-script error messages are very bad, use this for getting the error text and the 
    # correct traceback
    print("Exception: ", e)
    traceback.print_exc()
