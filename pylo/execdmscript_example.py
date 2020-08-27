import os

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
tg3.TagGroupSetIndexedTagAsFloat(index, 0.0001);
index = tg3.TagGroupCreateNewLabeledTag("b");
tg3.TagGroupSetIndexedTagAsFloat(index, 0.0002);

TagGroup tl2 = newTagList();
"""

fs = os.listdir(os.path.expanduser("~"))
for e in fs:
    script3 += "tl2.TagGroupInsertTagAsString(infinity(), \"{}\");\n".format(
        str(e).replace("\\", "\\\\").replace("\"", "\\\"")
    )

script3 += """
index = tg3.TagGroupCreateNewLabeledTag("files");
tg3.TagGroupSetIndexedTagAsTagGroup(index, tl2);
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
    }
}

wrapper = execdmscript.DMScriptWrapper(script1, script2, script3, readvars=readvars)
exec_script = wrapper.getExecDMScriptCode()

print(exec_script)
with open(os.path.join(os.path.dirname(__file__), "execdmscript.s"), "w+") as f:
    f.write(exec_script)