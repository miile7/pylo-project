import os
import typing

from .datatype import Datatype

def parse_int(v: typing.Any) -> int:
    """Parse the value `v` to an int.
    
    This function fixes parsing values like "100.1" to int by rounding.

    Raises
    ------
    ValueError
        When the value `v` could not be parsed

    Parameters
    ----------
    v : int, float, str, any
        The value to parse
    
    Returns
    -------
    int
        The converted int
    """
    return int(float(v))

def format_int(v: typing.Any, f: typing.Optional[str]="") -> str:
    """Format the given value to an int.

    Parameters
    ----------
    v : any
        The value to format
    f : str
        The format specification
    
    Returns
    -------
    str
        The formatted value or an emtpy string if it is not formattable
    """
    try:
        v = parse_int(v)
    except ValueError:
        return ""
    return ("{" + f + "}").format(v)

int_type = Datatype("int", format_int, parse_int)
int_type.default_parse = 0

def parse_hex(v: typing.Any) -> int:
    """Parse the given value to an integer on the base of 16.

    Raises
    ------
    ValueError
        When the value `v` could not be parsed

    Parameters
    ----------
    v : int, float, str, any
        If int or float are given, the number is returned as an int, if a
        string is given it is treated as a hex number (values after the decimal
        separator are ignored), everything else will be tried to convert to a 
        16 base int
    
    Returns
    -------
    int
        The converted int
    """

    if isinstance(v, (int, float)):
        return int(v)
    elif isinstance(v, str):
        v = v.split(".")
        return int(v[0], base=16)
    else:
        return int(v, base=16)

def format_hex(v: typing.Any, f: typing.Optional[str]="") -> str:
    """Format the given value to a hex number.

    Parameters
    ----------
    v : any
        The value to format
    f : str
        The format specification
    
    Returns
    -------
    str
        The formatted value or an empty string if it is not formattable
    """

    f = list(Datatype.split_format_spec(f))
    # alternative form, this will make 0x<number>
    f[3] = "#"
    # convert to hex
    f[8] = "x"
    # remove precision, raises error otherwise
    f[7] = ""

    try:
        v = parse_int(v)
    except ValueError:
        return ""

    return Datatype.join_format_spec(f).format(v)

hex_int_type = Datatype("hex", format_hex, parse_hex)
hex_int_type.default_parse = 0

def parse_dirpath(v: typing.Any) -> str:
    """Parse the given value to be the absolute path of the directory.

    If a file is given, the directory name (the containing directory) is 
    returned, the absolute path of the `v` otherwise.

    Raises
    ------
    ValueError
        When the value `v` could not be parsed

    Parameters
    ----------
    v : any
        The path expression to parse
    
    Returns
    -------
    str
        The directory path
    """
    try:
        if os.path.isfile(v):
            return os.path.abspath(os.path.dirname(v))
        else:
            return os.path.abspath(v)
    except TypeError as e:
        raise ValueError(("The value '{}' could not be parsed to a directory " + 
                          "path").format(v)) from e

def format_dirpath(v: typing.Any, f: typing.Optional[str]="") -> str:
    """Format the given value to an absolute directory path.

    If the value is a plain string, it will be relative to the current working
    directory.

    Parameters
    ----------
    v : any
        The value to format
    f : str
        The format specification
    
    Returns
    -------
    str
        The formatted value or an empty string if it is not formattable
    """
    try:
        return str(parse_dirpath(v))
    except ValueError:
        return ""

dirpath_type = Datatype("dirpath", format_dirpath, parse_dirpath)
dirpath_type.default_parse = ""

def parse_filepath(v: typing.Any) -> str:
    """Parse the given value to be the absolute file path.

    Raises
    ------
    ValueError
        When the value `v` could not be parsed

    Parameters
    ----------
    v : any
        The path expression to parse
    
    Returns
    -------
    str
        The file path
    """
    try:
        return os.path.abspath(v)
    except TypeError as e:
        raise ValueError(("The value '{}' could not be parsed to a directory " + 
                          "path").format(v)) from e

def format_filepath(v: typing.Any, f: typing.Optional[str]="") -> str:
    """Format the given value to an absolute path.

    If the value is a plain string, it will be relative to the current working
    directory.

    Parameters
    ----------
    v : any
        The value to format
    f : str
        The format specification
    
    Returns
    -------
    str
        The formatted value or an empty string if it is not formattable
    """
    try:
        return str(parse_filepath(v))
    except ValueError:
        return ""

filepath_type = Datatype("filepath", format_filepath, parse_filepath)
filepath_type.default_parse = ""

def float_np(n: int) -> Datatype:
    """Get a float datatype that rounds to `n` digits.

    Parameters
    ----------
    n : int
        The number of digits after the decimal separator
    
    Returns
    -------
    Datatype
        The datatype
    """

    def format_float_np(v: typing.Any, f: typing.Optional[str]="") -> str:
        """Format the given value to a float.

        Parameters
        ----------
        v : any
            The value to format
        f : str
            The format specification
        
        Returns
        -------
        str
            The formatted value or an emtpy string if it is not formattable
        """
        try:
            v = float(v)
        except ValueError:
            return ""
            
        f = list(Datatype.split_format_spec(f))
        if f[7] == "":
            f[7] = str(n)
        f[8] = "f"

        f = Datatype.join_format_spec(f)

        return f.format(v)

    dt = Datatype("float_{}p".format(n), format_float_np, float)
    dt.default_parse = "0.00"

    return dt