"""This files contains some general functions and objects that may be used 
anywhere in the pylo program.

Variables
---------
path_like : tuple
    A tuple that contains the types that match a path, can be used for 
    `isinstance()` and for `typing.Union[path_like]`
"""

import os
import sys
import math
import typing
import inspect
import logging
import pathlib
import datetime

from collections import defaultdict

from .datatype import Datatype
from .datatype import OptionDatatype
from .logginglib import log_debug
from .logginglib import log_error


# allow to check if a variable is a path
path_like = []
path_like.append(str)
# add the base class of all path objects
path_like.append(pathlib.PurePath)

if hasattr(os, "PathLike"):
    # keep support for python 3.5.6, os.PathLike is invented in python 3.6
    path_like.append(os.PathLike)

path_like = tuple(path_like)

def format_value(datatype: typing.Union[type, Datatype], value: typing.Any,
                suppress_errors: typing.Optional[bool]=False) -> str:
    """Get the `value` correctly formatted as a string.

    Parameters
    ----------
    datatype : type, Datatype
        The datatype
    value : any
        The value to format
    suppress_errors : bool, optional
        If True no errors will be shown, if the value is not parsable a default
        value will be returned, default: False
    
    Returns
    -------
    str
        The `value` as a string
    """

    if isinstance(datatype, Datatype):
        try:
            return datatype.format(value)
        except ValueError as e:
            if not suppress_errors:
                raise e
    
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

def human_value(var: "MeasurementVariable", val: typing.Any) -> typing.Any:
    """Convert the given `val` of the `var` to the human output.

    Parameters
    ----------
    var : MeasurementVariable
        The measurement variable
    val : any
        The value
    
    Returns
    -------
    any
        The formatted and calibrated value
    """
    if var.has_calibration:
        val = var.ensureCalibratedValue(val)
    
    if var.has_calibration and isinstance(var.calibrated_format, Datatype):
        val = format_value(var.calibrated_format, val)
    elif isinstance(var.format, Datatype):
        val = format_value(var.format, val)
    
    return val

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

class _ExpandVarsDefaultValue:
    """The default value for the `pylolib.expand_vars()` function if keys do 
    not exist"""
    
    def __str__(self):
        return ""
    
    def __getattr__(self, name):
        return self
    
    def __getitem__(self, name):
        return self
    
    def __contains__(self, name):
        return True
    
