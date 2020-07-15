import os
import re
import math
import typing
import textwrap

from .stop_program import StopProgram
from .abstract_view import AbstractView

class CLIView(AbstractView):
    """This class represents a very basic CLI view. It uses `print()` and 
    `input()` functions to display contents and react to user inputs.

    Attributes
    ----------
    line_length : int
        The number of characters that fit in one line
    error : str
        The current error to display
    """

    def __init__(self, controller: "Controller") -> None:
        """Get the CLIView object.
        
        Parameters
        ----------
        controller : Controller
            The controller
        """
        super().__init__(controller)

        self.line_length = min(79, os.get_terminal_size().columns)
        self.error = ""

        self.clear()
        self.printTitle()
    
    def clear(self) -> None:
        """Clear the current command line."""
        os.system('cls' if os.name=='nt' else 'clear')
    
    def printTitle(self) -> None:
        """Print the title."""

        from .config import PROGRAM_NAME

        self.print(PROGRAM_NAME)
        self.print("*" * len(PROGRAM_NAME))
        self.print("")

        if self.error != "":
            self.print("Error: {}".format(self.error))
        else:
            self.print("")

        self.error = ""

    def print(self, *values: object, 
              sep: typing.Optional[str]=" ", 
              end: typing.Optional[str]="\n",
              inset: typing.Optional[str]="") -> None:
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
        inset : str
            Some characters to print before every line
        """

        text = inset + sep.join(map(str, values)) + end
        text = textwrap.wrap(text, self.line_length, drop_whitespace=False,
                             replace_whitespace=False)
        text = ("\n" + inset).join(lines)

        print(text, sep="", end="")

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

        return self._showCreateMeasurementLoop(controller)
    
    def _showCreateMeasurementLoop(self, controller: "Controller",
                                   start: typing.Optional[dict]=None,
                                   series: typing.Optional[dict]=None) -> typing.Tuple[dict, dict]:

        default_var = None
        measuremnt_vars_inputs = []
        variable_ids = []
        errors = []

        for v in controller.microscope.supported_measurement_variables:
            variable_ids.append(v.unique_id)

            if default_var is None:
                default_var = v
            
            if not isinstance(start, dict):
                start = {}
            if not v.unique_id in start:
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
            
            measuremnt_vars_inputs.append({
                "id": v.unique_id,
                "label": str(v.name) + " [{}]".format(v.unit) if v.unit is not None else "",
                "datatype": float,
                "min_value": v.min_value,
                "max_value": v.max_value,
                "required": True,
                "value": start[v.unique_id]
            })
        
        if not isinstance(series, dict):
            series = {}
        if not "variable" in series:
            series["variable"] = default_var.unique_id
        series_inputs, series_errors = self._parseSeriesInputs(series, controller)
        errors += series_errors

        self.errors = "\n".join(errors)

        values, command = self._printSelect(
            "Define the start conditions",
            measuremnt_vars_inputs,
            "Define the series",
            series_inputs
        )

        series_reg = re.compile(r"series-([\d]+)-([\w\-]+)")
        start = {}
        series = {}
        for k, v in values.items():
            if k in variable_ids:
                start[k] = float(v)
            else:
                match = series_reg.match(k)

                if match is not None:
                    depth = int(match.group(1))
                    s = series
                    for _ in range(depth):
                        if not "on-each-point" in s:
                            s["on-each-point"] = {}
                        s = s["on-each-point"]

                    if match.group(2) == "start":
                        s["start"] = float(v)
                    elif match.group(2) == "step-width":
                        s["step-width"] = float(v)
                    elif match.group(2) == "end":
                        s["end"] = float(v)

        if command == True:
            return start, series
        elif command == False:
            raise StopProgram
        else:
            # restart loop
            return self._parseSeriesInputs(start, series)
    
    
    def _parseSeriesInputs(self, series: dict, controller: "Controller", 
                           path: typing.Optional[list]=[]) -> typing.Tuple[list, list]:
        """Parse the given `series` recursively and return the inputs and the 
        errors if there are some.

        Takes the `series` dict and parses the keys. If the keys are not given
        or values are invalid, defaults are used instead and an error message 
        will be appended to the error log.

        Parameters
        ----------
        series : dict
            The series dict with at least the 'variable' index that contains a
            valid `MeasurementVariable` id, optional with the 'start', 'end',
            'step-width' and 'on-each-point' keys
        controller : Controller
            The controller to use
        path : list, optional
            The parent 'variable' ids if the `series` is the series in the 
            'on-each-point' index of the parent
        
        Returns
        -------
        list, list
            The input list at index 0, the error message list at index 1
        """

        var = controller.microscope.getMeasurementVariableById(series["variable"])
        errors = []
        if isinstance(path, (list, tuple)):
            path_str = "".join([" in 'on-each-step' of {}".format(p) 
                                  for p in path])
        else:
            path_str = ""

        keys = {
            "start": min(max(0, var.min_value), var.max_value),
            "end": var.max_value,
            "step-width": (var.max_value - var.min_value) / 10
        }

        for k, d in keys.items():
            if not k in series or not isinstance(series[k], (int, float)):
                series[k] = d
                # errors.append(("The series{} '{}' key is not " + 
                #                "defined.").format(path_str, k))
            elif (k == "start" or k == "end") and series[k] < var.min_value:
                series[k] = var.min_value
                errors.append(("The series{} '{}' key is less than the " + 
                               "minimum value of {}.").format(path_str, k, 
                                                              var.min_value))
            elif (k == "start" or k == "end") and series[k] > var.max_value:
                series[k] = var.max_value
                errors.append(("The series{} '{}' key is greater than the " + 
                               "maximum value of {}.").format(path_str, k, 
                                                              var.max_value))

        variable_names = [v.unique_id for v in 
                          controller.microscope.supported_measurement_variables]
        variable_names = list(filter(lambda x: x not in path, variable_names))
        # do not allow to make a series of the current variable on each point 
        # of the current series
        on_each_point_names = variable_names.copy()
        on_each_point_names.remove(series["variable"])

        series_inputs = [
            {
                "id": "series-{}-variable".format(len(path)),
                "label": "Series over",
                "datatype": variable_names,
                "required": True,
                "value": series["variable"],
                "inset": len(path) * "  "
            },
            {
                "id": "series-{}-start".format(len(path)),
                "label": "Start value",
                "datatype": float,
                "min_value": var.min_value,
                "max_value": var.max_value,
                "required": True,
                "value": series["start"],
                "inset": len(path) * "  "
            },
            {
                "id": "series-{}-step-width".format(len(path)),
                "label": "Step width",
                "datatype": float,
                "min_value": 0,
                "max_value": var.max_value - var.min_value,
                "required": True,
                "value": series["step-width"],
                "inset": len(path) * "  "
            },
            {
                "id": "series-{}-end".format(len(path)),
                "label": "End value",
                "datatype": float,
                "min_value": var.min_value,
                "max_value": var.max_value,
                "required": True,
                "value": series["end"],
                "inset": len(path) * "  "
            },
            {
                "id": "series-{}-on-each-point".format(len(path)),
                "label": "Series on each point",
                "datatype": on_each_point_names,
                "required": False,
                "value": series["on-each-point"] if "on-each-point" in series else None,
                "inset": len(path) * "  "
            }
        ]
        
        if ("on-each-point" in series and 
            isinstance(series["on-each-point"], dict) and
            "variable" in series["on-each-point"]):
            child_inputs, child_errors = self._parseSeriesInputs(
                series["on-each-point"],
                controller,
                path + [series["variable"]]
            )

            series_inputs += child_inputs
            errors += child_errors
        
        return series_inputs, errors

    def _printSelect(self, *args: typing.Union[str, dict]) -> dict:
        """Show a select overview.

        This does not start a loop. This shows some inputs one time, the user 
        can modify them one time or continue. In both cases the (new) values 
        will be returned in a dict including all ids and their values. The 
        calling function has to take care, if multiple inputs can be changed 
        (which is nearly always the case).
        
        An input can have the following indices:
        - "label": str (required), the name to show to the user
        - "id": str (required), the id that is used in the returned dict
        - "datatype": type or list (required), the type, currently 
          supported: float or a list of possible inputs
        - "value": <type of "datatype" or None if "required" is False> 
          (required), the value to use, only if "required" is false, None can 
          be used too
        - "min_value": float (optional), the minimum value that is allowed, 
          only for numeric inputs
        - "max_value": float (optional), the maximum value that is allowed, 
          only for numeric inputs
        - "required": bool (optional), whether the current input has to be
          set or not, default: False
        - "inset": str (optional), a string to add in front of the line for the 
          input
        
        Returns
        -------
        dict, bool or None
            The dict with the values at index 0, True at index 1 if the user
            wants to continue, False if he/she wants to cancel and None if the
            user selected someting without "pressing" continue or "cancel"
        """

        self.clear()
        self.printTitle()

        label_col_width = max([len(l["label"]) if isinstance(l, dict) else 0 
                               for l in args])

        max_index = len(filter(lambda x: isinstance(x, dict), args)) - 1
        index_width = math.floor(math.log10(max_index) + 1)
        index = 0
        values = {}

        for line in args:
            if isinstance(line, str):
                self.print(line)
            elif isinstance(line, dict):
                values[line["id"]] = line["value"]

                text = ("[{:" + index_width + "}]" + 
                        "{:" + str(label_col_width) + "} {}").format(
                            index,
                            (str(line["name"]) + 
                            "*" if "required" in line and line["required"] else "" + 
                            ":"), 
                            line["value"]
                        )

                if "min_value" in line and "max_value" in line:
                    text += " {} <= val <= {}".format(line["min_value"],
                                                     line["max_value"])
                elif "min_value" in line:
                    text += " >= {}".format(line["min_value"])
                elif "max_value" in line:
                    text += " >= {}".format(line["max_value"])

                if "inset" in line:
                    inset = line["inset"]
                else:
                    inset = ""
                
                self.print(text, inset=inset)
                index += 1

        self.print("")
        self.print("Type in the number to change the value of, type [c] for " + 
                   "continue and [x] for Cancel.")
        user_input = self.input("Number, [c] or [x]: ")

        if user_input == "x":
            return values, False
        elif user_input == "c":
            return values, True
        elif 0 <= int(user_input) and int(user_input) <= max_index:
            index = int(user_input)
            id_index_map = list(values.keys())
            id_ = id_map[index]
            id_args_map = [l["id"] if isinstance(l, dict) else None for l in args]
            args_index = id_args_map.search(id_)
            input_definition = args[args_index]

            args = list(args)
            values[id_] = self._inputValueLoop(input_definition)

            return values[id_], None
        else:
            # error is shown in CLIView::printTitle
            self.error = "The input '{}' is not valid.".format(user_input)
            self._printSelect(*args)