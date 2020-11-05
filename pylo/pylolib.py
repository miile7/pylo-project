"""This files contains some general functions and objects that may be used 
anywhere in the pylo program.

Variables
---------
path_like : tuple
    A tuple that contains the types that match a path, can be used for 
    `isinstance()` and for `typing.Union[path_like]`
"""

import os
import typing
import pathlib

from .datatype import Datatype
from .datatype import OptionDatatype

# allow to check if a variable is a path
path_like = []
path_like.append(str)
# add the base class of all path objects
path_like.append(pathlib.PurePath)

if hasattr(os, "PathLike"):

    # keep support for python 3.5.6, os.PathLike is invented in python 3.6
    path_like.append(os.PathLike)

path_like = tuple(path_like)

def format_value(datatype: typing.Union[type, Datatype, list, tuple], value: typing.Any) -> str:
    """Get the `value` correctly formatted as a string.

    Parameters
    ----------
    datatype : type, Datatype, list or tuple
        The datatype or a list of allowed values
    
    Returns
    -------
    str
        The `value` as a string
    """

    if isinstance(datatype, Datatype):
        return datatype.format(value)
    else:
        return "{}".format(value)

def get_datatype_name(datatype: typing.Union[type, Datatype, list, tuple]) -> str:
    """Get the datatype name to identify the datatype

    Parameters
    ----------
    datatype : type, Datatype, list or tuple
        The datatype
    
    Returns
    -------
    str
        The datatype name
    """

    if datatype == int:
        type_name = "int"
    elif datatype == float:
        type_name = "float"
    elif datatype == bool:
        type_name = "boolean"
    elif datatype == str:
        type_name = "string"
    elif isinstance(datatype, (list, tuple)):
        type_name = "list"
    elif hasattr(datatype, "name") and isinstance(datatype.name, str):
        type_name = datatype.name
    elif hasattr(datatype, "__name__") and isinstance(datatype.__name__, str):
        type_name = datatype.__name__
    else:
        type_name = str(datatype)
    
    return type_name

def get_datatype_human_text(datatype: typing.Union[type, Datatype, list, tuple]) -> str:
    """Get the datatype name for humans.

    Parameters
    ----------
    datatype : type, Datatype, list or tuple
        The datatype
    
    Returns
    -------
    str
        A string that is human readable for the `datatype`
    """

    if datatype == int:
        type_name = "integer number"
    elif datatype == float:
        type_name = "decimal number"
    elif datatype == bool:
        type_name = "boolean value (yes/y/true/t/on or no/n/false/f/off)"
    elif datatype == str:
        type_name = "text"
    elif isinstance(datatype, OptionDatatype) or isinstance(datatype, (list, tuple)):
        type_name = "possibility list"
    elif hasattr(datatype, "name") and isinstance(datatype.name, str):
        type_name = datatype.name
    elif hasattr(datatype, "__name__") and isinstance(datatype.__name__, str):
        type_name = datatype.__name__
    else:
        type_name = str(datatype)
    
    return type_name

def human_concat_list(x: typing.Sequence, surround: typing.Optional[str]="'", 
                      separator: typing.Optional[str]=", ", 
                      word: typing.Optional[str]=" or "):
    """Concatenate the list `x` with `separator` and the last time with the 
    `word`.

    Example:
    ```python
    >>> human_concat_list(["a", "b", "c"])
    "'a', 'b' or 'c'"
    >>> human_concat_list(["a", "b"])
    "'a' or 'b'"
    >>> human_concat_list(["a", "b", "c"], surround="*", separator=";", 
    ... word="and")
    "*a*;*b* and *c*"
    ```

    Parameters
    ----------
    x : Sequence
        The sequence to concat
    surround : str, optional
        The characters to surround the list items with
    separator : str, optional
        The text to print between two list items (except the last two), 
        default: ", "
    word : str, optional
        The word to use between the last two items
    
    Returns
    -------
    str
        The concatenated list
    """
    if surround != "":
        x = map(lambda y: "{s}{y}{s}".format(s=surround, y=y), x)
    if word != "":
        word = str(word)
    x = list(x)

    if len(x) > 2:
        return separator.join(x[:-1]) + word + x[-1]
    elif len(x) > 1:
        return word.join(x)
    elif len(x) == 1:
        return x[0]
    elif surround != "":
        return ""
    else:
        return surround * 2

__dirpath_parse = lambda v: (os.path.abspath(os.path.dirname(v)) 
                             if os.path.isfile(v) else os.path.abspath(v))
dirpath_type = Datatype(
    "dirpath", 
    lambda v, f: str(__dirpath_parse(v)),
    __dirpath_parse
)
filepath_type = Datatype(
    "filepath", 
    lambda v, f: str(os.path.abspath(v)),
    lambda v: str(os.path.abspath(v))
)