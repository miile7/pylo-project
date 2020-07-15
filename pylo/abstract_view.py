import typing

if hasattr(typing, "TypedDict"):
    class AskInput(typing.TypedDict, total=False):
        datatype: type
        description: str
        options: typing.Union[None, typing.Collection]
        allow_custom: bool
else:
    AskInput = typing.Dict

class AbstractView:
    """This class defines the methods for the view.
    
    Attributes
    ----------
    progress_max : int
        The maximum number the progress can have
    progress : int
        The current progress
    """

    def __init__(self):
        """Get the view object."""
        self.progress_max = 100
        self.progress = 0

    @property
    def progress(self):
        """The current progress."""
        return self.__progress

    @progress.setter
    def progress(self, progress : int) -> None:
        """Progress setter."""

        if progress < 0:
            self.__progress = 0
        elif progress > self.progress_max:
            self.__progress = self.progress_max
        else:
            self.__progress = progress

    def showCreateMeasurement(self, controller: "Controller") -> typing.Tuple[dict, dict]:
        """Show the dialog for creating a measurement.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters:
        -----------
        controller : Controller
            The current controller for the microsocpe and the allowed 
            measurement variables

        Returns
        -------
        dict, dict
            A dict that defines the start conditions of the measurement where 
            each`MeasurementVariable`s ids as a key and the value is the start 
            value
            Another dict that contains the series with a 'variable', 'start', 
            'end' and 'step-width' key and an optional 'on-each-point' key that 
            may contain another series
        """
        raise NotImplementedError()

    def showSettings(self, configuration: "AbstractConfiguration", 
                     keys: dict=None,
                     set_in_config: typing.Optional[bool]=True) -> dict:
        """Show the settings to the user.
        
        The `keys` can be a dict that contains dicts at each index. The index 
        of the outer dict is treated as the group, the index of the inner group
        is the key. The value will be set as the current value to the inputs.
        
        When the dialog is confirmed the settings_changed event is fired and 
        the new settings are returned. If `set_in_config` is True the settings 
        will also be applied to the configuration.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        keys : collection of tuples, optional
            A list of tuples where index 0 contains the group and index 1
            contains the key name of the settings to show. The definitions are 
            loaded from the configuration, if not given all keys are shown
        set_in_config : bool, optional
            Whether to apply the settings to the configuration if confirmed,
            default: True
        
        Returns
        -------
        dict of dict
            A dict that contains the groups as keys, as the value there is 
            another dict for the keys in that group, the value is the newly set
            value
        """
        raise NotImplementedError()

    def showHint(self, hint : str) -> None:
        """Show the user a hint.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        hint : str
            The text to show
        """
        raise NotImplementedError()

    def showError(self, error : str, how_to_fix: typing.Optional[str]=None) -> None:
        """Show the user a hint.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        hint : str
            The text to show
        how_to_fix : str, optional
            A text that helps the user to interpret and avoid this error,
            default: None
        """
        raise NotImplementedError()

    def print(self, *values: object, sep: typing.Optional[str]=" ", end: typing.Optional[str]="\n") -> None:
        """Print a line to the user.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        values : str or object
            The value to print
        sep : str
            The separator between two values, default: " "
        end : str
            The end character to end a line, default: "\n"
        """
        raise NotImplementedError()
    
    def showRunning(self) -> None:
        """Show the progress bar and the outputs of the `AbstractView::print()`
        function.
        """
        raise NotImplementedError()

    def askFor(self, *inputs: AskInput) -> tuple:
        """Ask for the specific input when the program needs to know something 
        from the user. 
        
        The following indices are supported for the `inputs`:
        - 'name' : str, required - The name of the input to show
        - 'datatype' : type - The datatype to allow
        - 'description' : str - A description what this value is about
        - 'options' : list or tuple - A list of options to show to the user to 
          select from
        - 'allow_custom' : bool - Whether the user may only use the 'options' 
          (True) or is is allowed to type in custom values too (False), this 
          value is ignored if there are no 'options' given, default: False
        
        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        inputs : dict
            A dict with the 'name' key that defines the name to show. Optional
            additional keys are 'datatype', 'description', 'options' and 
            'allow_custom'
        
        Returns
        -------
        tuple
            A tuple of values where the value on index 0 is the value for the 
            `inputs[0]` and so on
        """
        raise NotImplementedError()

    def _formatAskForInput(self, input_dict : AskInput) -> dict:
        """Format and check the `input_dict` used in `AbstractView::askFor()`.

        Raises
        ------
        KeyError
            When the "name" key is missing
        TypeError
            When the type of the key is wrong
        
        Parameters
        ----------
        input_dict : dict
            A dict with the 'name' key that defines the name to show. Optional
            additional keys are 'datatype', 'description', 'options' and 
            'allow_custom'
        
        Returns
        -------
        dict
            The same dict with valid keys only, if the value was None or empty
            the key is removed
        """

        if not "name" in input_dict:
            raise KeyError("There is no '{}' index given.".format("name"))

        for key, datatype in {"name": str, "datatype": type, "description": str,
                              "options": (list, tuple), "allow_custom": bool}.items():
            if key in input_dict:
                if input_dict[key] is None:
                    del input_dict[key]
                elif not isinstance(input_dict[key], datatype):
                    raise TypeError(("The value for index '{}' has to be a {} " + 
                                    "but {} is given").format(key, datatype, 
                                    type(input_dict[key])))
        
        if "description" in input_dict and input_dict["description"] == "":
            del input_dict["description"]

        if "options" not in input_dict:
            input_dict["allow_custom"] = True
        elif "allow_custom" not in input_dict:
            input_dict["allow_custom"] = not ("options" in input_dict)
        
        return input_dict