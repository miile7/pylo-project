import textwrap
import sys
import os
import re

maxlen = None

def prnt(*values, sep=" ", end="\n", file=sys.stdout, flush=False, inset=""):
    """Print some values.

    This is a wrapper that executes the python `print()` function but if a 
    `maxlen` is given, the text will be added with new line characters after 
    this width.

    Parameters
    ----------
    inset : str
        A inset to apply before every line (including the first)
    """

    global maxlen
    
    if isinstance(maxlen, int):
        text = sep.join(list(map(str, values)))
        text = wrap(text, inset)
        values = (text, )
        sep = ""

    print(*values, sep=sep, end=end, file=file, flush=flush)

def inpt(prompt, inset=""):
    """User input some values.

    This is a wrapper that executes the python `input()` function but if a 
    `maxlen` is given, the text will be added with new line characters after 
    this width.

    Parameters
    ----------
    inset : str
        A inset to apply before every line (including the first)
    """
    
    prompt = wrap(prompt, inset)
    return input(prompt)

def wrap(text, inset=""):
    """Add new lines to the given `text` if the text is longer that the 
    `maxlen`.

    If the `maxlen` is not given, the text will be returned.

    Parameters
    ----------
    inset : str
        A inset to apply before every line (including the first)
    """

    global maxlen

    if isinstance(maxlen, int):
        text = "\n".join([textwrap.fill(p) for p in text.splitlines()])
        # lines = textwrap.wrap(inset + text, maxlen, drop_whitespace=False, 
        #                       replace_whitespace=False)
        # text = ("\n" + inset).join(lines)
        text = textwrap.indent(text, inset)
    else:
        text = inset + text
    
    return text

def clear():
    """Clear the current command line."""
    os.system('cls' if os.name=='nt' else 'clear')

def _input_value(text, input_text, is_valid, error, post_process=None, **kwargs):
    """Input a value.

    Print the `text` to the user. The `input_text` is optional, if it is given
    it will be used before the input is asked from the user.

    The `is_valid` tells whether the value is valid, the `error` returns the
    error message if not.

    Parameters
    ----------
    text : str
        The text to show to the user
    input_text : str
        The text that is directly in front of the part to type in
    is_valid : callable
        A function that returns True if the value is valid and False if not,
        the value will be the first and only parameter, always as a string
    error : callable
        A function that returns the error message if the value is not valid 
        (if `is_valid` returns False). The first and only parameter will be the
        value as a string
    post_process : callable, optional
        A function to call after the input is detected, the first and only
        argument is the user input, if not callable it will be ignored, 
        default: None
    
    Keyword Args
    ------------
    lines_before : int
        The number of empty lines before the question starts, default: 2
    inset : int
        The number of spaces to use for the inset, default: 0
    add_inset : int
        The number of spaces to use before the question to ask, this is added
        to the `inset`
    add_choices : dict
        A dict where the keys hold the text that is also allowed, the value is 
        the value that is returned if the user puts in this text, default: {}
    post_process_add_choices : bool
        Whether to use the `post_process` function on the value of the 
        `add_choices` too or not, default: False
    
    Returns
    -------
    str
        The user input as a string
    """

    kwkeys = (
        ("lines_before", 2, int),
        ("inset", 0, int),
        ("add_inset", 3, int),
        ("add_choices", {}, dict),
        ("post_process_add_choices", False, bool),
    )

    for key, default, datatype in kwkeys:
        if not key in kwargs:
            kwargs[key] = default
        elif not isinstance(kwargs[key], datatype):
            raise TypeError(("The '{}' index of the kwargs has to be of type " + 
                            "{} but it is {}.").format(key, datatype, 
                            type(kwargs[key])))

    inset = " " * kwargs["inset"]
    prnt("\n" * kwargs["lines_before"], end="")
    if input_text != "":
        prnt(text, inset=inset)
    else:
        prnt(text, inset=inset, end="")

    tabs = " " * (kwargs["add_inset"] + kwargs["inset"])
    input_text = input_text + ": "

    inp = inpt(input_text, inset=tabs).lower().strip()
    while not is_valid(inp) and inp not in kwargs["add_choices"]:
        prnt("")
        prnt("Error: " + error(inp), inset=tabs)
        inp = inpt(input_text, inset=tabs).lower().strip()
    
    if inp in kwargs["add_choices"]:
        inp = kwargs["add_choices"][inp]
        is_choice = True
    else:
        is_choice = False

    if (callable(post_process) and not is_choice or 
        kwargs["post_process_add_choices"]):
        inp = post_process(inp)

    return inp

