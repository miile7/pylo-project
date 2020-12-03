import DigitalMicrograph as DM

print("Initializing DigitalMicrograph environmnet...");

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

print("Initializing python environment...");

import pprint
import time
import random
import threading
import importlib
import traceback

try:
    import pylo

    print("Preparing...");

    view = pylo.DMView()
    configuration = pylo.AbstractConfiguration()
    
    controller = pylo.Controller(view, configuration)

    controller.microscope = pylo.loader.getDevice("Digital Micrograph Microscope", controller)
    controller.camera = pylo.loader.getDevice("Dummy Camera", controller)

    tests = [
        "set-lorentz-mode",
        "get-lorentz-mode",
    ]

    setgettests = {
        "om-current": random.randint(2, 10),
        "x-tilt": random.randint(2, 10),
        # "y-tilt": 5,
        # "ol-current": 0x20,
    }
    hex_display = ("ol-current", "om-current")

    if "set-lorentz-mode" in tests:
        print("")
        print("= " * 40)
        print("")
        print("Setting microscope into lorentz mode")
        controller.microscope.setInLorentzMode(True)

    if "get-lorentz-mode" in tests:
        print("")
        print("= " * 40)
        print("")
        print("Checking if microscope is in lorentz mode")
        print("In lorentz-mode:", controller.microscope.getInLorentzMode())

    for var_id, value in setgettests.items():
        print("")
        print("= " * 40)
        print("")
        
        if var_id in hex_display:
            info = " (0x{:x})".format(value)
        else:
            info = ""
        
        print("Setting {} to {}{}".format(var_id, value, info))
        controller.microscope.setMeasurementVariableValue(var_id, value)

        print("Getting {}: ".format(var_id), end="")
        val = controller.microscope.getMeasurementVariableValue(var_id)
        print(val, end="")

        if var_id in hex_display:
            print(" (0x{:x})".format(val), end="")
        
        print("")

except Exception as e:
    print("Exception: ", e)
    traceback.print_exc()
    raise e