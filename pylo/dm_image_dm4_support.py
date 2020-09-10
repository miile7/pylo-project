try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
    DM = None

import os
import sys
import typing

if DM is not None:
    # for development only, execdmscript is another module that is developed
    # separately
    try:
        import dev_constants
        load_from_dev = True
    except (ModuleNotFoundError, ImportError) as e:
        load_from_dev = False

    if load_from_dev:
        if hasattr(dev_constants, "execdmscript_path"):
            if not dev_constants.execdmscript_path in sys.path:
                sys.path.insert(0, dev_constants.execdmscript_path)
            
    import execdmscript
else:
    raise RuntimeError("execdmscript can only be imported inside " + 
                       "the Digital Micrograph program by Gatan.")

from .image import Image

def _export_image_object_to_dm4(file_path: str, image: Image) -> None:
    """Save the given image object to the given file_path as a dm4 file.

    The if the file already exists, it will be overwritten silently. If the 
    parent directory doesn't exist, or any error occurres, an Exception will be
    raised.

    Parameters:
    -----------
    file_path : str
        The path of the file to save to including the file name and the
        extension, if the path already exists, it will silently be 
        overwritten
    image : Image
        The image object to save
    """

    if DM is None:
        raise RuntimeError("This is only executable in Gatan Microscopy Suite.")
    
    # create the name
    name = os.path.basename(file_path)
    name, _ = os.path.splitext(name)

    img = DM.CreateImage(image.image_data)
    img.SetName(name)

    # save the tags
    if isinstance(image.tags, dict) and image.tags != {}:
        tag_group = execdmscript.convert_to_taggroup(image.tags)
        img.GetTagGroup().CopyTagsFrom(tag_group)
    
    # remove file for overwriting, DM does not do that but that is the expected
    # behaviour of this function
    if os.path.isfile(file_path):
        os.remove(file_path)

    # save to the file
    img.SaveAsGatan(file_path)

    # remove image reference to free the memory
    del img

Image.export_extensions["dm4"] = _export_image_object_to_dm4