def input_inline_choices(text, choices, short_text="", **kwargs):
    """Let the user select a value from the `choices`.

    If the `choices` is a dict, the keys have to be the values the user can 
    type in. The corresponding value of the `choices` dict will then be 
    returned. If the `choices` is a list (or tuple), all the values will be 
    offered to the user. The selected index will then be returned.

    Parameters
    ----------
    text : str
        The text to show to the user
    choices : dict or list or tuple
        A dict that contains the user selectable options as the keys and the
        corresponding value to return as the value or a list of values to offer
        to the user. The corresponding index will be returned.
    short_text : str, optional
        A short text that will be shown in front of the input line
    
    Returns
    -------
    any
        The value in the `choices` dict the user selected the key of or the
        index of the element in the `choices` list the user selected
    """
    
    input_text = str(short_text)
    if input_text != "":
        input_text += " "
    
    input_text += "("

    if isinstance(choices, (list, tuple)):
        l = len(choices)
        choices = [(v, i) for i, v in enumerate(choices)]
    elif isinstance(choices, dict):
        l = len(choices)
        choices = choices.items()
    else:
        raise TypeError(("Choices is of type {} but needs to be a list, " + 
                          "tuple or dict").format(type(choices)))
    
    return_values_dict = {}
    for i, (k, v) in enumerate(choices):
        k = str(k)
        input_text += "[{}]{}".format(k[0], k[1:])
        return_values_dict[k[0].lower()] = v

        if i + 1 < l:
            input_text += "/"
    
    input_text += ")"

    ks = tuple(return_values_dict.keys())
    error_msg = "The value {} is not valid. Please use {}.".format("{}", 
                (", ".join(ks[:-1]) + " or " + str(ks[-1])))
    
    inp = _input_value(
        text, 
        input_text,
        lambda x: x in return_values_dict, 
        lambda x: error_msg.format(x),
        **kwargs
    )
    
    if inp in return_values_dict:
        return return_values_dict[inp]
    else:
        # if there are 'add_choices' given
        return inp

def input_yn(text, short_text="", **kwargs):
    """Ask a Yes-No-question to the user.

    Parameters
    ----------
    text : str
        The text to show to the user
    short_text : str, optional
        A short text that will be shown in front of the input line

    Returns
    -------
    bool
        True for "yes" and False for "no"
    """
    return input_inline_choices(text, {"Yes": True, "No": False}, short_text,
                                **kwargs)

def input_confirm(text, short_text="", **kwargs):
    """Ask the user to confirm something, "ok" and "cancel" are shown

    Parameters
    ----------
    text : str
        The text to show to the user
    short_text : str, optional
        A short text that will be shown in front of the input line

    Returns
    -------
    bool
        True for "Ok" and False for "Cancel"
    """
    return input_inline_choices(text, {"Ok": True, "Cancel": False}, short_text,
                                **kwargs)

