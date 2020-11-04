import typing

from .datatype import Datatype

def parse_int(v):
    """Parse the value `v` to an int.
    
    This function fixes parsing values like "100.1" to int by rounding.

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
    """Format the given value for the given format.

    Parameters
    ----------
    v : any
        The value to format
    f : str
        The format specification
    
    Returns
    -------
    str
        The formatted value
    """
    return ("{" + f + "}").format(parse_int(v))

int_type = Datatype(
    "int", 
    format_int,
    parse_int
)

def parse_hex(v):
    """Parse the given value.

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
    """Format the given value for the given format.

    Parameters
    ----------
    v : any
        The value to format
    f : str
        The format specification
    
    Returns
    -------
    str
        The formatted value
    """

    f = list(Datatype.split_format_spec(f))
    # alternative form, this will make 0x<number>
    f[3] = "#"
    # convert to hex
    f[8] = "x"
    # remove precision, raises error otherwise
    f[7] = ""

    return Datatype.join_format_spec(f).format(parse_int(v))

hex_int_type = Datatype(
    "hex", 
    format_hex,
    parse_hex
)