"""This files contains some general functions and objects that may be used 
anywhere in the pylo program.

Variables
---------
path_like : tuple
    A tuple that contains the types that match a path, can be used for 
    `isinstance()` and for `typing.Union[path_like]`
"""

import os
import math
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

def format_value(datatype: typing.Union[type, Datatype], value: typing.Any) -> str:
    """Get the `value` correctly formatted as a string.

    Parameters
    ----------
    datatype : type, Datatype
        The datatype
    value : any
        The value to format
    
    Returns
    -------
    str
        The `value` as a string
    """

    if isinstance(datatype, Datatype):
        return datatype.format(value)
    else:
        return "{}".format(value)

def parse_value(datatype: typing.Union[type, Datatype, None], value: typing.Any,
                suppress_errors: typing.Optional[bool]=True) -> typing.Any:
    """Parse the given `value` for the given `datatype`.

    Raises
    ------
    ValueError
        When the `value` is not parsable and `surpress_errors` is False
    TypeError
        When the `datatype` neither is a datatype nor a type and 
        `surpress_errors` is False

    Parameters
    ----------
    datatype : type, Datatype or None
        The datatype, if None is given the `value` is not converted
    value : any
        The value to parse
    suppress_errors : bool, optional
        If True no errors will be shown, if the value is not parsable a default
        value will be returned, default: True
    
    Returns
    -------
    any
        The `value` as the type of `datatype`
    """
        
    if datatype == bool:
        if isinstance(value, str):
            value = value.lower()
        
        true_vals = ["yes", "y", "true", "t", "on"]
        false_vals = ["no", "n", "false", "f", "off"]
        
        if value in true_vals:
            value = True
        elif value in false_vals:
            value = False
        else:
            try:
                value = float(value)
                error_context = None
            except ValueError as e:
                error_context = e

            if isinstance(value, float):
                # prevent issues with float rounding
                if math.isclose(value, 1):
                    value = True
                elif math.isclose(value, 0):
                    value = False
            
            if not isinstance(value, bool) and not suppress_errors:
                err = ValueError(("'{}' is not supported for a boolean. " + 
                                  "Please use {} to indicate a true " + 
                                  "boolean, use {} to represent false " + 
                                  "(case insensitive)").format(value,
                                    human_concat_list(true_vals + [1]),
                                    human_concat_list(false_vals + [0]),
                                ))
                
                if isinstance(error_context, Exception):
                    raise err from error_context
                else:
                    raise err
    
    if isinstance(datatype, (type, Datatype)):
        try:
            value = datatype(value)
        except Exception as e:
            if not suppress_errors:
                if isinstance(datatype, OptionDatatype):
                    raise ValueError(("The value '{}' is not an option of " + 
                                      "the list, please enter {}").format(
                                          value,
                                          human_concat_list(datatype.options)))
                else:
                    raise ValueError(("The value '{}' could not be " + 
                                      "converted to a '{}'. Please type in " + 
                                      "a correct value.").format(
                                        value, 
                                        get_datatype_human_text(datatype)))
            
            if (isinstance(datatype, Datatype) and 
                datatype.default_parse is not None):
                value =  datatype.default_parse
            elif datatype in (int, float):
                value =  0
            elif datatype == str:
                value =  ""
            else:
                value = value
    elif not suppress_errors:
        raise TypeError(("Cannot convert the value '{}' because the datatype " + 
                         "is not a datatype definition but a {}").format(value,
                            type(datatype)))
                
    return value

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