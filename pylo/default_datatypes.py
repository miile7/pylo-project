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