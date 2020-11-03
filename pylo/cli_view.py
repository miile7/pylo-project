import os
import re
import sys
import math
import typing
import textwrap
import linecache

from .pylolib import format_value
from .pylolib import get_datatype_human_text
from .pylolib import human_concat_list
from .datatype import Datatype
from .stop_program import StopProgram
from .abstract_view import AskInput
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

    def __init__(self) -> None:
        """Get the CLIView object.
        """

        self.line_length = 79
        try:
            l = os.get_terminal_size().columns
        except (OSError, ValueError):
            l = self.line_length
            pass
        if l < self.line_length:
            self.line_length = l
        
        self.error = ""

        super().__init__()
        self.clear()
        self.printTitle()
    
    def clear(self) -> None:
        """Clear the current command line."""
        try:
            # for custom implementations of the stdout, especially in the test
            sys.stdout.clear()
            sys.stdout.cls()
        except (NameError, TypeError, AttributeError):
            pass
        
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
        sep : str, optional
            The separator between two values, default: " "
        end : str, optional
            The end character to end a line, default: "\n"
        inset : str, optional
            Some characters to print before every line, default: ""
        """

        text = inset + sep.join(map(str, values)) + end
        text = textwrap.wrap(text, self.line_length, drop_whitespace=False,
                             replace_whitespace=False)
        text = ("\n" + inset).join(text)

        print(text, sep="", end="")
    
    def input(self, text: str, inset: typing.Optional[str]="") -> str:
        """Get the input of the user.

        Parameters
        ----------
        text : str
            The text to show in front of the input
        inset : str, optional
            Some characters to print before every line, default: ""
        
        Returns
        -------
        str
            The user input
        """
        text = textwrap.wrap(text, self.line_length, drop_whitespace=False,
                             replace_whitespace=False)
        text = ("\n" + inset).join(text)

        return input(text)

    def showCreateMeasurement(self, controller: "Controller") -> typing.Tuple[dict, dict]:
        """Show the dialog for creating a measurement.

        Raises
        ------
        StopProgram
            When the user wants to cancel the creation.
        
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

        return self._showCreateMeasurementLoop(controller)
    
    def _showCreateMeasurementLoop(self, controller: "Controller",
                                   start: typing.Optional[dict]=None,
                                   series: typing.Optional[dict]=None) -> typing.Tuple[dict, dict]:
        """Show the create measurement view until the measurement is valid or 
        the user cancels the creation.

        This function calls itself again whenever the user changes something.
        This way the content is redrawn until the user confirms his/her inputs.

        Note that the parameters are for the recursive call only.

        Raises
        ------
        StopProgram
            When the user wants to cancel the creation.

        Parameters
        ----------
        start : dict, optional (for recursive use only!)
            The start dict as it is required for the `Measurement::fromSeries()`
            function with the `MeasurementVariable`s as the keys and their 
            start values as their values with uncalibrated values
        series : dict, optional (for recursive use only!)
            The series dict as it is required for the 
            `Measurement::fromSeries()` with the 'variable', 'start', 
            'step-width', 'end' and the optional 'on-each-point' indices with 
            uncalibrated values
        
        Returns
        -------
        dict, dict
            The valid and filled `start` dict at index 0, the `series` dict at
            index 1 bot as they are required in the `Measurement::fromSeries()`
            function.
        """

        measuremnt_vars_inputs = []
        errors = []

        start, start_errors = self.parseStart(
            controller.microscope.supported_measurement_variables, start, 
            add_defaults=True, parse=False, uncalibrate=False
        )
        for id_ in start:
            v = controller.microscope.getMeasurementVariableById(id_)
            
            if v.has_calibration and v.calibrated_name is not None:
                label = str(v.calibrated_name)
                if v.calibrated_unit is not None:
                    label += " [{}]".format(v.calibrated_unit)
            else:
                label = str(v.name)
                if v.unit is not None:
                    label += " [{}]".format(v.unit)

            measuremnt_vars_inputs.append({
                "id": v.unique_id,
                "label": label,
                "datatype": v.calibrated_format if v.has_calibration else v.format,
                "min_value": v.ensureCalibratedValue(v.min_value),
                "max_value": v.ensureCalibratedValue(v.max_value),
                "required": True,
                "value": v.ensureCalibratedValue(start[v.unique_id])
            })
        
        errors += start_errors
        if not isinstance(series, dict):
            series = {}
        
        series_inputs, series_errors = self._parseSeriesInputs(controller, series)
        errors += series_errors

        self.error = "\n".join(errors)

        values, command, changed = self._printSelect(
            "Define the start conditions",
            *measuremnt_vars_inputs,
            "",
            "Define the series",
            *series_inputs
        )

        series_reg = re.compile(r"series-([\d]+)-([\w\-]+)")
        
        start = {}
        series = {}
        variable_ids = [v.unique_id for v in 
                        controller.microscope.supported_measurement_variables]
        for k, v in values.items():
            if k in variable_ids:
                start[k] = v
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
                        s["start"] = v
                    elif match.group(2) == "step-width":
                        s["step-width"] = v
                    elif match.group(2) == "end":
                        s["end"] = v
                    elif (match.group(2) == "variable" and v in variable_ids and
                        ("variable" not in s or changed == k)):
                        # on-each-point sets the "variable" key already, only 
                        # overwrite if the user changes this value, this is 
                        # necessary because the variable in the on-each-point
                        # value can be changed by either the 
                        # series-on-each-point value or the 'variable' value of
                        # the new sub-series
                        s["variable"] = v
                    elif (match.group(2) == "on-each-point" and v in variable_ids):
                        s["on-each-point"] = {"variable": v}
        
        # recalculate to uncalibrated values, do another validation because the
        # iteration is there anyway
        start, _ = self.parseStart(
            controller.microscope.supported_measurement_variables, start,
            add_defaults=True, parse=False, uncalibrate=True
        )
        series, _ = self.parseSeries(
            controller.microscope.supported_measurement_variables, series, 
            add_defaults=True, parse=False, uncalibrate=True
        )

        if command == True:
            return start, series
        elif command == False:
            raise StopProgram
        else:
            # restart loop
            return self._showCreateMeasurementLoop(controller, start, series)
    
    def _parseSeriesInputs(self, controller: "Controller", series: dict) -> typing.Tuple[list, list]:
        """Parse the given `series` recursively and return the inputs and the 
        errors if there are some.

        Takes the `series` dict and parses the keys. If the keys are not given
        or values are invalid, defaults are used instead and an error message 
        will be appended to the error log.

        Parameters
        ----------
        controller : Controller
            The controller to use
        series : dict
            The series dict with at least the 'variable' index that contains a
            valid `MeasurementVariable` id, optional with the 'start', 'end',
            'step-width' and 'on-each-point' keys with uncalibrated values
        
        Returns
        -------
        list, list
            The input list at index 0, the error message list at index 1
        """
        
        series_inputs = []
        series, errors = self.parseSeries(
            controller.microscope.supported_measurement_variables, series, 
            add_defaults=True, parse=False, uncalibrate=False
        )
        if series is None:
            return series_inputs, errors
        
        variable_ids = [v.unique_id for v in
                        controller.microscope.supported_measurement_variables]

        depth = 0
        s = series
        while s is not None:
            var = controller.microscope.getMeasurementVariableById(s["variable"])

            on_each_point_ids = variable_ids.copy()
            if s["variable"] in on_each_point_ids:
                on_each_point_ids.remove(s["variable"])

            series_inputs += [
                {
                    "id": "series-{}-variable".format(depth),
                    "label": "Series variable",
                    "datatype": variable_ids.copy(),
                    "required": True,
                    "value": s["variable"],
                    "inset": depth * "  "
                },
                {
                    "id": "series-{}-start".format(depth),
                    "label": "Start value",
                    "datatype": var.calibrated_format if var.has_calibration else var.format,
                    "min_value": var.ensureCalibratedValue(var.min_value),
                    "max_value": var.ensureCalibratedValue(var.max_value),
                    "required": True,
                    "value": var.ensureCalibratedValue(s["start"]),
                    "inset": depth * "  "
                },
                {
                    "id": "series-{}-step-width".format(depth),
                    "label": "Step width",
                    "datatype": var.calibrated_format if var.has_calibration else var.format,
                    "min_value": var.ensureCalibratedValue(0),
                    "max_value": var.ensureCalibratedValue(var.max_value - var.min_value),
                    "required": True,
                    "value": var.ensureCalibratedValue(s["step-width"]),
                    "inset": depth * "  "
                },
                {
                    "id": "series-{}-end".format(depth),
                    "label": "End value",
                    "datatype": var.calibrated_format if var.has_calibration else var.format,
                    "min_value": var.ensureCalibratedValue(var.min_value),
                    "max_value": var.ensureCalibratedValue(var.max_value),
                    "required": True,
                    "value": var.ensureCalibratedValue(s["end"]),
                    "inset": depth * "  "
                },
                {
                    "id": "series-{}-on-each-point".format(depth),
                    "label": "Series on each point",
                    "datatype": on_each_point_ids,
                    "required": False,
                    "value": s["on-each-point"]["variable"] if "on-each-point" in s else None,
                    "inset": depth * "  "
                }
            ]

            if ("on-each-point" in s and 
                isinstance(s["on-each-point"], dict)):
                if s["variable"] in variable_ids:
                    variable_ids.remove(s["variable"])
                s = s["on-each-point"]
                depth += 1
            else:
                break
        
        return series_inputs, errors

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
        self.print(hint)

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
        self.printTitle()
        
        if isinstance(error, Exception):
            raise error
            exc_type, exc_obj, tb = sys.exc_info()
            lineno = tb.tb_lineno
            frame = tb.tb_frame
            filename = frame.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, frame.f_globals)

            error_msg = "{} (#{} in {})".format(
                error, line, os.path.basename(filename)
            )
        else:
            error_msg = "{}".format(error)

        self.print("Error: {}".format(error_msg))
        self.error = "Error: {}".format(error_msg)

        if isinstance(how_to_fix, str) and how_to_fix != "":
            self.print("")
            self.print(how_to_fix)
    
    def showRunning(self):
        """Show that the program is running."""
        self.printTitle()
        self._updateRunning()
        super().showRunning()
    
    def _updateRunning(self):
        """Update the running indicator, the progress has updated."""

        counter_width = math.floor(math.log10(self.progress_max)) + 1
        loader_width = self.line_length - 2 * counter_width - 2
        prog = round((self.progress / self.progress_max) * loader_width)

        line = ("{:" + str(loader_width) + "} " + 
                "{:" + str(counter_width) + "}/" + 
                "{:" + str(counter_width) + "}")
        
        self.print("\b" * self.line_length + line.format(
            "█" * prog + "▒" * (loader_width - prog),
            self.progress,
            self.progress_max
        ), sep="", end="")
    
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
        values = self._showSettingsLoop(configuration, keys)

        if set_in_config:
            for group in values:
                for key in values[group]:
                    configuration.setValue(group, key, values[group][key])
        
        return values

    def _showSettingsLoop(self, configuration: "AbstractConfiguration", 
                     keys: dict=None,
                     config_dict: typing.Optional[dict]=None) -> dict:
        """Show the settings loop.

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
        
        Returns
        -------
        dict of dict
            A dict that contains the groups as keys, as the value there is 
            another dict for the keys in that group, the value is the newly set
            value
        """
        self.printTitle()

        if not isinstance(config_dict, dict):
            config_dict = {}
        
        setting_inputs = []

        for group, key, value, datatype, default, ask, description, restart in configuration.items():
            if not isinstance(keys, (list, tuple)) or (group, key) in keys:
                if group in config_dict and key in config_dict[group]:
                    val = config_dict[group][key]
                elif value is not None:
                    val = value
                else:
                    val = default

                setting_inputs.append({
                    "label": "{} ({})".format(key, group),
                    # escape minus
                    "id": "{}-{}".format(group.replace("-", "--"), key.replace("-", "--")),
                    "datatype": datatype,
                    "value": val,
                    "description": description
                })
            
                if not group in config_dict:
                    config_dict[group] = {}
                
                config_dict[group][key] = val

        values, command, _ = self._printSelect(
            "Change settings.",
            *setting_inputs
        )

        for id_ in values:
            # single minus is only used by the separator between group and key
            group, key = re.split(r"(?<!-)-(?!-)", id_)
            group = group.replace("--", "-")
            key = key.replace("--", "-")

            if not group in config_dict:
                config_dict[group] = {}
            
            config_dict[group][key] = values[id_]

        if command == False:
            raise StopProgram
        elif command == True:
            return config_dict
        else:
            return self._showSettingsLoop(configuration, keys, config_dict)

    def askFor(self, *inputs: AskInput, **kwargs) -> tuple:
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
        
        Keyword Args
        ------------
        text : str
            The text to show when the input lines pop up, default:
            "Please enter the following values."
        
        Returns
        -------
        tuple
            A tuple of values where the value on index 0 is the value for the 
            `inputs[0]` and so on
        """

        return self._askForLoop(inputs, None, **kwargs)

    def _askForLoop(self, inputs: typing.Sequence[AskInput], 
                    ask_dict: typing.Optional[dict]=None, **kwargs):
        """Show the ask for loop.
        
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
        inputs : sequence of dicts
            Dicts with the 'name' key that defines the name to show. Optional
            additional keys are 'datatype', 'description', 'options' and 
            'allow_custom'
        
        Keyword Args
        ------------
        text : str
            The text to show when the input lines pop up, default:
            "Please enter the following values."
        
        Returns
        -------
        tuple
            A tuple of values where the value on index 0 is the value for the 
            `inputs[0]` and so on
        """
        if not isinstance(ask_dict, dict):
            ask_dict = {}

        input_definitions = []

        if not "text" in kwargs:
            input_definitions.append("Please enter the following values.")
        elif isinstance(kwargs["text"], str):
            input_definitions.append(kwargs["text"])
        
        for i, line in enumerate(inputs):
            l = {
                "label": line["name"],
                "id": i,
                "required": True
            }
            if ("options" in line and isinstance(line["options"], (list, tuple)) and 
                (not "allow_custom" in line or not line["allow_custom"])):
               l["datatype"] = line["options"]
            elif isinstance(line["datatype"], type):
                l["datatype"] = line["datatype"]
            else:
                l["datatype"] = str
            
            if "description" in line:
                l["description"] = line["description"]
            
            if i in ask_dict:
                l["value"] = ask_dict[i]
            else:
                l["value"] = None
            
            input_definitions.append(l)
        
        values, command, _ = self._printSelect(
            *input_definitions
        )

        if command == False:
            raise StopProgram
        elif command == True:
            return tuple(map(lambda x: x[1], sorted(values.items(), key=lambda x: x[0])))
            # return tuple(sorted(values.items(), key=lambda x: x[0]))
        else:
            return self._askForLoop(inputs, values, **kwargs)

    def _printSelect(self, *args: typing.Union[str, dict]) -> typing.Tuple[dict, typing.Union[bool, None], typing.Union[str, None]]:
        """Show a select overview.

        This function offers to change multiple values. Each value will be 
        displayed in one line. There will be a number in front of each line. 
        To change a value, the user must enter this number.

        Text can directly be passed to the function and will be output. Inputs
        are defined by the use of dicts as described below.

        This function will terminate whenever the user decides to continue or 
        to cancel (by entering the code for continuing or for cancelling) or 
        when the user changes a value. In the first case True is returned as 
        the second return value, in the second False. When a value is changed, 
        the index 1 of the return value will hold None.

        The returned value at index 0 will hold the values after the function 
        is terminated. The keys are the 'id's of the inputs, the values are 
        the values in the type that the input defines.
        
        An input is defined with the following indices:
        - "label": str (required), the name to show to the user
        - "id": str (required), the id that is used in the returned dict
        - "datatype": type, Datatype or list (required), the type, currently 
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
        
        The user can edit the value with the number, continue with 'c' and 
        quit with 'q'.
        
        Returns
        -------
        dict, bool or None
            The dict with the values at index 0, True at index 1 if the user
            wants to continue, False if he/she wants to cancel and None if the
            user selected someting without "pressing" continue or "cancel" and
            the "id" of the changed value or None if nothing changed or a 
            command ("continue" or "cancel") was performed at index 2
        """

        self.clear()
        self.printTitle()

        none_val = "<empty>"

        # get the char counts (=width) of each column to make calculate the 
        # layout
        label_widths = []
        value_widths = [len(none_val)]
        max_index = -1

        for line in args:
            if isinstance(line, dict):
                label_widths.append(len(line["label"]))
                value_widths.append(len(format_value(
                    line["datatype"], line["value"]
                )))
                max_index += 1

        # the label char width, +1 for the colon, +1 for the "required" asterix
        label_width = max(label_widths) + 2
        value_width = max(value_widths)
        
        if max_index > 0:
            index_width = math.floor(math.log10(max_index) + 1)
        else:
            index_width = 1
        index = 0
        values = {}
        id_index_map = {}

        for line in args:
            if isinstance(line, str):
                self.print(line)
            elif isinstance(line, dict):
                values[line["id"]] = line["value"]
                id_index_map[index] = line["id"]

                text = ("[{index:" + str(index_width) + "}] " + 
                        "{label:" + str(label_width) + "} " + 
                        "{value:<" + str(value_width) + "} " + 
                        "{conditions}")
                
                conditions = ""
                if "min_value" in line and "max_value" in line:
                    conditions = " {} <= val <= {}".format(
                        format_value(line["datatype"], line["min_value"]),
                        format_value(line["datatype"], line["max_value"])
                    )
                elif "min_value" in line:
                    conditions = " >= {}".format(
                        format_value(line["datatype"], line["min_value"])
                    )
                elif "max_value" in line:
                    conditions = " >= {}".format(
                        format_value(line["datatype"], line["max_value"])
                    )
                
                text_value = ""
                if line["value"] is None:
                    text_value = none_val
                else:
                    text_value = format_value(
                        line["datatype"], line["value"]
                    )

                text = text.format(
                    index=index,
                    label=(
                        str(line["label"]) + 
                        ("*" if "required" in line and line["required"] else "") + 
                        ":"
                    ), 
                    value=text_value,
                    conditions=conditions
                )

                if "inset" in line:
                    inset = line["inset"]
                else:
                    inset = ""
                
                self.print(text, inset=inset)
                index += 1

        self.print("")
        self.print("Type in the number to change the value of, type [c] for " + 
                   "continue and [q] for quit.")
        user_input = self.input("Number, [c]ontinue or [q]uit: ")

        if user_input == "q":
            return values, False, None
        elif user_input == "c":
            errors = []

            counter = 0
            for line in args:
                # check if all arguments are the correct type and set if 
                # required
                if isinstance(line, dict):
                    try:
                        self._parseValue(line, values[line["id"]])
                    except ValueError as e:
                        errors.append(
                            ("{} (#{})".format(line["label"], counter), e)
                        )
                    counter += 1
            
            if len(errors) > 0:
                self.error = "The values for {} are invalid.".format(
                    human_concat_list([e[0] for e in errors], word=" and ")
                )
                self.error += " (Details: "
                for i, e in enumerate(errors):
                    self.error += "{}: {}".format(e[0], e[1])

                    if i + 1 < len(errors):
                        self.error += "; "
                
                self.error += ")"
                return self._printSelect(*args)
            else:
                return values, True, None
        else:
            try:
                user_input = int(user_input)
            except ValueError:
                # error is shown in CLIView::printTitle
                self.error = ("The input '{}' neither is a number nor a " + 
                              "command so it cannot be interpreted.").format(user_input)
                return self._printSelect(*args)

            if 0 <= user_input and user_input <= max_index:
                index = int(user_input)
                id_ = id_index_map[index]
                id_args_map = [l["id"] if isinstance(l, dict) else None for l in args]
                args_index = id_args_map.index(id_)
                input_definition = args[args_index]

                args = list(args)
                try:
                    v = self._inputValueLoop(input_definition)

                    if (v is not None or (not "required" in input_definition or 
                        not input_definition["required"])):
                        values[id_] = v
                    else:
                        id_ = None
                except StopProgram:
                    pass

                return values, None, id_
            else:
                # error is shown in CLIView::printTitle
                self.error = ("The input '{}' is out of range. Please type " + 
                              "a number 0 <= number <= {}.").format(user_input,
                                                                    max_index)
                return self._printSelect(*args)
    
    def _inputValueLoop(self, input_definition: dict) -> typing.Any:
        """Get the input for the `input_definition` by asking the user.

        The `input_definition` is a dict that supports the following keys:
        - "label": str (required), the name to show to the user
        - "id": str (required), the id that is used in the returned dict
        - "datatype": type, Datatype or list (required), the type, currently 
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
        - "description": str (optional), a description what this value is about

        The user can enter the value, 'x' or '!empty' for clear the value (if 
        not required) and 'a' or '!abort' for aborting.
        
        Raises
        ------
        StopProgram
            When the user aborts the input
        
        Parameters
        ----------
        input_definition : dict
            The definition of the input
        
        Returns
        -------
        <input_definition["datatype"]> or None
            Returns the value entered by the user in the given type, the value 
            is in the defined boudaries or None if the input is optional and
            the user wants to remove it
        """

        self.clear()
        self.printTitle()
        
        empty_command = "x"
        abort_command = "a"
        text = "Please set the {} to ".format(input_definition["label"])

        if isinstance(input_definition["datatype"], (list, tuple)):
            options = list(map(str, input_definition["datatype"]))
            text += human_concat_list(options) + "."

            options_ci = list(map(lambda x: x.lower(), options))
            
            if abort_command in options_ci:
                if "!abort" not in options_ci:
                    abort_command = "!abort"
                else:
                    for i in range(97, 122):
                        abort_command = "!{}".format(chr(i))

                        if (abort_command not in options_ci and
                            abort_command != empty_command):
                            break
            
            if empty_command in options_ci:
                if "!empty" not in options_ci:
                    empty_command = "!empty"
                else:
                    for i in range(97, 122):
                        empty_command = "!{}".format(chr(i))

                        if (empty_command not in options_ci and
                            abort_command != empty_command):
                            break
        
        name = get_datatype_human_text(input_definition["datatype"])

        if name == "text":
            abort_command = "!abort"
            empty_command = "!empty"

        if "min_value" in input_definition and "max_value" in input_definition:
            name += " with {} <= value <= {}".format(
                format_value(
                    input_definition["datatype"], input_definition["min_value"]
                ), 
                format_value(
                    input_definition["datatype"], input_definition["max_value"]
                )
            )
        elif "min_value" in input_definition:
            name += " with value >= {}".format(format_value(
                input_definition["datatype"], input_definition["min_value"]
            ))
        elif "max_value" in input_definition:
            name += " with value <= {}".format(format_value(
                input_definition["datatype"], input_definition["max_value"]
            ))
        
        text += " a {}.".format(name)
        
        if "description" in input_definition:
            description = str(input_definition["description"]).strip()
            if description[-1] not in (".", "?", "!"):
                description += "."

            text += " {}.".format(description)
        
        text += " To abort type '{}'.".format(abort_command)

        if not "required" in input_definition or not input_definition["required"]:
            text += (" To leave the input empty (remove the current value) " + 
                     "type '{}'.").format(empty_command)

        self.print(text)

        val = self.input("{}: ".format(input_definition["label"]))
        if val.lower() == abort_command:
            raise StopProgram
        elif val.lower() == empty_command:
            if (not "required" in input_definition or 
                not input_definition["required"]):
                return None
            else:
                self.error = ("The '{}' is required. You have to put " + 
                              "in something here.").format(input_definition["label"])
                return self._inputValueLoop(input_definition)
        
        try:
            return self._parseValue(input_definition, val)
        except ValueError:
            return self._inputValueLoop(input_definition)
    
    def _parseValue(self, input_definition: dict, val: typing.Any) -> typing.Any:
        """Parse the `val` defined by the `input_definition` so it matches the
        defined criteria.

        The `input_definition` is a dict that supports the following keys:
        - "label": str (required), the name to show to the user
        - "id": str (required), the id that is used in the returned dict
        - "datatype": type, Datatype or list (required), the type, currently 
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
        - "description": str (optional), a description what this value is about

        Raises
        ------
        ValueError
            When the val is None but "required" is True or
            when the "datatype" is a list but the value is not in the list or
            when the value cannot be parsed to the desired type or
            when the value is not in the boundaries
        
        Parameters
        ----------
        input_definition : dict
            The definition of the input
        val : str or any
            The value as the user types it in (as the string representation) or 
            the parsed value
        
        Returns
        -------
        any
            The correct and parsed values in the boundaries (if given)
        """
        if (val is None and "required" in input_definition and 
            input_definition["required"]):
            raise ValueError(("The value is required. You have to fill in " + 
                              "something valid."))
        elif val is not None:
            if isinstance(input_definition["datatype"], (list, tuple)):
                options = list(map(str, input_definition["datatype"]))
                options_ci = list(map(lambda x: x.lower(), options))
                # count how many times the lower case option occurres, if it is
                # more than once, the case matters
                options_ci_max_count = max(map(lambda x: options_ci.count(x), 
                                               options_ci))

                if options_ci_max_count > 1:
                    case_insensitive = False
                else:
                    case_insensitive = True

                if (not isinstance(val, str) or 
                    (case_insensitive and val.lower() not in options_ci) or 
                    (not case_insensitive and val not in options)):
                    raise ValueError(("The value has to be one of the " + 
                                      "following: {}").format(human_concat_list(options)))
                elif case_insensitive:
                    index = options_ci.index(val.lower())
                    val = options[index]
            elif input_definition["datatype"] == bool:
                if isinstance(val, bool):
                    return val
                elif (isinstance(val, str) and 
                      val.lower() in ("yes", "y", "true", "t", "on")):
                    val = True
                elif (isinstance(val, str) and 
                      val.lower() in ("no", "n", "false", "f", "off")):
                    val = False
                else:
                    raise ValueError(("Please use 'yes', 'y', 'true', 't' " + 
                                      "or 'on' to indicate a true boolean, " + 
                                      "use 'no', 'n', 'false', 'f' or 'off' " + 
                                      "to represent a false (case insensitive)"))
            elif callable(input_definition["datatype"]):
                try:
                    val = input_definition["datatype"](val)
                except ValueError:
                    raise ValueError(("The value '{}' could not be " + 
                                      "converted to a '{}'. Please type in " + 
                                      "a correct value.").format(
                                        val, 
                                        get_datatype_human_text(
                                            input_definition["datatype"]
                                        )
                                    ))

            if "min_value" in input_definition:
                try:
                    if val < input_definition["min_value"]:
                        raise ValueError(("The value must be greater than " + 
                                          " or equal to {}.").format(
                                            input_definition["min_value"]
                                        ))
                except TypeError:
                    # < operator is not supported
                    pass

            if "max_value" in input_definition:
                try:
                    if val > input_definition["max_value"]:
                        raise ValueError(("The value must be lesser than or " + 
                                          "equal to {}.").format(
                                              input_definition["max_value"]
                                        ))
                except TypeError:
                    # < operator is not supported
                    pass
        
        return val