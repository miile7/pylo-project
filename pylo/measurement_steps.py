import copy
import math
import typing
import logging
import functools
import collections
import collections.abc

from .datatype import Datatype
from .pylolib import parse_value
from .logginglib import log_debug
from .logginglib import log_error
from .logginglib import get_logger
from .pylolib import get_datatype_human_text

class MeasurementSteps(collections.abc.Sequence):
    """A sequence containing all measurement steps.

    Attributes
    ----------
    series : dict
        The formatted series dict that is used to create the measurement steps
    start : dict
        The formatted start dict
    series_variables : set
        The variable ids of the variables that are modified at least one time
        when performing all the steps
    """

    def __init__(self, controller: "Controller", start: dict, series: dict):
        """Create the steps for the measurement by the given `start` conditions
        and the `series`.

        Notes
        -----
        The `start` value for the `MeasurementVariable` that the 
        series is done of will be ignored because the `series` defines the 
        start conditions. 

        In other words: The value of the `start[series["variable"]]` is ignored 
        because `series["start"]` defines the start condition for the 
        `series["variable"]`.

        Raises
        ------
        KeyError
            When the `start` does not contain all supported 
            `MeasurementVariables` or when the `series` is missing the 
            'variable', 'start', 'end' or 'step-width' indices
        ValueError
            When the `start` or the `series` 'step' or 'end' contains invalid 
            values (e.g. values are out of the bounds the `MeasurementVariable` 
            defines) or the `series` 'step-width' index is smaller or equal to 
            zero or the 'on-each-point' contains a variable that is measured 
            already
        TypeError
            When one of the values has the wrong type

        Parameters
        ----------
        controller : Controller
            The controller for the measurement and the microscope
        start : dict of int or floats
            The start conditions, the `MeasurementVariable` id has to be the 
            key, the value to start with (in the `MeasurementVariable` specific 
            units) has to be the value, note that every `MeasurementVariable` 
            has to be included
        series : dict with str, and three or four times int or float
            A dict with the 'variable', 'start', 'step-width', 'end' and the 
            optional 'on-each-point' indices. The series iterate the 
            `MeasurementVaraible` at the 'variable' index starting with 'start'
            and ending at 'end' (including start and end) while travelling with 
            the 'step-width'. The 'on-each-point' can hold another series dict
            that defines another series that will be iterated over on each step
            the current series does.
        
        Returns
        -------
        list of dicts
            Returns the steps which is a list of dicts where each dict contains
            every `MeasurementVariable` id as the key its corresponding value.
            The full list represents the measurement defined by the 
            `start_condition` and the `series`.
        """

        self._logger = get_logger(self, instance_args=(series, start))
        
        self.series_variables = []
        self.controller = controller

        self.series = MeasurementSteps.formatSeries(
            controller.microscope.supported_measurement_variables, 
            series, self.series_variables, add_default_values=False,
            logger=self._logger, start=start)
        self.series_variables = set(self.series_variables)

        self.start = MeasurementSteps.formatStart(
            controller.microscope.supported_measurement_variables, start, 
            self.series, add_default_values=False, logger=self._logger)

        self._cached_len = None
        self._cached_nests = None
    
    @staticmethod
    def formatSeries(measurement_variables: typing.Iterable["MeasurementVariable"], 
                     series: dict, series_path: typing.Optional[list]=None,
                     add_default_values: typing.Optional[bool]=False,
                     parse: typing.Optional[bool]=False,
                     uncalibrate: typing.Optional[bool]=False,
                     start: typing.Optional[dict]=None,
                     default_values: typing.Optional[dict]=None,
                     logger: typing.Optional[logging.Logger]=None, *args,
                     parse_measurement_variable_default: typing.Optional[bool]=False) -> dict:
        """Format the given `series` to contain valid values only.

        If an invalid value is found and `add_default_values` is True, the 
        error will be added to the returned error list and the value will be 
        replaced with a default value.

        If an invalid value is found and `add_default_values` is False, an 
        Error is raised.

        The default series creation is rather complicated. At first the 
        `default_values` are added if they are given and valid. Valid means 
        that the type and the value is correct, also concerning the present 
        `series` values. E.g. the default value `end=10` is valid if no 
        `series` is given, but not if the series contains `{"start": 20}`.
        
        If the value is not found in the `default_values`, the default values 
        of the `MeasurementVariable` are used, again if they are given and 
        valid in the context. If not, the value is calculated. If two values
        are given, the third one is calculated to perform 5 steps.

        This process is performed for each, the "step-width", the "start" and 
        the "end" value in this order. This means, that the context changes by
        the proceeding. 
        
        The "step-width" calculation is skipped if not at least two values are 
        given and no defaults can be found. In this case the "start" and "end"
        defaults are retrieved. Then the "step-width" is calculated in the end.

        Raises
        ------
        KeyError
            When the `series` is missing the one of the 'variable', 'start', 
            'end' or 'step-width' indices and `add_default_values` is False
        ValueError
            When the `series` 'start', 'step-width' or 'end' index contains 
            invalid values (e.g. values are out of the bounds the 
            `MeasurementVariable` defines or the 'step-width' is smaller or 
            equal to zero) or the 'on-each-point' contains a variable that is 
            measured already (preventing recursive series) and 
            `add_default_values` is False
        TypeError
            When one of the values has the wrong type and `add_default_values` 
            is False

        Parameters
        ----------
        measurement_variables : iterable of MeasurementVariables
            The measurement variables
        series : dict with str, and three or four times int or float
            A dict with the 'variable', 'start', 'step-width', 'end' and the 
            optional 'on-each-point' indices. The series iterate the 
            `MeasurementVaraible` at the 'variable' index starting with 'start'
            and ending at 'end' (including start and end) while travelling with 
            the 'step-width'. The 'on-each-point' can hold another series dict
            that defines another series that will be iterated over on each step
            the current series does.
        series_path : list, optional
            A list to which the variable names of the parent series are added 
            if the current parse series is in the 'on-each-point' index of 
            another series, if something else than a list is given, the value 
            is ignored, only use this as a reference parameter, and only use 
            empty lists, default: None
        add_default_values : bool, optional
            Whether to try adding default values until the series is valid 
            (True) and return the errors to the list at index 1 or to raise 
            the errors (False)
        parse : bool, optional
            Whether to parse the input (if there is a datatype given for the 
            measurement variable), default: False
        uncalibrate : bool, optional
            Whether to assume that the values are given as calibrated values 
            and to enforce them to be uncalibrated (if there is a calibration
            given for the measurment variable), default: False
        start : dict, optional
            The start dict to use the values of if the start value of the 
            series is not given or invalid, default: None
        default_values : dict, optional
            The default values to use, the key must be the variable id, the 
            values is another dict with the "start", "step-width" and "end" 
            values containing the default values, if not given the 
            measurement variables definitions are used, note that the defaults
            must be valid, they are **not** checked, default: None
        raise_errors : bool, optional
            Whether to raise the errors and stop the execution on an error or 
            to continue and return all errors, default: False
        logger : logging.Logger, optional
            The logger object to log to, if not given no logs are made
        parse_measurement_variable_default : bool, optional
            Whether to parse the default values if the series variables defines
            default values, default: False
        
        Returns
        -------
        (dict, list) or dict
            A tuple with the valid `series` at index 0 and the error list at 
            index 1 if `add_default_values` is True, otherwise the valid 
            `series` dict at index 0
        """
        
        # ultimate fallback values if there is nothing given at all
        default_steps = 5
        default_min = 0
        default_max = 10
        default_step_width = 1

        log_debug(logger, "Formatting series '{}'".format(series))
        errors = []

        if isinstance(series_path, list) and len(series_path) > 0:
            error_str = "".join([" in 'on-each-point' of {}".format(p) 
                                  for p in series_path])
        else:
            if not isinstance(series_path, list):
                series_path = []
            error_str = ""
        
        if not isinstance(series, dict):
            try:
                series = dict(series)
            except TypeError:
                err = ValueError(("The series{} '{}' is not a dict").format(
                        error_str, series))
                
                if add_default_values:
                    errors.append(err)
                    series = {}
                else:
                    log_error(logger, err)
                    raise err

        series_variable = None
        if "variable" in series:
            for var in measurement_variables:
                if var.unique_id == series["variable"]:
                    series_variable = var
                    break

        if series_variable is None:
            if "variable" not in series:
                err = KeyError(("The series{} does not have a 'variable' " +
                                "index").format(error_str))
            else:
                err = ValueError(("The series{} variable '{}' is not a " + 
                                  "measurement variable.").format(error_str,
                                    series["variable"]))

            if add_default_values:
                errors.append(err)
                series_variable = None

                for var in measurement_variables:
                    if var.unique_id not in series_path:
                        series_variable = var
                        series["variable"] = var.unique_id
                        break
            else:
                log_error(logger, err)
                raise err
        
        id_ = series_variable.unique_id

        # prevent recursive series, the series variable must not be in one of 
        # the parent series (if there are parent series)
        if id_ in series_path:
            err = ValueError(("The variable '{}' in the series{} is " + 
                              "already measured in one of the parent " +
                              "series.").format(id_, error_str))

            if add_default_values:
                errors.append(err)
                return None, errors
            else:
                log_error(logger, err)
                raise err

        series_definition = {
            "start": (int, float), 
            "end": (int, float), 
            "step-width": (int, float), 
        }

        def in_bounds(value: typing.Any, series_variable: "MeasurementVariable") -> bool:
            """Whether the `value` is inside of the bounds given by the 
            `series_variable`, if one of the parameters doesn't support 
            comparisms, True is returned

            Parameters
            ----------
            value : any
                The value to test
            series_variable : MeasurementVariable
                The measurement variable
            
            Returns
            -------
            bool
                Whether the `value` is inside the bounds or not testable
            """

            _in_bounds = True

            try:
                _in_bounds = (value >= series_variable.min_value)
            except TypeError:
                pass
            
            if _in_bounds:
                try:
                    _in_bounds = (value <= series_variable.max_value)
                except TypeError:
                    pass
        
            return _in_bounds

        # format the known/given series, if defaults are not added, errors are
        # raised if an error is found
        for key, datatype in series_definition.items():
            if (key not in series and key == "start" and 
                isinstance(start, dict) and id_ in start):
                series[key] = start[id_]
            
            if key not in series:
                err = KeyError(("The series{} does not have a '{}' " + 
                                "index.").format(error_str, key))
                
                if add_default_values:
                    errors.append(err)
                else:
                    log_error(logger, err)
                    raise err
            else:
                if parse:
                    series[key] = parse_value(series_variable, series[key])

                if uncalibrate:
                    series[key] = series_variable.ensureUncalibratedValue(series[key], key)
                
                if not isinstance(series[key], datatype):
                    err = TypeError(("The series{} '{}' key has to be of type {} " + 
                                    "but it is {}.").format(
                                        error_str,
                                        key, 
                                        get_datatype_human_text(datatype),
                                        type(series[key])))

                    if add_default_values:
                        errors.append(err)
                        del series[key]
                    else:
                        log_error(logger, err)
                        raise err
                elif key in ("start", "end"):
                    if not in_bounds(series[key], series_variable):
                        err = ValueError(("The '{key}' key in the series{path} " + 
                                        "is out of bounds. The {key} has to be " + 
                                        "{min} <= {key} <= {max} but it is " + 
                                        "{val}.").format(
                                            path=error_str,
                                            key=key, 
                                            min=series_variable.min_value,
                                            max=series_variable.max_value,
                                            val=series[key]
                                        ))
                        
                        if add_default_values:
                            errors.append(err)
                            del series[key]
                        else:
                            log_error(logger, err)
                            raise err
                elif key == "step-width":
                    if math.isclose(series[key], 0):
                        err = ValueError(("The 'step-width' in the series{} " + 
                                          "must not be 0.").format(error_str))

                        if add_default_values:
                            errors.append(err)
                            del series[key]
                        else:
                            log_error(logger, err)
                            raise err
        
        if not isinstance(default_values, dict):
            default_values = {}
        
        if (not id_ in default_values or 
            not isinstance(default_values[id_], dict)):
            default_values[id_] = {}
        
        if "step-width" not in series:
            log_debug(logger, "Trying to find a default value for the step " + 
                              "width")

            # set step-width default values
            defaults = collections.OrderedDict()
            # try to use parameter
            if "step-width" in default_values[id_]:
                defaults["default_values"] = default_values[id_]["step-width"]
            
            # try to use series variable default value
            if series_variable.default_step_width_value is not None:
                if parse_measurement_variable_default:
                    defaults["measurement variable default value"] = (
                        parse_value(series_variable, 
                                    series_variable.default_step_width_value))
                else:
                    defaults["measurement variable default value"] = (
                        series_variable.default_step_width_value)
            
            # try to use value depending on current series
            if "start" in series and "end" in series:
                defaults["(end-start)/n"] = ((series["end"] - series["start"]) / 
                                           default_steps)
            
            # find first valid default
            if len(defaults) > 0:
                for name, value in defaults.items():
                    if isinstance(value, (int, float)) and not math.isclose(value, 0):
                        series["step-width"] = value
                        log_debug(logger, "Using step width from '{}'".format(name))
                        break
            
            if not "step-width" in series:
                log_debug(logger, "Did not find a default value for the step " +  
                                  "width, this is added in the end")
        
        if "start" not in series:
            # set start default values
            defaults = collections.OrderedDict()
            # try to use parameter
            if "start" in default_values[id_]:
                defaults["default_values"] = default_values[id_]["start"]
            
            # try to use series variable default value
            if series_variable.default_start_value is not None:
                if parse_measurement_variable_default:
                    defaults["measurement variable default value"] = (
                        parse_value(series_variable, 
                                    series_variable.default_start_value))
                else:
                    defaults["measurement variable default value"] = (
                        series_variable.default_start_value)
            
            # try to use value depending on current series
            if "step-width" in series and "end" in series:
                defaults["end-(step*n)"] = (series["end"] - 
                                            series["step-width"] * default_steps)
            
            # try to use the limit value
            if "step-width" in series and series["step-width"] < 0:
                if series_variable.max_value is not None:
                    defaults["series variable max value"] = series_variable.max_value
                else:
                    defaults["fallback max value"] = default_max
            else:
                if series_variable.min_value is not None:
                    defaults["series variable min value"] = series_variable.min_value
                else:
                    defaults["fallback min value"] = default_min
            
            if "end" in series:
                defaults["end-default_step"] = series["end"] - default_step_width
                defaults["end+default_step"] = series["end"] + default_step_width
                defaults["end"] = series["end"]
            
            # find first valid default
            # This does terminate and does find a value. The following cases 
            # are possible.
            #
            # The end value is in the bounds, so it is always valid, otherwise
            # it is removed before this if block
            #
            # min_value: yes, "end":  yes -> "end" is valid and in the defaults
            #                                -> matches boundaries and <= "end" 
            #                                   criteria
            # min_value: no,  "end":  yes -> "end" is valid and in the defaults
            #                                -> boundaries not checkable, 
            #                                   matches <= "end" criteria, 
            # min_value: yes, "end":  no  -> min_value is in the defaults
            #                                -> matches boundaries, <= "end"
            #                                   not checkable
            # min_value: no,  "end":  no  -> default_min is in the defaults
            #                               -> no criterias possible
            if len(defaults) > 0:
                for name, value in defaults.items():
                    if (isinstance(value, (int, float)) and 
                        in_bounds(value, series_variable) and 
                        ("end" not in series or 
                        ((("step-width" not in series or 
                           series["step-width"] >= 0) and value <= series["end"]) or
                        ("step-width" in series and 
                         series["step-width"] < 0 and value >= series["end"])))):
                        series["start"] = value
                        log_debug(logger, "Using start from '{}'".format(name))
                        break
        
        if "end" not in series:
            # set end default values
            defaults = collections.OrderedDict()
            # try to use parameter
            if "end" in default_values[id_]:
                defaults["default_values"] = default_values[id_]["end"]
            
            # try to use series variable default value
            if series_variable.default_end_value is not None:
                if parse_measurement_variable_default:
                    defaults["measurement variable default value"] = (
                        parse_value(series_variable, 
                                    series_variable.default_end_value))
                else:
                    defaults["measurement variable default value"] = (
                        series_variable.default_end_value)
            
            # try to use value depending on current series
            if "step-width" in series and "start" in series:
                defaults["start+(step*n)"] = (series["start"] + 
                                              series["step-width"] * default_steps)
            
            # try to use the limit value
            if "step-width" in series and series["step-width"] < 0:
                if series_variable.min_value is not None:
                    defaults["series variable min value"] = series_variable.min_value
                else:
                    defaults["fallback min value"] = default_min
            else:
                if series_variable.max_value is not None:
                    defaults["series variable max value"] = series_variable.max_value
                else:
                    defaults["fallback max value"] = default_max
            
            if "start" in series:
                defaults["start+default_step"] = series["start"] + default_step_width
                defaults["start-default_step"] = series["start"] - default_step_width
                defaults["start"] = series["start"]
                
            # find first valid default
            # this terminates and finds a value, check out the comment for 
            # the start
            if len(defaults) > 0:
                for name, value in defaults.items():
                    if (isinstance(value, (int, float)) and 
                        in_bounds(value, series_variable) and 
                        ("start" not in series or 
                        ((("step-width" not in series or 
                           series["step-width"] >= 0) and value >= series["start"]) or
                        ("step-width" in series and 
                         series["step-width"] < 0 and value <= series["start"])))):
                        series["end"] = value
                        log_debug(logger, "Using end from '{}'".format(name))
                        break
        
        if "step-width" not in series:
            series["step-width"] = (series["end"] - series["start"]) / default_steps
            log_debug(logger, "Using step width from '{}'".format("(end-start)/n"))
        
        log_debug(logger, "Created series '{}', checking sub series".format(series))

        series_path.append(id_)

        if "on-each-point" in series:
            if isinstance(series["on-each-point"], dict):
                on_each_point = MeasurementSteps.formatSeries(
                    measurement_variables, series["on-each-point"], 
                    series_path=series_path, 
                    add_default_values=add_default_values, parse=parse, 
                    default_values=default_values,
                    uncalibrate=uncalibrate, start=start, logger=logger)
                
                if add_default_values:
                    series["on-each-point"] = on_each_point[0]
                    errors += on_each_point[1]
                else:
                    series["on-each-point"] = on_each_point
            
            if not isinstance(series["on-each-point"], dict):
                del series["on-each-point"]
        
        log_debug(logger, "Done with formatting, series is now '{}'".format(series))

        if add_default_values:
            return series, errors
        else:
            return series
    
    @staticmethod
    def formatStart(measurement_variables: typing.Iterable["MeasurementVariable"], 
                    start: dict, series: dict,
                    add_default_values: typing.Optional[bool]=False,
                    parse: typing.Optional[bool]=False,
                    uncalibrate: typing.Optional[bool]=False,
                    default_values: typing.Optional[dict]=None,
                    logger: typing.Optional[logging.Logger]=None) -> dict:
        """Format the given `start` to contain valid values only.

        If an invalid value is found and `add_default_values` is True, the 
        error will be added to the returned error list and the value will be 
        replaced with a default value.

        If an invalid value is found and `add_default_values` is False, an 
        Error is raised.

        Make sure to pass a valid `series` only. Use the 
        `MeasurementSteps.formatSeries()` for the `series` at first.

        Raises
        ------
        KeyError
            When the `start` does not contain all supported 
            `MeasurementVariables`
        ValueError
            When the `start` values contains invalid values (e.g. values are 
            out of the bounds the `MeasurementVariable` defines)
        TypeError
            When one of the values has the wrong type

        Parameters
        ----------
        measurement_variables : iterable of MeasurementVariables
            The measurement variables
        start : dict of int or floats
            The start conditions, the `MeasurementVariable` id has to be the 
            key, the value to start with (in the `MeasurementVariable` specific 
            units) has to be the value, note that every `MeasurementVariable` 
            has to be included
        series : dict with str, and three or four times int or float
            A dict with the 'variable', 'start', 'step-width', 'end' and the 
            optional 'on-each-point' indices. The series iterate the 
            `MeasurementVaraible` at the 'variable' index starting with 'start'
            and ending at 'end' (including start and end) while travelling with 
            the 'step-width'. The 'on-each-point' can hold another series dict
            that defines another series that will be iterated over on each step
            the current series does
        add_default_values : bool, optional
            Whether to try adding default values until the series is valid 
            (True) and return the errors to the list at index 1 or to raise 
            the errors (False)
        parse : bool, optional
            Whether to parse the input (if there is a datatype given for the 
            measurement variable), default: False
        uncalibrate : bool, optional
            Whether to assume that the values are given as calibrated values 
            and to enforce them to be uncalibrated (if there is a calibration
            given for the measurment variable), default: False
        default_values : dict, optional
            The default values to use, the key must be the variable id, the 
            value is the corresponding default value to use, note that the 
            defaults must be valid, they are **not** checked, if not given the 
            default values of the measurement variables are used, default: None
        logger : logging.Logger, optional
            The logger object to log to, if not given no logs are made
        
        Returns
        -------
        dict
            The valid `start` dict
        """

        errors = []
        log_debug(logger, ("Formatting start '{}' with series '{}'").format(
                            start, series))
        
        if not isinstance(series, dict):
            try:
                series = dict(series)
            except TypeError:
                series = {}
        
        if not isinstance(start, dict):
            try:
                start = dict(start)
            except TypeError:
                err = ValueError(("The start '{}' is not a dict").format(start))
                
                if add_default_values:
                    errors.append(err)
                    start = {}
                else:
                    log_error(logger, err)
                    raise err

        # extract the start values from the series
        series_starts = {}
        s = series
        while s is not None:
            series_starts[s["variable"]] = s["start"]

            if "on-each-point" in s:
                s = s["on-each-point"]
            else:
                s = None
                break
        
        if not isinstance(default_values, dict):
            default_values = {}

        for var in measurement_variables:
            if var.unique_id not in default_values:
                if var.default_start_value is not None:
                    default_values[var.unique_id] = var.default_start_value
                else:
                    default_values[var.unique_id] = 0

        # check and create start variables
        for var in measurement_variables:
            if var.unique_id in series_starts:
                # make sure also the measured variable is correct
                start[var.unique_id] = series_starts[var.unique_id]
            elif var.unique_id not in start:
                err = KeyError(("The measurement variable {} (id: {}) "  + 
                                "is neither contained in the start " + 
                                "conditions nor in the series. All " + 
                                "parameters (measurement variables) " + 
                                "values must be known!").format(
                                    var.name, var.unique_id))
                if add_default_values:
                    start[var.unique_id] = default_values[var.unique_id]
                    errors.append(err)
                else:
                    log_error(logger, err)
                    raise err
            else:
                if parse:
                    if (var.has_calibration and 
                        isinstance(var.calibrated_format, (type, Datatype))):
                        start[var.unique_id] = parse_value(var.calibrated_format, 
                                                           start[var.unique_id])
                    else:
                        start[var.unique_id] = parse_value(var.format, 
                                                           start[var.unique_id])

                if uncalibrate:
                    start[var.unique_id] = var.ensureUncalibratedValue(
                        start[var.unique_id])
                
                if not isinstance(start[var.unique_id], (int, float)):
                    err = TypeError(("The '{}' index in the start conditions " + 
                                    "contains a {} but only int or float are " + 
                                    "supported.").format(
                                        var.unique_id, 
                                        type(start[var.unique_id])))
                    if add_default_values:
                        errors.append(err)
                        start[var.unique_id] = default_values[var.unique_id]
                    else:
                        log_error(logger, err)
                        raise err
                else:
                    in_bounds = True

                    try:
                        in_bounds = (in_bounds and 
                                     start[var.unique_id] >= var.min_value)
                    except TypeError:
                        pass

                    try:
                        in_bounds = (in_bounds and 
                                     start[var.unique_id] <= var.max_value)
                    except TypeError:
                        pass
                        
                    if not in_bounds:
                        err = ValueError(("The '{id}' value in the start " + 
                                        "is out of bounds. The {id} has to be " + 
                                        "{min} <= {id} <= {max} but it is " + 
                                        "{val}.").format(
                                            id=var.unique_id, 
                                            min=var.min_value,
                                            max=var.max_value,
                                            val=start[var.unique_id]
                                        ))
                        if add_default_values:
                            errors.append(err)
                            start[var.unique_id] = default_values[var.unique_id]#
                        else:
                            log_error(logger, err)
                            raise err

        log_debug(logger, "Done with formatting, start is now '{}'".format(start))

        if add_default_values:
            return start, errors
        else:
            return start
    
    def __len__(self) -> int:
        """Get the number of steps.

        Returns
        -------
        int
            The number of steps
        """

        if isinstance(self._cached_len, int):
            return self._cached_len

        # calculate the product of each "on-each-point" series length which is 
        # returned by MeasurementSteps._getNestLengths()
        nests = self._getNestLengths()
        self._cached_len = functools.reduce(lambda x, y: x * y, nests, 1)
        log_debug(self._logger, ("Returning length '{}' calculated with " + 
                                "product of '{}'").format(self._cached_len, 
                                list(nests)))
        return self._cached_len
    
    def _getNestLengths(self) -> typing.Generator[int, None, None]:
        """Get a list containing the lengths of each nested series calculating 
        the length by the 'start', 'step-width' and 'end' indices and 
        **ignoring** the 'on-each-step' nested series.

        The list will start with the most outer length (the most outer series)
        at index 0 and add all the lengths of each "on-each-point" series.

        Returns
        -------
        generator of int
            The length of each series starting with the most outer series
        """
        
        series = self.series
        while series is not None:
            yield MeasurementSteps._getSeriesLength(series)

            if "on-each-point" in series:
                series = series["on-each-point"]
            else:
                series = None
                break
    
    def _getReversedCommulativeNestLengths(self) -> typing.List[int]:
        """Get a list containing the commulative lengths of each nested series 
        calculated by the length by the 'start', 'step-width' and 'end' indices.

        This returns the reversed commulative, that means that the most inner 
        series will have its normal length, the next outer one has the inner 
        length times its own length and so on.
        
        Example:
        ```
        Series over a with values [1, 2, 3]
            Series over b (on each point of a) with values [4, 5]
                Series over c (on each point of b) with values [6, 7, 8, 9]
        ```
        This function will return
        ```
        [0=a: 3*8=24, 1=b: 2*4=8, 2=c: 4]
        ```

        The list will start with the most outer length (the most outer series)
        at index 0 and add all the lengths of each "on-each-point" series.

        Returns
        -------
        list of int
            The commulative length of each series plus its nested series 
            starting with the most outer series
        """
        
        lengths = list(self._getNestLengths())
        reversed_commulative_lengths = []
        comm_length = 1
        for l in reversed(lengths):
            comm_length *= l
            reversed_commulative_lengths.insert(0, comm_length)

        return reversed_commulative_lengths
    
    def _getNestVariables(self) -> typing.Generator[str, None, None]:
        """Get a list containing the variables that the series is over.

        Returns
        -------
        generator of str
            The ids of the variables the base and each "on-each-point" series 
            are over
        """
        
        series = self.series
        while series is not None:
            yield series["variable"]

            if "on-each-point" in series:
                series = series["on-each-point"]
            else:
                series = None
                break
    
    def _getNestSeries(self) -> typing.Generator[dict, None, None]:
        """Get a list containing the complete series.

        Returns
        -------
        generator of dict
            The base series and each "on-each-point" series in a list where the 
            lowest index contains the most outer (base) series, the highest
            index contains the most inner series
        """
        
        return MeasurementSteps.getSeriesNests(self.series)
    
    def _getNestedSeriesForLevel(self, level: int) -> dict:
        """Get the series of the given `level`.

        This will go `level` times in the "on-each-point" series of the 
        `MeasurementStep.series` and return this dict.

        Example:
        ```python
        >>> MeasurementSteps.series
        {"variable": "a", "start": 0, "step-width": 2, "end": 6, "on-each-point":
            {"variable": "b", "start": 1, "step-width": 3, "end": 7, "on-each-point": 
                {"variable": "c", "start": 2, "step-width": 4, "end": 10}
            }
        }
        >>> MeasurementSteps._getNestedSeries(2)
        {"variable": "c", "start": 2, "step-width": 4, "end": 10}
        >>> MeasurementSteps._getNestedSeries(1)
        {"variable": "b", "start": 1, "step-width": 3, "end": 7, "on-each-point": 
            {"variable": "c", "start": 2, "step-width": 4, "end": 10}
        }
        ```

        Raises
        ------
        IndexError
            When the `level` is lower than zero or gerater than the maximum 
            level count

        Parameters
        ----------
        level : int
            The level to return, zero-based
        
        Returns
        -------
        dict
            The series dict of the given `level`
        """

        if level < 0:
            raise IndexError("The level '{}' is less than zero.".format(level))

        series = self.series
        for i in range(level):
            if "on-each-point" in series:
                series = series["on-each-point"]
            else:
                raise IndexError(("The level '{}' is greater than the " + 
                                  "maximum level {}.").format(level, i - 1))
        
        return series
    
    def _getCachedNests(self) -> typing.Tuple[int, typing.List[int], typing.List[dict]]:
        """Get the reversed and chached "nests" that are used for calculating 
        the current step.

        This function is for speeding up the `MeasurementSteps.__getitem__()` 
        function only.

        It returns the (cached) lists of the nests. Each "nest" is one series 
        where the first one (here reversed, so index *n*) is the most outer
        series, the next one (again reversed, so index *n-1*) is the next inner 
        series, so the "on-each-point" series of the first one, then the next
        inner one until the last one (reversed, so index 0) is the most inner 
        series.

        Returns
        -------
        int, list of int, list of dict
            The number of nests, commulative step count of each nest, the nest
            series
        """

        if self._cached_nests is None:
            log_debug(self._logger, "Creating nests and caching them")
            # nest_lengths = list(self._getNestLengths())
            # r_commulative_nest_lengths = tuple(reversed(tuple(self._getCommulativeNestLengths())))
            # commulative_nest_lengths = tuple(self._getCommulativeNestLengths())
            commulative_nest_lengths = self._getReversedCommulativeNestLengths()
            nest_series = tuple(self._getNestSeries())
            # r_nest_series = tuple(reversed(tuple(self._getNestSeries())))
            self._cached_nests = (len(nest_series),
                                #   nest_lengths,
                                  commulative_nest_lengths,
                                  nest_series)
        
        log_debug(self._logger, "Returning cached nests '{}'".format(
                               self._cached_nests))
        
        return self._cached_nests
    
    def __getitem__(self, index: int) -> dict:
        """Get the measurement step dict at the given `index`.

        Raises
        ------
        TypeError
            When the `index` is not an int
        IndexError
            When the `index` is out of bounds

        Returns
        -------
        dict
            The measurement step dict containing all measurement variable ids
            and their corresponding value for the given `index`
        """
        log_debug(self._logger, "Getting item for index '{}'".format(index))
        
        if index < 0:
            err = IndexError(("The index has to be greater than 0 but it " + 
                              "is '{}'.").format(index))
            log_error(self._logger, err)
            raise err
        elif index >= len(self):
            err = IndexError(("The index has to be smaller than {} but it " + 
                              "is '{}'.").format(len(self), index))
            log_error(self._logger, err)
            raise err
        
        nest_count, commulative_nest_lengths, nest_series = self._getCachedNests()
        
        # all steps are based on the start, each series value adds on to this 
        # start
        step = copy.deepcopy(self.start)

        # print("MeasurementSteps.__getitem__() for index {}".format(index))
        # for i, series in enumerate(nest_series):
        #     print("   {}: {}: {} values".format(i, series["variable"], commulative_nest_lengths[i]))
        log_debug(self._logger, "Iterating over nests '{}'".format(nest_series))
        
        remaining_index = index
        for i, series in enumerate(nest_series):
            if i + 1 < nest_count:
                value_index = remaining_index // commulative_nest_lengths[i + 1]
                # print("   calculating value index by {} // {} = {}".format(remaining_index, commulative_nest_lengths[i + 1], value_index))
                remaining_index = remaining_index % commulative_nest_lengths[i + 1]
            else:
                value_index = remaining_index
                remaining_index = None
            
            # print("   {}-th value index for value {}".format(value_index, series["variable"]))

            # print("   -> value is {}".format(series["start"] + value_index * series["step-width"]))

            step[series["variable"]] = max(
                series["start"], 
                min(
                    series["start"] + value_index * series["step-width"],
                    series["end"]
                )
            )

            log_debug(self._logger, ("Setting '{}' of step to start value " + 
                                    "'{}' plus '{}' times the step width "+ 
                                    "'{}' (= '{}') calculated from the '{}'th " + 
                                    "series (counting from outer to inner = " + 
                                    "fewest changes to most changes), " + 
                                    "remaining index is '{}'").format(
                                    series["variable"], series["start"], 
                                    value_index, series["step-width"], 
                                    step[series["variable"]], i, 
                                    remaining_index))

        # print("-> returning", step)
        log_debug(self._logger, "Returning step '{}'".format(step))

        return step
    
    def __iter__(self) -> collections.abc.Iterator:
        """Get this class as the iterator.

        Returns
        -------
        Iterator
            This object
        """
        log_debug(self._logger, "Initializing iteration over measurement steps")
        self._current_step = None
        self._carry = False
        self._r_nest_series = tuple(reversed(tuple(self._getNestSeries())))
        return self
    
    def __next__(self) -> dict:
        """Get the next step.

        This creates the steps by increasing the value of the most inner series
        if possible, if not it resets the value and increase the outer more

        Returns
        -------
        dict
            The measurement step
        """

        # print("MeasurementSteps.__next__()")
        log_debug(self._logger, "Creating next measurement step")

        if self._current_step is None:
            log_debug(self._logger, "Returing start '{}'".format(self.start))
            self._current_step = self.start
        elif self._carry:
            log_debug(self._logger, "Stopping iteration because carry is '{}'".format(
                    self._carry))
            raise StopIteration()
        else:
            # use the for-loop as a "carry", when the addition was successfull,
            # the for loop is stopped (and the carry is set to False), if 
            # increasing the value would make it bigger than the end value, 
            # set it to the start and add the next value, if all values have 
            # reached their end value, the iteration is over
            for series in self._r_nest_series:
                if (math.isclose(self._current_step[series["variable"]] + series["step-width"], series["end"]) or
                    self._current_step[series["variable"]] + series["step-width"] < series["end"]):
                    log_debug(self._logger, ("Adding step width '{}' of '{}' " + 
                                            "to current step is still " + 
                                            "smaller or equal than the end " + 
                                            "value '{}'").format(
                                            series["step-width"], 
                                            series["variable"], series["end"]))
                    self._current_step[series["variable"]] += series["step-width"]
                    self._carry = False
                    break
                else:
                    log_debug(self._logger, ("Adding step width '{}' of '{}' " + 
                                            "to current step is greater " + 
                                            " than the end value '{}', " + 
                                            "resetting value to start value " + 
                                            "and setting carry to True").format(
                                            series["step-width"], 
                                            series["variable"], series["end"]))
                    self._current_step[series["variable"]] = series["start"]
                    self._carry = True
            
            if self._carry:
                log_debug(self._logger, "Carry is true but all series are " + 
                                       "visited, that means that all steps " + 
                                       "are visited which means the " + 
                                       "measurement is done. Stopping " + 
                                       "iteration")
                raise StopIteration()
        
        log_debug(self._logger, "Returning step '{}'".format(self._current_step))
        # make sure to copy the step, otherwise the step will be modified after 
        # returning it
        return copy.deepcopy(self._current_step)

    @staticmethod
    def _getSeriesLength(series: dict) -> int:
        """Get the length of this series defined by the start, end and step 
        width.

        This ignores the "on-each-point" length.

        Parameters
        ----------
        series : dict
            The series dict
        
        Returns
        -------
        int
            The length of this series without the "on-each-point" series
        """
        return math.floor((series["end"] - series["start"]) / series["step-width"]) + 1
    
    @staticmethod
    def getSeriesNests(series: dict) -> typing.Generator[dict, None, None]:
        """Get a generator containing the complete series.

        Returns
        -------
        generator of dict
            The base series and each "on-each-point" series in a list where the 
            lowest index contains the most outer (base) series, the highest
            index contains the most inner series
        """
        
        s = series
        while s is not None:
            yield s

            if "on-each-point" in s:
                s = s["on-each-point"]
            else:
                s = None
                break
