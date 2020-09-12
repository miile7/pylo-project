import typing
import re

# the regular expression that matches any valid format specification, each 
# group contains one specification item
format_reg = re.compile(r"^((?:.(?=(?:<|>|\^)))?)([<>=^]?)([\-+ ]?)(#?)(0?)([\d]*)([_,]?)((?:\.[\d]+)?)([bcdeEfFgGnosxX%]?)$")

class Datatype:
    def __init__(self, name: str, format: callable, parse: typing.Optional[callable]=None) -> None:
        """Create a new datatype.

        Example:
        -------
        ```python
        >>> Datatype("string", 
        ...          lambda v, f: ("{" + f + "}").format(v), 
        ...          lambda x: str(x))
        ```

        Parameters
        ----------
        name :  str
            The name to show
        format : callable 
            A function that will get the value to format as the first argument
            and a format string (as defined in 
            https://docs.python.org/library/string.html#formatspec, with just
            the arguments after the colon) as the second argument, note that
            this can be empty too
        parse : callable
            A function that will get the value (can be any type) as the 
            parameter and has to return the parsed value in the datatype this
            object is representing
        """

        self.name = name
        self._format = format
        self._parse = parse
    
    def parse(self, value: typing.Any) -> typing.Any:
        """Parse the `value`.

        Parameters
        ----------
        value : any
            The value to parse
        
        Returns
        -------
        any
            The parsed value as the current datatype defines
        """

        if callable(self._parse):
            return self._parse(value)
        else:
            return value
    
    def format(self, value: typing.Any, format: typing.Optional[str]="") -> str:
        """Format the `value`.

        Parameters
        ----------
        value : any
            The value as the current datatype
        format : str
            The string format without curly brackets as defined in 
            https://docs.python.org/library/string.html#formatspec
        
        Returns
        -------
        str
            The string representation of the `value` in the current datatype
        """
        return self._format(value, format)
    
    def __call__(self, *args: typing.Any) -> typing.Any:
        """Parse the `value` to this datatype.

        Parameters
        ----------
        value : any
            The value to parse
        
        Returns
        -------
        any
            The parsed value as the current datatype defines
        """

        return self.parse(args[0])
    
    @staticmethod
    def split_format_spec(format_spec: str) -> typing.Tuple[str, str, str, str, str, typing.Union[str, int], str, typing.Union[str, int], str]:
        """Split the format specification as it is defined in 
        https://docs.python.org/library/string.html#formatspec.

        Parameters
        ----------
        format_spec : str
            The format specification
        
        Returns
        -------
        tupl or None
            A tuple that represents the specification or None if the
            secification is invalid, the tuple has the following indices:
            - 0: fill character or an empty string
            - 1: alignment character or an empty string
            - 2: sign character or an empty string
            - 3: "#" for alternative representation, empty string for normal
            - 4: "0" for zeros between sign and number, empty string otherwise
            - 5: width as an int or an empty string
            - 6: thousands grouping option ("_" or ",") or empty string for no 
                grouping
            - 7: precision as an int or an empty string
            - 8: type specifier
        """

        matches = format_reg.match(format_spec)

        if matches is not None:
            pattern = []
            for i, v in enumerate(matches.groups()):
                if (i == 5 or i == 7) and v != "":
                    if v.startswith("."):
                        v = v[1:]
                    v = int(v)
                
                pattern.append(v)
            pattern = tuple(pattern)
        else:
            pattern = None
        
        return pattern
    
    @staticmethod
    def join_format_spec(format_tuple: typing.Tuple[str, str, str, str, str, typing.Union[str, int], str, typing.Union[str, int], str], keyname: typing.Optional[str]="") -> str:
        """Join the `format_tuple` of the form as returned by 
        `Datatype::split_format_tuple()` to a valid format string.

        This returns the format string including the curly brackets and the 
        colon. For using a key you can set the `keyname`.

        The `format_tuple` must have the following form. At index:
        - 0: fill character or an empty string
        - 1: alignment character or an empty string
        - 2: sign character or an empty string
        - 3: "#" for alternative representation, empty string for normal
        - 4: "0" for zeros between sign and number, empty string otherwise
        - 5: width as an int or an empty string
        - 6: thousands grouping option ("_" or ",") or empty string for no 
            grouping
        - 7: precision as an int or an empty string
        - 8: type specifier

        Parameters
        ----------
        format_tuple : tuple
            The format tuple of the form as the `Datatype::split_format_tuple()`
            returns
        keyname : str, optional
            The name of the key for the format string, this goes before the 
            colon (`{keyname:format_tuple}`)
        
        Returns
        -------
        str
            A valid format string
        """

        format_tuple = list(format_tuple)

        if format_tuple[8] in ("b", "c", "d", "o", "x", "X", "n"):
            # precision is not allowed for integer types
            format_tuple[7] = ""
        elif format_tuple[7] != "":
            format_tuple[7] = "." + str(format_tuple[7])
        
        return "{" + str(keyname) + ":" + "".join(map(str, format_tuple)) + "}"