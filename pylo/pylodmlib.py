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
        ini_path = os.path.realpath(os.path.join(d, "devices.ini"))
        if os.path.exists(ini_path) and os.path.isfile(ini_path):
            # add the values to the ini loader
            additional_device_files.add(ini_path)
    
    return additional_device_files