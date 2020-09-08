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
global_tags = DM.GetPersistentTagGroup()
if global_tags.IsValid():
    s, __file__ = global_tags.GetTagAsString(file_tag_name);
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
	
	base_path = str(os.path.dirname(__file__))
	
	if base_path not in sys.path:
		sys.path.insert(0, base_path)

print("Initializing python environment...")

import traceback

try:
	import importlib

	import pylo
	import pylo.microscopes
	import pylo.cameras

	print("Preparing...")

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

	# configuration.setValue("pyjem-camera", "detector-name", "camera")
	# configuration.setValue("pyjem-camera", "image-size", 1024)

	controller = pylo.Controller(view, configuration)

	pylo.microscopes.PyJEMMicroscope.defineConfigurationOptions(controller.configuration)
	# pylo.cameras.PyJEMCamera.defineConfigurationOptions(controller.configuration)

	# controller.microscope = pylo.microscopes.PyJEMMicroscope(controller)
	controller.microscope = pylo.microscopes.DummyMicroscope(controller)
	# controller.camera = pylo.cameras.PyJEMCamera(controller)
	controller.camera = pylo.cameras.DummyCamera(controller)

	print("Done.")
	print("Starting.")
	controller.startProgramLoop()

	# pylo.execute()

except Exception as e:
	# dm-script error messages are very bad, use this for getting the error text and the 
	# correct traceback
	print("Exception: ", e)
	traceback.print_exc()