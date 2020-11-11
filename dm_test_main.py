import DigitalMicrograph as DM

DM.ClearResults()
print("Starting, this can take a while...")
print("")

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
	
	base_path = str(os.path.dirname(__file__))
	
	if base_path not in sys.path:
		sys.path.insert(0, base_path)

print("Initializing python environment...")

try:
	import pylo

	print("Preparing...")
	# pylo.OFFLINE_MODE = True

	# create view and configuration, both using the DM environmnent
	view = pylo.DMView()
	configuration = pylo.DMConfiguration()

	# set the microscope to use the PyJEM microscope
	configuration.setValue("setup", "microscope-module", "pylo.microscopes")
	configuration.setValue("setup", "microscope-class", "PyJEMTestMicroscope")

	# use the DMCamera as the camera
	configuration.setValue("setup", "camera-module", "pylo.cameras")
	configuration.setValue("setup", "camera-class", "DMTestCamera")
	print("Done.")
	print("Starting...")

	# redirect all print() calls to the debug window
	DM.SetOutputTo(2)
	pylo.execute(view, configuration)
	# set everything back to the results window
	DM.SetOutputTo(0)

	print("Done with everything.")
	print("Exiting.")
except Exception as e:
	# dm-script error messages are very bad, use this for getting the error 
	# text and the correct traceback
	print("{}: ".format(e.__class__.__name__), e)
	import traceback
	traceback.print_exc()