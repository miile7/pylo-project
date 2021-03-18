import os
import typing


from . import FallbackModuleNotFoundError
from . import ExecutionOutsideEnvironmentError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
    raise ExecutionOutsideEnvironmentError("Could not load module DigitalMicrograph.") from e

from . import config
from . import logginglib

logger = logginglib.get_logger("pylodmlib.py", create_msg=False)

def get_additional_dirs() -> typing.Set[str]:
    """Get the additional data directories that are supported if PyLo is
    executed inside GMS.

    Returns
    -------
    set of str
        A set containing the absolute paths to the directories where data can
        be places
    """

    # adding device paths
    # get device paths from dm-script and save them into global tags
    application_dir_names = ("application", "preference", "plugin")
    dir_path_tag_name = "__dir_path_{dirname}"
    dmscript_template = "\n".join((
        "if(!GetPersistentTagGroup().TagGroupDoesTagExist(\"{tagname}\")){{",
            "GetPersistentTagGroup().TagGroupCreateNewLabeledTag(\"{tagname}\");",
        "}}",
        "GetPersistentTagGroup().TagGroupSetTagAsString(\"{tagname}\", GetApplicationDirectory(\"{dirname}\", 0));"
    ))

    # create the script
    dmscript = []
    for name in application_dir_names:
        dmscript.append(dmscript_template.format(tagname=dir_path_tag_name.format(dirname=name),
                                                dirname=name))
    logginglib.log_debug(logger, ("Getting dm paths for device ini files " + 
                                  "by executing dmscript '{}'").format(dmscript))
    # execute the script
    DM.ExecuteScriptString("\n".join(dmscript))

    dirs = set()

    # read the values from the global tags
    for name in application_dir_names:
        tn = dir_path_tag_name.format(dirname=name)
        s, dir_path = DM.GetPersistentTagGroup().GetTagAsString(tn)
        if s and os.path.exists(dir_path):
            dirs.add(dir_path)
    
        DM.GetPersistentTagGroup().DeleteTagWithLabel(tn)
    
    return dirs

def get_additional_device_files() -> typing.Set[str]:
    """Get the additional `devices.ini` files that are found in the additional
    directories returned by `get_additional_dirs()`

    Returns
    -------
    set of str
        The paths of the `devices.ini` files
    """
    
    additional_device_files = set()

    for d in get_additional_dirs():
        for f in ("devices.ini", "plugins.ini"):
            ini_path = os.path.realpath(os.path.join(d, f))
            if os.path.exists(ini_path) and os.path.isfile(ini_path):
                # add the values to the ini loader
                additional_device_files.add(ini_path)
    
    return additional_device_files

def _gettag(name: str, datatype: typing.Optional[type]=str, 
            base: typing.Optional[str]="Private:Save Numbered") -> typing.Any:
    """Get the tag value from the persistent tags.

    Raises
    ------
    RuntimeError
        When the tag does not exist

    Parameters
    ----------
    name : str
        The tag name
    datatype : type
        The datatype, only str and bool are currently supported
    base : str
        The base path without the trailing colon to add in front of the name
    
    Returns
    -------
    any
        The value of the given `datatype`
    """
    tag = "{}:{}".format(base, name)

    if datatype == str:
        s, v = DM.GetPersistentTagGroup().GetTagAsString(tag)
    elif datatype == bool:
        s, v = DM.GetPersistentTagGroup().GetTagAsBoolean(tag)

    if not s:
        raise RuntimeError("Could not find the tag '{}'".format(tag))
    
    return v

def get_savedir() -> str:
    """Get the save directory from the persistent tags from the save numbered
    settings.

    Raises
    ------
    RuntimeError
        When the persistent tag does not exist

    Returns
    -------
    str
        The directory name to save the images to
    """
    return _gettag("File Directory")

def get_savetype() -> str:
    """Get the save format as the extension.

    Raises
    ------
    RuntimeError
        When the options are not found
    ValueError
        When the format is not supported

    Returns
    -------
    str
        The file extension to use
    """
    
    save_format = _gettag("File Save Option")
    if save_format == "Save Image":
        save_format = _gettag("Save Image Format")
    else:
        save_format = _gettag("Save Display Format")

    if save_format == "Gatan Format":
        return "dm4"
    elif save_format == "Gatan 3 Format":
        return "dm3"
    elif save_format == "TIFF Format":
        return "tif"
    elif save_format == "BMP Format":
        return "bmp"
    elif save_format == "GIF Format":
        return "gif"
    elif save_format == "JPEG/JFIF Format":
        return "jpg"
    elif save_format == "Text Format":
        return "txt"
    else:
        raise ValueError("The format '{}' is not supported.".format(save_format))

def get_savename() -> str:
    """Get the savename from the persistent tags from the save numbered 
    settings

    Raises
    ------
    RuntimeError
        When the persistent tags do not exists

    Returns
    -------
    str
        The save numbered settings filename (without extension) with eventual 
        placeholders for the `pylolib.expand_vars()` function
    """
    
    kind = _gettag("File Name Option")
    
    if kind == "Build":
        # build from values
        use_detector = _gettag("Build Name:Detector", datatype=bool)
        use_magnification = _gettag("Build Name:Magnification", datatype=bool)
        use_operator = _gettag("Build Name:Operator", datatype=bool)
        use_specimen = _gettag("Build Name:Specimen", datatype=bool)
        use_voltage = _gettag("Build Name:Voltage", datatype=bool)

        texts = []
        if use_detector:
            texts.append("{tags[detector]}")
        if use_magnification:
            texts.append("{tags[magnification]}")
        if use_operator:
            texts.append("{tags[operator]}")
        if use_specimen:
            texts.append("{tags[specimen]}")
        if use_voltage:
            texts.append(_gettag("Voltage", base="Microscope Info"))

        sep = _gettag("Build Name:Separator")

        return sep.join(texts)

    elif kind == "Type":
        # create text
        name = _gettag("Name")
        sep = _gettag("Index Separator")
        num = _gettag("Number")

        return "{}{}{{counter}}".format(name, sep, num)
        