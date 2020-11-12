import typing

from .pylolib import human_concat_list
from .datatype import Datatype

if hasattr(typing, "TypedDict"):
    AskInput = typing.TypedDict("AskInput", {
                                "datatype": typing.Union[type, Datatype],
                                "description": str
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
            each `MeasurementVariable`s ids as a key and the value is the start 
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

    def clear(self) -> None:
        """Clear the current text output."""
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
        - 'datatype' : type or Datatype - The datatype to allow
        - 'description' : str - A description what this value is about
        
        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        
        Parameters
        ----------
        inputs : dict
            A dict with the 'name' key that defines the name to show. Optional
            additional keys are 'datatype', and 'description'
        
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
            additional keys are 'datatype', and 'description'
        
        Returns
        -------
        dict
            The same dict with valid keys only, if the value was None or empty
            the key is removed
        """

        if not "name" in input_dict:
            raise KeyError("There is no '{}' index given.".format("name"))

        for key, datatype in {"name": str, "datatype": (type, Datatype), 
                              "description": str}.items():
            if key in input_dict:
                if input_dict[key] is None:
                    del input_dict[key]
                elif not isinstance(input_dict[key], datatype):
                    raise TypeError(("The value for index '{}' has to be a {} " + 
                                    "but {} is given").format(key, datatype, 
                                    type(input_dict[key])))
        
        if "description" in input_dict and input_dict["description"] == "":
            del input_dict["description"]
        
        return input_dict
    
    def parseStart(self, measurement_variables: typing.Union[list, dict], 
                   start: typing.Union[dict, None], 
                   add_defaults: typing.Optional[bool]=True,
                   parse: typing.Optional[bool]=False,
                   uncalibrate: typing.Optional[bool]=False) -> typing.Tuple[typing.Union[dict, None], list]:
        """Parse the `start`.

        Convert all the values for the start setup to uncalibrated values. If 
        `add_defaults` is True, default values will be added for each missing
        key. If `add_defaults` is False, None is returned if an error occurres.

        Parameters
        ----------
        measurement_variables : list or dict
            All the supported measurement variables, either as a list or as a
            dict where the key is the unique_id and the value is the 
            `MeasurementVariable` object
        series : dict
            The series dict with the "variable", "start", "step-width", "end" 
            and optionally the "on-each-point" keys
        add_defaults : bool, optional
            Whether to try adding default values until the series is valid 
            (True) or to return None when the series is invalid (False)
        parse : bool, optional
            Whether to parse the input (if there is a datatype given for the 
            measurement variable), default: False
        uncalibrate : bool, optional
            Whether to assume that the values are given as calibrated values 
            and to enforce them to be uncalibrated (if there is a calibration
            given for the measurment variable), default: False
        
        Returns
        -------
        dict or None, list
            The valid start or None if `add_defaults` is False and an error 
            occurred and the list of errors
        """

        # for keeping the same parameter datatypes, dict is not necessary here
        if not isinstance(measurement_variables, dict):
            m_vars = {}
            for var in measurement_variables:
                m_vars[var.unique_id] = var
            measurement_variables = m_vars

        errors = []
        for v in measurement_variables.values():
            if not isinstance(start, dict):
                if not add_defaults:
                    return None, errors
                else:
                    start = {}
            
            if (v.unique_id in start and parse and v.format != None and 
                isinstance(v.format, (type, Datatype))):
                start[v.unique_id] = v.format(start[v.unique_id])

            if (not v.unique_id in start or 
                not isinstance(start[v.unique_id], (int, float))):
                if not add_defaults:
                    return None, errors
                else:
                    start[v.unique_id] = min(max(0, v.min_value), v.max_value)
            else:
                if uncalibrate:
                    start[v.unique_id] = v.ensureUncalibratedValue(
                        start[v.unique_id]
                    )
                
                if start[v.unique_id] > v.max_value:
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
    
    def parseSeries(self, measurement_variables: typing.Union[list, dict], 
                    series: typing.Union[dict, None], 
                    add_defaults: typing.Optional[bool]=True, 
                    parse: typing.Optional[bool]=False,
                    uncalibrate: typing.Optional[bool]=False,
                    path: typing.Optional[list]=[]) -> typing.Tuple[typing.Union[dict, None], typing.List[str]]:
        """Recursively parse the `series`.

        Convert all the values for the series and the child series to 
        uncalibrated values. If `add_defaults` is True and there is a 
        "variable" index, the defaults will be added, `add_defaults` is False
        and a key is missing, the whole series will be deleted.

        Parameters
        ----------
        measurement_variables : list or dict
            All the supported measurement variables, either as a list or as a
            dict where the key is the unique_id and the value is the 
            `MeasurementVariable` object
        series : dict
            The series dict with the "variable", "start", "step-width", "end" 
            and optionally the "on-each-point" keys
        add_defaults : bool, optional
            Whether to try adding default values until the series is valid 
            (True) or to return None when the series is invalid (False)
        parse : bool, optional
            Whether to parse the input (if there is a datatype given for the 
            measurement variable), default: False
        uncalibrate : bool, optional
            Whether to assume that the values are given as calibrated values 
            and to enforce them to be uncalibrated (if there is a calibration
            given for the measurment variable), default: False
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

        if not isinstance(measurement_variables, dict):
            m_vars = {}
            for var in measurement_variables:
                m_vars[var.unique_id] = var
            measurement_variables = m_vars

        if isinstance(path, (list, tuple)):
            path_str = "".join([" in 'on-each-point' of {}".format(p) 
                                for p in path])
        else:
            path = []
            path_str = ""
        
        errors = []

        if not isinstance(series, dict):
            series = {}
        
        if not "variable" in series or series["variable"] in path:
            ids = list(measurement_variables.keys())
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
        
        try:
            var = measurement_variables[series["variable"]]
        except KeyError as e:
            msg = ("The measurement variable '{}' does not " + 
                   "exist.").format(series["variable"])
            raise KeyError(msg) from e

        keys = {
            "start": var.min_value,
            "end": var.max_value,
            "step-width": (var.max_value - var.min_value) / 10
        }

        for k, d in keys.items():
            if (k in series and parse and var.format != None and 
                isinstance(var.format, (type, Datatype))):
                series[k] = var.format(series[k])
            
            if not k in series or not isinstance(series[k], (int, float)):
                if not add_defaults:
                    return None, errors
                
                series[k] = d
                # errors.append(("The series{} '{}' key is not " + 
                #                "defined.").format(path_str, k))
            else:
                if uncalibrate:
                    series[k] = var.ensureUncalibratedValue(series[k])
                
                if (k == "start" or k == "end") and series[k] < var.min_value:
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
                    measurement_variables, series["on-each-point"], add_defaults, 
                    parse, uncalibrate, path + [series["variable"]]
                )
                series["on-each-point"] = on_each_point_series
                errors += on_each_point_errors
            
            if series["on-each-point"] is None:
                del series["on-each-point"]
        
        return series, errors