def input_int(text, short_text="", min_value=None, max_value=None, **kwargs):
    """Ask the user for an integer value.

    Parameters
    ----------
    text : str
        The text to show to the user
    short_text : str, optional
        A short text that will be shown in front of the input line
    min_value : int, optional
        A minimum value, if not given there is no lower limit
    max_value : int, optional
        A maximum value, if not given there is no upper limit

    Returns
    -------
    int
        The value
    """
    short_text = [short_text]
    num_re = re.compile(r"^\s*-?\s*([\d]+|0(?:x|X)[\da-fA-F])\s*$")
    is_numeric = lambda x: num_re.match(x) is not None
    error_msg = "The value must only be digits or a hex value with leading '0x'"

    if isinstance(min_value, int) and isinstance(max_value, int):
        short_text.append("{} <= value <= {}".format(min_value, max_value))
        is_valid = lambda x: (is_numeric(x) and min_value <= int(x) and 
                              int(x) <= max_value)
        error_msg += " and {} <= value <= {}".format(min_value, max_value)
    elif isinstance(min_value, int):
        short_text.append("value >= {}".format(min_value))
        is_valid = lambda x: (is_numeric(x) and min_value <= int(x))
        error_msg += " and value >= {}".format(min_value)
    elif isinstance(max_value, int):
        short_text.append("value <= {}".format(max_value))
        is_valid = lambda x: (is_numeric(x) and int(x) <= max_value)
        error_msg += " and value <= {}".format(max_value)
    else:
        is_valid = is_numeric
    
    short_text = " ".join(short_text)
    error_msg += "."

    return _input_value(
        text, 
        short_text,
        is_valid, 
        lambda x: error_msg,
        post_process=lambda x: int(x, base=16) if str(x[0:2]).lower() == "0x" else int(x),
        **kwargs
    )

def input_text(text, short_text="", allow_empty_string=False, **kwargs):
    """Ask the user for a text value.

    Parameters
    ----------
    text : str
        The text to show to the user
    short_text : str, optional
        A short text that will be shown in front of the input line
    allow_empty_string : bool, optional
        Whether to allow the user to type nothing

    Returns
    -------
    str
        The value
    """
    if allow_empty_string:
        is_valid = lambda x: True
        error_msg = ""
    else:
        is_valid = lambda x: x != ""
        error_msg = "The value must not be empty"
    
    return _input_value(
        text, 
        short_text,
        is_valid, 
        lambda x: error_msg,
        **kwargs
    )

def input_filesave(text, short_text="", default_filename="", extensions="", 
                   allow_overwrite=False, **kwargs):
    """Show a file save to the user.

    Parameters
    ----------
    text : str
        The text to show to the user
    short_text : str, optional
        A short text that will be shown in front of the input line
    allow_empty_string : bool, optional

    Returns
    """
    
    short_text = [short_text]
    if extensions != "":
        short_text.append("({})".format(extensions))
    
    extensions = list(map(lambda x: x.strip().lower(), extensions.split(";")))
    
    short_text = " ".join(short_text)

    is_valid_parent_dir = lambda x: os.path.isdir(os.path.dirname(os.path.abspath(x)))
    is_valid_extension = lambda x: os.path.splitext(x)[1] in extensions
    is_filename = lambda x: x != "" and os.path.basename(x) != ""

    if allow_overwrite:
        file_not_exist = lambda x: False
    else:
        file_not_exist = lambda x: not os.path.isfile(os.path.abspath(x))

    is_valid = lambda x: (
        is_valid_parent_dir(x) and 
        file_not_exist(x) and 
        is_valid_extension(x) and
        is_filename(x)
    )

    error_msg = lambda x: (
        ("The directory {} does not exist.".format(os.path.dirname(os.path.abspath(x)))) 
        if not is_valid_parent_dir(x) else (
            ("The file {} already exists.".format(os.path.abspath(x)))
            if not file_not_exist(x) else (
                ("The extension {} is not valid. Use {}.".format(
                    os.path.splitext(os.path.abspath(x))[1],
                    ", ".join(extensions[:-1]) + " or {}".format(extensions[-1]))
                ) if not is_valid_extension(x) else (
                    "The path {} is not a file.".format(os.path.abspath(x))
                )
            )
        )
    )
    
    return _input_value(
        text, 
        short_text,
        is_valid, 
        error_msg,
        post_process=os.path.abspath,
        **kwargs
    )

if __name__ == "__main__":
    print(input_int("Input int"))