def expand_vars(*text: str, controller: typing.Optional["Controller"]=None,
                step: typing.Optional[dict]=None, 
                start: typing.Optional[dict]=None,
                series: typing.Optional[dict]=None,
                tags: typing.Optional[dict]=None, 
                counter: typing.Optional[int]=None, **kwargs) -> str:
    """Format the given text.

    The placeholders in the `text` are replaced with pythons format mini 
    language. The following objects can be used in the `text`:

    - 'varname': The variable names with the keys as measurement variable ids
      and the values as the corresponding name, only present if the `controller`
      is given
    - 'varunit': The variable unit with the keys as measurement variable ids
      and the values as the corresponding name, only present if the `controller`
      is given
    - 'step': The current step with the keys as measurement variable ids and 
      the values as machine values (uncalibrated and unformatted values), only
      present if the `step` is given
    - 'humanstep': The current step with the keys as measurement variable ids 
      and the values as human readable values (calibrated and formatted values), 
      only present if the `controller` and the `step` are given
    - 'start': The measurement start definition with the keys as measurement 
      variable ids and the values as machine values (uncalibrated and 
      unformatted values), only present if the `start` is given
    - 'humanstart': The measurement start definition with the keys as 
      measurement variable ids and the values as human readable values 
      (calibrated and formatted values), only present if the `controller` and
      the `start` are given
    - 'series': The measurement series nest definitions as a list of series
      nests (index 0 contains the most outer series dict with 'start', 'end' 
      and 'step-width', index 1 the next inner series and so on) as machine 
      values (uncalibrated and unformatted values), only present if the
      `series` is given
    - 'humanseries': The measurement series nest definitions as a list of series
      nests (index 0 contains the most outer series dict with 'start', 'end' 
      and 'step-width', index 1 the next inner series and so on) as human 
      readable values (calibrated and formatted values), only present if the 
      `controller` and the `series` are given
    - 'tags': The tags depending on the context, only present if the `tags` are 
      given
    - 'counter': The image counter, only present if the `counter` is given
    - 'time': The current time as a datetime object

    Additionally to the python format values, text can be grouped by using 
    '{?<...>}', '{_<...>}' and '{!<...>}' e.g. '{?the value is {step[value]}}'. 
    If the value `step["value"]` does not exist, the whole group is omitted if 
    '{?<...>}' is used, if '{_<...>}'  is used, only the value is omitted. If 
    '{!<...>}' is used, the key error of the python `format` function is 
    raised. The default group is using the underscore.

    Curly brackets can be escaped with anoter curly bracket. Note that nested 
    groups are currently not supported.
    
    Parameters
    ----------
    text : str
        The text to format
    
    Returns
    -------
    str
        The formatted name
    """
    from .controller import Controller
    from .measurement_steps import MeasurementSteps

    if isinstance(series, dict):
        series_nests = list(MeasurementSteps.getSeriesNests(series))
    else:
        series_nests = None

    format_kwargs = kwargs

    if isinstance(step, dict):
        format_kwargs["humanstep"] = {}
        format_kwargs["step"] = step
    
    if isinstance(start, dict):
        format_kwargs["humanstart"] = {}
        format_kwargs["start"] = start
    
    if isinstance(series, dict):
        format_kwargs["humanseries"] = []
        format_kwargs["series"] = series_nests

    if isinstance(controller, Controller):
        format_kwargs["varname"] = {}
        format_kwargs["varunit"] = {}

        for var in controller.microscope.supported_measurement_variables:
            if var.has_calibration and var.calibrated_name is not None:
                format_kwargs["varname"][var.unique_id] = str(var.calibrated_name)
            else:
                format_kwargs["varname"][var.unique_id] = str(var.name)

            if var.has_calibration and var.calibrated_unit is not None:
                format_kwargs["varunit"][var.unique_id] = var.calibrated_unit
            elif var.unit is not None:
                format_kwargs["varunit"][var.unique_id] = var.unit
            
            if isinstance(step, dict) and var.unique_id in step:
                format_kwargs["humanstep"][var.unique_id] = human_value(
                    var, step[var.unique_id])
            
            if isinstance(start, dict) and var.unique_id in start:
                format_kwargs["humanstart"][var.unique_id] = human_value(
                    var, start[var.unique_id])
        
        if isinstance(series_nests, (list, tuple)):
            for nest in series_nests:
                if ("variable" in nest and "start" in nest and "end" in nest and 
                    "step-width" in nest):
                    try:
                        var = controller.microscope.getMeasurementVariableById(
                            nest["variable"])
                        if var.has_calibration and var.calibrated_name is not None:
                            name = str(var.calibrated_name)
                        else:
                            name = str(var.name)
                        
                        format_kwargs["humanseries"].append({
                            "variable": name,
                            "start": human_value(var, nest["start"]),
                            "end": human_value(var, nest["end"]),
                            "step-width": human_value(var, nest["step-width"]),
                        })
                    except KeyError:
                        pass 

    if tags is not None:
        format_kwargs["tags"] = tags

    if counter is not None:
        format_kwargs["counter"] = counter
    
    format_kwargs["time"] = datetime.datetime.now()

    names = []
    for txt in text:
        groups = _split_expand_vars_groups(txt)

        name = []
        for modifier, t in groups:
            if modifier == "_":
                t = t.format_map(defaultdict(_ExpandVarsDefaultValue, **format_kwargs))
            else:
                try:
                    t = t.format(**format_kwargs)
                except KeyError as e:
                    if modifier == "?":
                        continue
                    else:
                        raise e
            name.append(t)
        
        names.append("".join(name))
        
    return names

def _split_expand_vars_groups(text: str) -> typing.List[typing.Tuple[str, str]]:
    """Split the given `text` into groups.

    A group is started with '{?' and ended with '}' while all other opening and
    closing brackets inbetween are ignored.

    Parameters
    ----------
    text : str
        The text to split
    
    Returns
    -------
    list of str
        The groups, with the modifier at index 0 and the text at index 1, if no 
        groups are defined the complete `text` will be in index 0 of the 
        returned list
    """

    groups = []
    bc = 0 # bracket count
    ig = False # in group or not
    lo = 0 # last start of group
    ebp = [] # escaped brackets positions
    mod = "_" # the mofifier to save
    lmod = "_" # the lastly used modifier
    for i, c in enumerate(text):
        if i in ebp:
            continue

        if c == "{" or c == "}":
            if i + 1 == len(text) or text[i + 1] != c:
                # current character is an semantic bracket
                if c == "{":
                    bc += 1
                elif c == "}":
                    bc -= 1
            else:
                # current character is an escaped bracket character, tell that 
                # this and the next brackets are escaping characters
                ebp.append(i)
                ebp.append(i + 1)
                continue
        
        end_i = i
        save_group = False
        if (not ig and c in ("?", "_", "!") and i > 0 and text[i - 1] == "{" and 
            i - 1 not in ebp):
            # curret character is a '?' followed by an unescaped bracket
            ig = bc
            save_group = True
            # remove the first curly bracket from saving it to the group
            end_i = i - 1
            lmod = mod
            mod = c
        elif ig != False and c == "}" and ig == bc + 1:
            ig = False
            save_group = True
            # group is closed, reset the modifier to the last modifier and the 
            # last modifier to the current modifier
            mod, lmod = lmod, mod
        
        if save_group:
            t = text[lo:end_i]
            if t != "":
                # add the the text from the last group opening as a group
                groups.append((lmod, t))
                
            # set the start of the coming group to the character after the 
            # current character
            lo = i + 1
    
    # add remaining text to the groups
    if lo < len(text):
        groups.append((mod, text[lo:]))
    
    return groups

