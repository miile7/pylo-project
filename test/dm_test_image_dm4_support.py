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

import os
import glob
import math
import time
import traceback

import numpy as np

try:
    import pylo
    import pylo.dm_image_dm4_support
    
    def remove_dirs(directories=None):
        """Remove all given directories recursively with files inside."""
        if not isinstance(directories, (list, tuple)):
            directories = glob.glob(os.path.join(test_root, "tmp-test-dm4-image-*"))
        
        for directory in directories:
            if os.path.exists(directory):
                directory = str(directory)
                for f in os.listdir(directory):
                    path = os.path.join(directory, f)
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        remove_dirs((path), )
            
                os.removedirs(directory)
    
    def recursive_test_image_tags(image, tags, path=""):
        if isinstance(tags, (list, tuple)):
            iterator = enumerate(tags)
        else:
            iterator = tags.items()

        for key, value in iterator:
            if isinstance(key, int):
                key = "[{}]".format(key)
            
            p = path + key
            if isinstance(value, (dict, list, tuple)):
                recursive_test_image_tags(image, value, p + ":")
                continue
            elif isinstance(value, str):
                s, v = image.GetTagGroup().GetTagAsString(p)
            elif isinstance(value, float):
                s, v = image.GetTagGroup().GetTagAsFloat(p)
            elif isinstance(value, int):
                s, v = image.GetTagGroup().GetTagAsLong(p)
            elif isinstance(value, bool):
                s, v = image.GetTagGroup().GetTagAsBoolean(p)
            else:
                print("  Type is invalid for {}".format(p))
                continue

            print("  Value for {} exists: ".format(p), s)
            assert s

            if isinstance(value, float):
                value_correct = math.isclose(v, value, abs_tol=1e-6)
            else:
                value_correct = v == value
            print("  Value for {} is correct".format(p), value_correct)
            if not value_correct:
                print("    ", v, "!=", value)
            assert value_correct

    test_root = os.path.join(os.path.dirname(__file__))

    # clear all test directories
    remove_dirs()

    # create test dirs
    tmp_path = os.path.join(test_root, "tmp-test-dm4-image-{}".format(int(time.time() * 100)))
    os.makedirs(tmp_path, exist_ok=True)

    image_data = (np.random.random((64, 64)) * 255).astype(dtype=np.uint8)
    tags = {
        "Test tag": "Test",
        "Test tag 2": 100,
        "Test tag 3": False,
        "Test tag 4": {
            "A": -1.1,
            "B": -2.3,
            "C": ["X", "Y", "Z"]
        },
        "Test tag 5": [
            "U",
            "V",
            "W",
            {"T": True, "F": False}
        ]
    }

    print("")
    print("= " * 40)
    print("")
    print("Testing saving image:")
    start_time = time.time()
    image = pylo.Image(image_data, tags)
    img_path = os.path.join(tmp_path, "test-image.dm4")

    thread = image.saveTo(img_path)
    thread.join()
    
    if len(thread.exceptions) > 0:
        for e in thread.exceptions:
            raise e

    file_exists = os.path.isfile(img_path)
    print("File exists: ", file_exists)
    assert file_exists

    file_new = os.path.getmtime(img_path) >= start_time
    print("File is created after the start time: ", file_new)
    assert file_new

    img = DM.OpenImage(img_path)
    data_correct = (img.GetNumArray() == image_data).all()
    print("The data is correct: ", data_correct)
    assert data_correct

    print("Checking tags:")
    recursive_test_image_tags(img, tags)
    
    print("")
    print("= " * 40)
    print("")
    print("Testing overwriting image:")
	
    overwrite_start_time = time.time()
    tags = {"Overwriting": True}
    image_data = (np.random.random((64, 64)) * 255).astype(dtype=np.uint8)
    image = pylo.Image(image_data, tags)

    thread = image.saveTo(img_path)
    thread.join()
    
    if len(thread.exceptions) > 0:
        for e in thread.exceptions:
            raise e

    file_exists = os.path.isfile(img_path)
    print("File exists: ", file_exists)
    assert file_exists

    file_new = os.path.getmtime(img_path) >= overwrite_start_time
    print("File is created after the start time: ", file_new)
    assert file_new

    del img

    print("")
    print("")
    print("=" * 80)
    print("All tests successfully")
    
    # clear all test directories
    remove_dirs()
    
except Exception as e:
    print("Exception: ", e)
    traceback.print_exc()