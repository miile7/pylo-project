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

	controller.microscope = pylo.loader.getDevice("Dummy Microscope", controller)
	controller.camera = pylo.loader.getDevice("Dummy Camera", controller)

	tests = [
		# "error",
		# "hint",
		# "create-measurement",
		# "ask-for-decision",
		# "show-settings",
		"show-custom-tags",
		# "ask-for",
		# "show-running",
	]
	
	# view._exec_debug = True

	if "error" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Showing an error:")
		view.showError("Test error", "Test fix")

	if "hint" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Showing a hint:")
		view.showHint("Test hint")

	if "create-measurement" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Showing create Measurement")
		pprint.pprint(view.showCreateMeasurement(controller))

	if "ask-for-decision" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Ask for decision")
		print(view.askForDecision("Please click on one of the buttons.", 
								  ("Button 1", "Button 2", "Button 3", "Button 4")))

	if "show-settings" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Showing Settings")
		pprint.pprint(view.showSettings(configuration))

	if "show-custom-tags" in tests:
		from pylo.config import CUSTOM_TAGS_GROUP_NAME
		configuration.setValue(CUSTOM_TAGS_GROUP_NAME, "saved-key", "Saved value");
		print("")
		print("= " * 40)
		print("")
		print("Showing Custom Tags")
		pprint.pprint(view.showCustomTags(configuration))
		print("Configuration:")
		config_tags = {}
		for key in configuration.getKeys(CUSTOM_TAGS_GROUP_NAME):
		    config_tags[key] = configuration.getValue(CUSTOM_TAGS_GROUP_NAME, key)
		pprint.pprint(config_tags)

	if "ask-for" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Asking for values")
		inputs = (
			{"name": "Askval1", "datatype": str, "description": "Type in a str"},
			{"name": "Askval2", "datatype": int, "description": "Type in an int"},
			{"name": "Askval3", "datatype": float, "description": "Type in a float"}
		)
		pprint.pprint(view.askFor(*inputs))
	
	if "show-running" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Show running indicator")
		
		view.progress = 0;
		view.progress_max = 987
		
		def updateProgress(view):
			i = 1
			while i <= view.progress_max:
				if random.randint(0, 3) == 0:
					i += random.randint(1, 30)
				else:
					i += 1
				view.progress = i
				view.print("Setting view.progress = {}".format(i));
				time.sleep(0.1)
		
		thread = threading.Thread(target=updateProgress, args=(view,))
		thread.start()
		
		view.showRunning()
		view.progress_max = 0
		print("  Thread stopped.")
			

except Exception as e:
	print("Exception: ", e)
	traceback.print_exc()
	raise e