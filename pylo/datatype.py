import re
import math
import typing

# the regular expression that matches any valid format specification, each 
# group contains one specification item
format_reg = re.compile(r"^((?:.(?=(?:<|>|\^)))?)([<>=^]?)([\-+ ]?)(#?)(0?)([\d]*)([_,]?)((?:\.[\d]+)?)([bcdeEfFgGnosxX%]?)$")

class Datatype:
    def __init__(self, name: str, 
                 format: typing.Callable[[typing.Union[int, float, str], str], typing.Union[int, float, str]], 
                 parse: typing.Optional[typing.Callable[[typing.Union[int, float, str]], typing.Union[int, float, str]]]=None) -> None:
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

class OptionDatatype(Datatype):
    """A datatype that allows the selection of a variant of values.

    Attributes
    ----------
    options : sequence
        The options that are allowed
    exact_comparism : bool, optional
        Whether to do exact comparisms or not, for strings exact is case 
        sensitive, for floats exact is all digits, default: False
    ignore_chars : list of strings
        The list of strings to replace before comparing (and before converting 
        to lower case) if `OptionDatatype.exact_comparism` is False and the 
        option is a string, this can be for example white space to compare with 
        ignore whitespace, default: []
    rel_tol : float
        The relative tolerance to use  if `OptionDatatype.exact_comparism` is
        False and the option is a float, default: 0
    abs_tol : float
        The absolute tolerance to use  if `OptionDatatype.exact_comparism` is
        False and the option is a float, default: 1e-6
    """

    def __init__(self, options: typing.Sequence, 
                 exact_comparism: typing.Optional[bool]=False) -> None:
        """Create a new option datatype.

        The `exact_comparism` tells, whether to compare exactly or not. What 
        this means depends on the type of the options.
        - `options` are strings: Exact is case sensitive, inexact is case 
          insensitive, `datatype.ignore_chars` can be a list of characters that 
          will be removed in both, the value and the option to compare before 
          comparism
        - `options` are floats: Exact is all digits, inexact uses 
          `math.isclose()`, `datatype.rel_tol` and `datatype.abs_tol` are given
          directly to the function if they are ints

        Parameters
        ----------
        options : sequence
            The options
        exact_comparism : bool, optional
            Whether to do exact comparisms or not, for strings exact is case 
            sensitive, for floats exact is all digits, default: False
        """

        self.ignore_chars = []
        self.rel_tol = 0
        self.abs_tol = 1e-6

        self.options = list(options)
        self.exact_comparism = exact_comparism

        super().__init__("optionslist", self.format_options, self.parse_options)

    def format_options(self, v: typing.Any, f: typing.Optional[str]="") -> str:
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

        return self.parse_options(v)

    def parse_options(self, v: typing.Any):
        """Parse the given value.

        Raises
        ------
        ValueError
            When the value `v` is not an allowed option.

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

        for o in self.options:
            if (not self.exact_comparism and isinstance(v, (int, float)) and 
                isinstance(o, (int, float))):
                c = math.isclose(v, o, abs_tol=self.abs_tol, rel_tol=self.rel_tol)
            elif (not self.exact_comparism and isinstance(v, str) and 
                  isinstance(o, str)):
                vm = v
                om = o
                for r in self.ignore_chars:
                    vm = vm.replace(r, "")
                    om = om.replace(r, "")

                c = vm.lower() == om.lower()
            else:
                c = o == v
            
            if c:
                return o
        
        raise ValueError("The value '{}' is not in the options.".format(v))
                