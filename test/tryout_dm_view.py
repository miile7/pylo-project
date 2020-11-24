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
	import pylo.microscopes
	import pylo.cameras

	print("Preparing...");

	pylo.OFFLINE_MODE = True

	pylo = importlib.reload(pylo)
	pylo.microscopes = importlib.reload(pylo.microscopes)
	pylo.cameras = importlib.reload(pylo.cameras)

	view = pylo.DMView()
	configuration = pylo.IniConfiguration()

	# configuration.setValue("setup", "microscope-module", "pyjem_microscope.py")
	# configuration.setValue("setup", "microscope-class", "PyJEMMicroscope")
	# configuration.setValue("setup", "camera-module", "pyjem_camera.py")
	# configuration.setValue("setup", "camera-class", "PyJEMCamera")

	configuration.setValue("pyjem-camera", "detector-name", "camera")
	configuration.setValue("pyjem-camera", "image-size", 1024)

	controller = pylo.Controller(view, configuration)

	pylo.microscopes.PyJEMMicroscope.defineConfigurationOptions(controller.configuration)
	pylo.cameras.PyJEMCamera.defineConfigurationOptions(controller.configuration)

	controller.microscope = pylo.microscopes.PyJEMMicroscope(controller)
	controller.camera = pylo.cameras.PyJEMCamera(controller)

	tests = [
		# "error",
		# "hint",
		# "create-measurement",
		# "show-settings",
		"ask-for-decision",
		# "ask-for",
		# "show-running",
	]

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
		print(view.askForDecision("Please click on one of the buttons.", ("Button 1", "Button 2", "Button 3", "Button 4")))

	if "show-settings" in tests:
		print("")
		print("= " * 40)
		print("")
		print("Showing Settings")
		pprint.pprint(view.showSettings(configuration))

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