def get_expand_vars_text(controller_given: typing.Optional[bool]=True,
                         step_given: typing.Optional[bool]=True,
                         start_given: typing.Optional[bool]=True,
                         series_given: typing.Optional[bool]=True,
                         tags_given: typing.Optional[bool]=True,
                         counter_given: typing.Optional[bool]=True) -> str:
    """Get the expand vars help.

    Parameters
    ----------
    controller_given, step_given, start_given, series_given, tags_given, 
    counter_given: bool
        Whether the corresponding parameter was/will be given for the 
        `expand_vars()` call this help is generated for

    Returns
    -------
    str
        The help text
    """

    placeholder_texts = []
    if step_given:
        placeholder_texts.append("Use {step[<variable-id>]} to access the " + 
                                 "current measurement step as uncalibrated " + 
                                 "and unformatted values.")
    if step_given and controller_given:
        placeholder_texts.append("Use {humanstep[<variable-id>]} to access " +
                                 "the current measurement step as human " + 
                                 "readable, formatted and calibrated values.")
    if start_given:
        placeholder_texts.append("Use {start[<variable-id>]} to access the " + 
                                 "current measurement series start definition " +
                                 "as uncalibrated and unformatted values.")
    if start_given and controller_given:
        placeholder_texts.append("Use {humanstart[<variable-id>]} to access " +
                                 "the current measurement step definition as" +
                                 "human readable, formatted and calibrated " + 
                                 "values.")
    if step_given:
        placeholder_texts.append("Use {step[<i>][start|step-width|end]} to " + 
                                 "access the current measurement series " + 
                                 "definition as uncalibrated and unformatted " + 
                                 "values where <i>=0 is the most outer and " + 
                                 "<i>=-1 the most inner series definition.")
    if step_given and controller_given:
        placeholder_texts.append("Use {humanstep[<i>][start|step-width|end]} " + 
                                 "to access the current measurement series " + 
                                 "definition as calibrated and formatted " + 
                                 "values where <i>=0 is the most outer and " + 
                                 "<i>=-1 the most inner series definition.")
    if controller_given:
        placeholder_texts.append("Use {varname[<variable-id>]} to access " +
                                 "the name of the given <variable-id>, use " + 
                                 "{varunit[<variable-id>]} to use the unit.")
    if tags_given:
        placeholder_texts.append("Use {tags[<tagname>]} to access the tags.")
    
    placeholder_texts.append("Use {time:%Y-%m-%d, %H:%M:%S} to access the " + 
                             "time. The time can be formatted with a format " + 
                             "expression after the colon. Use python date " + 
                             "format for formatting.")

    return "Some placeholders can be used. " + (" ".join(placeholder_texts))

def getDeviceText(additional_paths: typing.Optional[typing.Iterable]=None,
                  additional_device_files: typing.Optional[typing.Iterable]=None) -> str:
    """Get the device information text.

    The returned string contains all the directories where `devices.ini` files 
    can be placed in plus the `devices.ini` files that are loaded.

    Parameters
    ----------
    additional_paths : iterable
        Additional paths to show where device files can be
    additional_device_files : iterable
        Additional paths of `devices.ini` files

    Returns
    -------
    str
        The device files
    """

    try:
        additional_paths = set(additional_paths)
    except TypeError:
        additional_paths = set()

    try:
        additional_device_files = set(additional_device_files)
    except TypeError:
        additional_device_files = set()

    from . import loader
    from .config import PROGRAM_DATA_DIRECTORIES

    text = ["Device directories",
            "==================",
            "In the following directories `devices.ini` files can be placed:"
            ""]
    text += ["- {}".format(p) for p in PROGRAM_DATA_DIRECTORIES | additional_paths]

    text += ["",
            "Registered device files",
            "=======================",
            "The following `devices.ini` files are used when the program runs:"
            ""]
    text += ["- {}".format(p) for p in loader.device_ini_files | additional_device_files]
    
    return "\n".join(text)

def defineConfigurationOptions(configuration: "AbstractConfiguration", *, 
                               logger: typing.Optional[logging.Logger]=None) -> None:
    """Adds the configuration option of all classes that are loaded inside
    pylo (does NOT include the classes loaded via the loader)

    Parameters
    ----------
    configuration : AbstractConfiguration
        The configuration to load the definitions in
    logger : typing.Logger
        A logger to add debug logging information to
    """
    for name, _class in inspect.getmembers(sys.modules["pylo"], inspect.isclass):
        # print(name, _class, "@pylolib.defineConfigurationOptions()")
        if (hasattr(_class, "defineConfigurationOptions") and 
            callable(_class.defineConfigurationOptions)):
            # print("    has function", "@pylolib.defineConfigurationOptions()")
            try:
                # print("    executing function", "@pylolib.defineConfigurationOptions()")
                _class.defineConfigurationOptions(configuration)
                # print("    done", "@pylolib.defineConfigurationOptions()")
                if logger is not None:
                    log_debug(logger, ("Defining configuration options of " +   
                                       "class {}").format(name))
            except TypeError as e:
                # print("    error", e, "@pylolib.defineConfigurationOptions()")
                # arguemts
                if logger is not None:
                    log_error(logger, e, logging.DEBUG)