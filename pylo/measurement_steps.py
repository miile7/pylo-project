import copy
import math
import typing
import functools
import collections.abc

from .pylolib import get_datatype_human_text

class MeasurementSteps(collections.abc.Sequence):
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
        
        self.controller = controller
        self.series = self._formatSeries(controller, series)
        self.start = self._formatStart(controller, start, self.series)
    
    def _formatSeries(self, controller: "Controller", series: dict, 
                      series_path: typing.Optional[list]=[]) -> dict:
        """Format the given `series` to contain valid values only.

        If an invalid value is found, an error will be raised.

        Raises
        ------
        KeyError
            When the `series` is missing the one of the 'variable', 'start', 
            'end' or 'step-width' indices
        ValueError
            When the `series` 'start', 'step-width' or 'end' index contains 
            invalid values (e.g. values are out of the bounds the 
            `MeasurementVariable` defines or the 'step-width' is smaller or 
            equal to zero) or the 'on-each-point' contains a variable that is 
            measured already (preventing recursive series)
        TypeError
            When one of the values has the wrong type

        Parameters
        ----------
        controller : Controller
            The controller for the measurement and the microscope
        series : dict with str, and three or four times int or float
            A dict with the 'variable', 'start', 'step-width', 'end' and the 
            optional 'on-each-point' indices. The series iterate the 
            `MeasurementVaraible` at the 'variable' index starting with 'start'
            and ending at 'end' (including start and end) while travelling with 
            the 'step-width'. The 'on-each-point' can hold another series dict
            that defines another series that will be iterated over on each step
            the current series does.
        series_path : tuple, optional
            This is for internal use only. It holds the variable names of the 
            parent series if the current parse series is in the 'on-each-point'
            index of another series
        
        Returns
        -------
        dict
            The valid `start` dict
        """

        if isinstance(series_path, (list, tuple)):
            error_str = "".join([" in 'on-each-point' of {}".format(p) 
                                  for p in series_path])
        else:
            series_path = []
            error_str = ""

        series_definition = {
            "start": (int, float), 
            "end": (int, float), 
            "step-width": (int, float), 
            "variable": str
        }

        # check if all required indices are present and if their type is 
        # correct
        for key, datatype in series_definition.items():
            if key not in series:
                raise KeyError(("The series{} does not have a '{}' " + 
                                "index.").format(error_str, key))
            elif not isinstance(series[key], datatype):
                raise TypeError(("The series{} '{}' key has to be of type {} " + 
                                 "but it is {}.").format(
                                     error_str,
                                     key, 
                                     get_datatype_human_text(datatype),
                                     type(series[key])))
        
        # check if the series variable exists
        try:
            series_variable = controller.microscope.getMeasurementVariableById(
                series["variable"]
            )
        except KeyError:
            raise ValueError(("The variable '{}' in the series{} is not a " + 
                              "valid measurement variable id.").format(
                                  series["variable"], error_str))
        
        # prevent recursive series, the series variable must not be in one of 
        # the parent series (if there are parent series)
        if series["variable"] in series_path:
            raise ValueError(("The variable '{}' in the series{} is " + 
                              "already measured in one of the parent " +
                              "series.").format(series["variable"], error_str))
        # test if step is > 0
        if series["step-width"] <= 0:
            raise ValueError(("The 'step-width' in the series{} must be "+ 
                              "greater than 0.").format(error_str))
        
        # test if the start and end values are in the boundaries
        for index in ("start", "end"):
            if (series[index] < series_variable.min_value or 
                series[index] > series_variable.max_value):
                raise ValueError(("The '{index}' index in the series{path} is " + 
                                  "out of bounds. The {index} has to be " + 
                                  "{min} <= {index} <= {max} but it is " + 
                                  "{val}.").format(
                                      path=error_str,
                                      index=index, 
                                      min=series_variable.min_value,
                                      max=series_variable.max_value,
                                      val=series[index]
                                ))

        if isinstance(series_path, (tuple, list)):
            series_path = list(series_path)
        else:
            series_path = []
        
        series_path.append(series["variable"])

        if "on-each-point" in series:
            if isinstance(series["on-each-point"], dict):
                series["on-each-point"] = self._formatSeries(
                    controller, series["on-each-point"], series_path
                )
            else:
                del series["on-each-point"]
        
        return series
        
    def _formatStart(self, controller: "Controller", start: dict, series: dict) -> dict:
        """Format the given `start` to contain valid values only.

        If an invalid value is found, an error will be raised.

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
        dict
            The valid `start` dict
        """

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

        # check and create start variables
        for var in controller.microscope.supported_measurement_variables:
            if var.unique_id in series_starts:
                # make sure also the measured variable is correct
                start[var.unique_id] = series_starts[var.unique_id]
            elif var.unique_id not in start:
                raise KeyError(("The measurement variable {} (id: {}) "  + 
                                  "is neither contained in the start " + 
                                  "conditions nor in the series. All " + 
                                  "parameters (measurement variables) " + 
                                  "values must be known!").format(
                                      var.name, var.unique_id))

            if not isinstance(start[var.unique_id], (int, float)):
                raise TypeError(("The '{}' index in the start conditions " + 
                                 "contains a {} but only int or float are " + 
                                 "supported.").format(
                                     var.unique_id, 
                                     type(start[var.unique_id])))
            elif (start[var.unique_id] < var.min_value or 
                  start[var.unique_id] > var.max_value):
                raise ValueError(("The '{index}' index in the start " + 
                                  "conditions is out of bounds. The {index} " + 
                                  "has to be {min} <= {index} <= {max} but " + 
                                  "it is {val}.").format(
                                    index=var.unique_id, 
                                    min=var.min_value,
                                    max=var.max_value,
                                    val=start[var.unique_id]
                                ))

        return start
    
    def __len__(self) -> int:
        """Get the number of steps.

        Returns
        -------
        int
            The number of steps
        """

        # calculate the product of each "on-each-point" series length which is 
        # returned by MeasurementSteps._getNestLengths()
        return functools.reduce(lambda x, y: x * y, self._getNestLengths(), 1)
    
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
        
        series = self.series
        while series is not None:
            yield series

            if "on-each-point" in series:
                series = series["on-each-point"]
            else:
                series = None
                break
    
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

        if (not hasattr(self, "_cached_nests") or 
            self._cached_nests is None):
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
        if index < 0:
            raise IndexError(
                "The index has to be greater than 0 but it is '{}'.".format(index)
            )
        elif index >= len(self):
            raise IndexError(
                "The index has to be smaller than {} but it is '{}'.".format(
                    len(self), index
                )
            )
        
        nest_count, commulative_nest_lengths, nest_series = self._getCachedNests()
        
        # all steps are based on the start, each series value adds on to this 
        # start
        step = copy.deepcopy(self.start)

        # print("MeasurementSteps.__getitem__() for index {}".format(index))
        # for i, series in enumerate(nest_series):
        #     print("   {}: {}: {} values".format(i, series["variable"], commulative_nest_lengths[i]))
        
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

        # print("-> returning", step)

        return step
    
    def __iter__(self) -> collections.abc.Iterator:
        """Get this class as the iterator.

        Returns
        -------
        Iterator
            This object
        """
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

        if self._current_step is None:
            self._current_step = self.start
        elif self._carry:
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
                    self._current_step[series["variable"]] += series["step-width"]
                    self._carry = False
                    break
                else:
                    self._current_step[series["variable"]] = series["start"]
                    self._carry = True
            
            if self._carry:
                raise StopIteration()
        
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
