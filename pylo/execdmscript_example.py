try:
	import DigitalMicrograph as DM
	in_digital_micrograph = True
except ImportError:
	in_digital_micrograph = False

file_is_missing = False
try:
	if __file__ == "" or __file__ == None:
		file_is_missing = True
except NameError:
	file_is_missing = True

if in_digital_micrograph and file_is_missing:
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

import os
import sys
import pprint

if __file__ != "":	
	base_path = str(os.path.dirname(__file__))
	
	if base_path not in sys.path:
		sys.path.insert(0, base_path)

import execdmscript

script1 = """
number a = 40;
number b = -193.782;
number c = a + b;
string d = \"This is a test string\";
"""

script2 = """
number index;
TagGroup tg1 = NewTagGroup();
index = tg1.TagGroupCreateNewLabeledTag("key1");
tg1.TagGroupSetIndexedTagAsString(index, "value1");

index = tg1.TagGroupCreateNewLabeledTag("key2");
tg1.TagGroupSetIndexedTagAsNumber(index, c);

TagGroup tl1 = NewTagList();
tl1.TagGroupInsertTagAsString(infinity(), "list value 1");
tl1.TagGroupInsertTagAsString(infinity(), "list value 2");
tl1.TagGroupInsertTagAsNumber(infinity(), 100);

TagGroup tg2 = NewTagGroup();
index = tg2.TagGroupCreateNewLabeledTag("list");
tg2.TagGroupSetIndexedTagAsTagGroup(index, tl1);
index = tg2.TagGroupCreateNewLabeledTag("list-count");
tg2.TagGroupSetIndexedTagAsNumber(index, tl1.TagGroupCountTags());

index = tg1.TagGroupCreateNewLabeledTag("key3");
tg1.TagGroupSetIndexedTagAsTagGroup(index, tg2);

index = tg1.TagGroupCreateNewLabeledTag("key4");
tg1.TagGroupSetIndexedTagAsBoolean(index, 0);
"""

script3 = """
TagGroup tg3 = NewTagGroup();

index = tg3.TagGroupCreateNewLabeledTag("a");
tg3.TagGroupSetIndexedTagAsFloat(index, 10.0001);
index = tg3.TagGroupCreateNewLabeledTag("b");
tg3.TagGroupSetIndexedTagAsFloat(index, 11.0002);

TagGroup tl2 = newTagList();
"""

parent = os.path.expanduser("~")
fs = os.listdir(parent)
for e in fs:
    if os.path.isdir(os.path.join(parent, e)):
        script3 += "tl2.TagGroupInsertTagAsString(infinity(), \"{}\");\n".format(
            str(e).replace("\\", "\\\\").replace("\"", "\\\"")
        )

script3 += """
index = tg3.TagGroupCreateNewLabeledTag("files");
tg3.TagGroupSetIndexedTagAsTagGroup(index, tl2);

TagGroup tl3 = NewTagList();
tl3.TagGroupInsertTagAsString(infinity(), "a");
tl3.TagGroupInsertTagAsString(infinity(), "b");

TagGroup tl4 = NewTagList();
tl4.TagGroupInsertTagAsString(infinity(), "c");
tl4.TagGroupInsertTagAsNumber(infinity(), 5);

TagGroup tl5 = NewTagList();
tl5.TagGroupInsertTagAsString(infinity(), "d");
"""

readvars = {
    "a": int,
    "b": "number",
    "c": "dOuBle",
    "d": str,
    "tg1": "TagGroup",
    "tg3": {
        "a": "float",
        "b": float,
        "files": [str] * len(fs)
    },
    "tl3": "TagList",
    "tl4": [str, int],
    "tl5": list
}

try:
    script = execdmscript.exec_dmscript(script1, script2, script3, readvars=readvars)
    script()
    for key in readvars.keys():
        print("Variable '", key, "'")
        pprint.pprint(script[key])
except Exception as e:
    print("Exception:", e)
    raise e

# wrapper = execdmscript.DMScriptWrapper(script1, script2, script3, readvars=readvars)

# exec_script = wrapper.getExecDMScriptCode()

# print(exec_script)
# with open(os.path.join(os.path.dirname(__file__), "execdmscript.s"), "w+") as f:
#     f.write(exec_script)