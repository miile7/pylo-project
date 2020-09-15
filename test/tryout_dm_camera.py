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
	
	base_path = str(os.path.dirname(os.path.dirname(__file__)))
	
	if base_path not in sys.path:
		sys.path.insert(0, base_path)

import pprint
import traceback
import matplotlib.pyplot as plt

try:
	import pylo
	import pylo.cameras

	view = pylo.CLIView()
	configuration = pylo.AbstractConfiguration()
	pylo.cameras.DMCamera.defineConfigurationOptions(configuration)

	controller = pylo.Controller(view, configuration)

	# camera = pylo.cameras.DMTestCamera(controller)
	camera = pylo.cameras.DMCamera(controller)
	camera.show_images = True
	img = camera.recordImage()

	plt.imshow(img.image_data)
	pprint.pprint(img.tags)
except Exception as e:
	# dm-script error messages are very bad, use this for getting the error text and the 
	# correct traceback
	print("Exception: ", e)
	traceback.print_exc()