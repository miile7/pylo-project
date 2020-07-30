import typing

from .datatype import Datatype

if hasattr(typing, "TypedDict"):
    AskInput = typing.TypedDict("AskInput", {
                                "datatype": type,
                                "description": str,
                                "options": typing.Union[None, typing.Sequence],
                                "allow_custom": bool
                                }, total=False)
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
        self.show_running = False
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
        
        if self.show_running:
            self._updateRunning()

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
            value (value has to be the uncalibrated value)
            Another dict that contains the series with a 'variable', 'start', 
            'end' and 'step-width' key and an optional 'on-each-point' key that 
            may contain another series (value has to be the uncalibrated value)
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
        keys : Sequence of tuples, optional
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

    def showError(self, error : typing.Union[str, Exception], how_to_fix: typing.Optional[str]=None) -> None:
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
        self.show_running = True
    
    def hideRunning(self) -> None:
        """Hides the progress bar shown by `AbstractView::showRunning()`."""
        self.show_running = False

    def _updateRunning(self) -> None:
        """Update the running indicator, the progress has updated."""
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
    
    def parseStart(self, controller: "Controller", 
                   start: typing.Union[dict, None], 
                   add_defaults: typing.Optional[bool]=True) -> typing.Tuple[typing.Union[dict, None], list]:
        """Parse the `start`.

        Convert all the values for the start setup to uncalibrated values. If 
        `add_defaults` is True, default values will be added for each missing
        key. If `add_defaults` is False, None is returned if an error occurres.

        Parameters
        ----------
        controller : Controller
            The controller
        series : dict
            The series dict with the "variable", "start", "step-width", "end" 
            and optionally the "on-each-point" keys
        add_defaults : bool, optional
            Whether to try adding default values until the series is valid 
            (True) or to return None when the series is invalid (False)
        
        Returns
        -------
        dict or None, list
            The valid start or None if `add_defaults` is False and an error 
            occurred and the list of errors
        """

        errors = []
        for v in controller.microscope.supported_measurement_variables:
            if not isinstance(start, dict):
                if not add_defaults:
                    return None, errors
                else:
                    start = {}
            if not v.unique_id in start:
                if not add_defaults:
                    return None, errors
                else:
                    start[v.unique_id] = min(max(0, v.min_value), v.max_value)
            elif start[v.unique_id] > v.max_value:
                errors.append(("The start value '{}' for '{}' is gerater " + 
                               "than the maximum value {}.").format(
                                   v.unique_id, start[v.unique_id], v.max_value
                               ))
                start[v.unique_id] = v.max_value
            elif start[v.unique_id] < v.min_value:
                errors.append(("The start value '{}' for '{}' is less " + 
                               "than the minimum value {}.").format(
                                   v.unique_id, start[v.unique_id], v.min_value
                               ))
                start[v.unique_id] = v.min_value
        
        return start, errors
    
    def parseSeries(self, controller: "Controller", 
                    series: typing.Union[dict, None], 
                    add_defaults: typing.Optional[bool]=True, 
                    path: typing.Optional[list]=[]) -> typing.Tuple[typing.Union[dict, None], typing.List[str]]:
        """Recursively parse the `series`.

        Convert all the values for the series and the child series to 
        uncalibrated values. If `add_defaults` is True and there is a 
        "variable" index, the defaults will be added, `add_defaults` is False
        and a key is missing, the whole series will be deleted.

        Parameters
        ----------
        controller : Controller
            The controller
        series : dict
            The series dict with the "variable", "start", "step-width", "end" 
            and optionally the "on-each-point" keys
        add_defaults : bool, optional
            Whether to try adding default values until the series is valid 
            (True) or to return None when the series is invalid (False)
        path : list, optional
            The parent 'variable' ids if the `series` is the series in the 
            'on-each-point' index of the parent
        
        Returns
        -------
        dict or None, list
            The `series` filled with all values and the values as uncalibrated 
            values or None if `add_defaults` is False and the series could not 
            be parsed or if there is a not solvable error
            The list of error messages
        """

        if isinstance(path, (list, tuple)):
            path_str = "".join([" in 'on-each-step' of {}".format(p) 
                                for p in path])
        else:
            path = []
            path_str = ""
        
        errors = []

        if not isinstance(series, dict):
            series = {}
        
        if not "variable" in series or series["variable"] in path:
            ids = [v.unique_id for v in 
                   controller.microscope.supported_measurement_variables]
            ids = list(filter(lambda i: i not in path, ids))

            if len(ids) == 0:
                errors.append(("There is no variable left to make a series " + 
                               "on each point."))
                return None, errors
            elif "variable" in series and series["variable"] in path:
                errors.append(("The series{} over '{}' is invalid, one of " + 
                               "the parent series is a series over '{}' " + 
                               "already. Use {}.").format(
                                path_str, series["variable"], 
                                series["variable"], 
                                human_concat_list(ids)
                            ))
                if not add_defaults:
                    return None, errors
            else:
                series["variable"] = ids[0]
        
        var = controller.microscope.getMeasurementVariableById(
            series["variable"]
        )

        keys = {
            "start": var.min_value,
            "end": var.max_value,
            "step-width": (var.max_value - var.min_value) / 10
        }

        for k, d in keys.items():
            if not k in series or not isinstance(series[k], (int, float)):
                if not add_defaults:
                    return None
                
                series[k] = d
                # errors.append(("The series{} '{}' key is not " + 
                #                "defined.").format(path_str, k))
            elif (k == "start" or k == "end") and series[k] < var.min_value:
                series[k] = var.min_value
                errors.append(("The series{} '{}' key is less than the " + 
                               "minimum value of {}.").format(
                                   path_str, k, var.min_value
                             ))
            elif (k == "start" or k == "end") and series[k] > var.max_value:
                series[k] = var.max_value
                errors.append(("The series{} '{}' key is greater than the " + 
                               "maximum value of {}.").format(
                                   path_str, k, var.max_value
                             ))

        if "on-each-point" in series:
            if not isinstance(series["on-each-point"], dict):
                errors.append(("The '{}' of the series{} has the wrong " + 
                               "type. It has to be of type 'dict' but it " + 
                               "is '{}'.").format("on-each-point", path_str,
                               type(series["on-each-point"])))
                series["on-each-point"] = None
            elif "variable" not in series["on-each-point"]:
                errors.append(("The '{}' of the 'on-each-point' series in " + 
                               "the series{} is missing.").format("variable", 
                               path_str
                             ))
                series["on-each-point"] = None
            elif (series["on-each-point"]["variable"] in 
                  path + [series["variable"]]):
                errors.append(("The variable '{}' of the 'on-each-point' " + 
                               "series in the series{} is used on another " + 
                               "series already.").format(
                                   series["on-each-point"]["variable"], 
                                    path_str
                             ))
                series["on-each-point"] = None
            else:
                # note that this can return None too, if add_defaults=False and
                # the series["on-each-point"] is invalid
                on_each_point_series, on_each_point_errors = self.parseSeries(
                    controller, series["on-each-point"], add_defaults, 
                    path + [series["variable"]]
                )
                series["on-each-point"] = on_each_point_series
                errors += on_each_point_errors
            
            if series["on-each-point"] is None:
                del series["on-each-point"]

        # convert to uncalibrated values
        series["start"] = var.ensureUncalibratedValue(series["start"])
        series["step-width"] = var.ensureUncalibratedValue(series["step-width"])
        series["end"] = var.ensureUncalibratedValue(series["end"])
        
        return series, errors