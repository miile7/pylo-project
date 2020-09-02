import os
import sys
import typing
import traceback

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
    DM = None

from .datatype import Datatype
from .stop_program import StopProgram
from .abstract_view import AskInput
from .abstract_view import AbstractView
from .abstract_configuration import AbstractConfiguration

from .pylolib import get_datatype_name

if DM is not None:
    # for development only, execdmscript is another module that is developed
    # separately
    try:
        import dev_constants

        if hasattr(dev_constants, "execdmscript_path"):
            if not dev_constants.execdmscript_path in sys.path:
                sys.path.insert(0, dev_constants.execdmscript_path)
            
            from execdmscript import exec_dmscript
    except:
        from .execdmscript import exec_dmscript
else:
    def exec_dmscript(*args, **kwargs):
        raise RuntimeError("This execdmscript can only be imported inside " + 
                           "the Digital Micrograph program by Gatan.")

class DMView(AbstractView):
    def __init__(self) -> None:
        """Get the view object."""
        if DM == None:
            raise RuntimeError("This class can only be used inside the " + 
                               "Digital Micrograph program by Gatan.")
            
        super().__init__()

        self._rel_path = os.path.dirname(__file__)

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
        with exec_dmscript("showAlert(msg, 1);", setvars={"msg": hint}):
            pass

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
        msg = ""
        if isinstance(error, Exception):
            try:
                msg = type(error).__name__
            except:
                pass
        
        if msg == "":
            msg = "Error"
            
        msg += ": " + str(error)

        print(msg)
        print("  Fix:", how_to_fix)

        if isinstance(error, Exception):
            traceback.print_exc()

        if isinstance(how_to_fix, str) and how_to_fix != "":
            msg += "\n\nPossible Fix:\n{}".format(how_to_fix)

        with exec_dmscript("showAlert(msg, 0);", setvars={"msg": msg}):
            pass
    
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

        if not "text" in kwargs:
            if len(inputs) > 1:
                kwargs["text"] = "Please enter the following values."
            else:
                kwargs["text"] = "Please enter the following value."

        for i, input_definition in enumerate(inputs):
            if "datatype" in input_definition:
                if not isinstance(input_definition["datatype"], str):
                    if hasattr(input_definition["datatype"], "name"):
                        inputs[i]["datatype"] = input_definition["datatype"].name
                    elif hasattr(input_definition["datatype"], "__name__"):
                        inputs[i]["datatype"] = input_definition["datatype"].__name__
                    else:
                        inputs[i]["datatype"] = str(input_definition["datatype"])

        rv = {
            "values": list
        }
        sv = {
            "ask_vals": inputs,
            "message": kwargs["text"]
        }
        
        path = os.path.join(self._rel_path, "dm_view_ask_for_dialog.s")
        with exec_dmscript(path, readvars=rv, setvars=sv, debug=False) as script:
            values = script["values"]

            if len(values) == len(inputs):
                return values
            
        return None
        
    
    def showCreateMeasurement(self, controller: "Controller") -> typing.Tuple[dict, dict]:
        """Show the dialog for creating a measurement.

        Raises
        ------
        StopProgram
            When the user clicks the cancel button.
        RuntimeError
            When the dialog returns unparsable values
        
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
        start, series, config = self._showDialog(
            controller.microscope.supported_measurement_variables,
            controller.configuration,
            0b10 | 0b01
        )

        if start is None or series is None:
            if start is None and series is None:
                raise RuntimeError("Neither the start nor the series could " + 
                                   "be created from the dialogs values.")
            elif start is None:
                raise RuntimeError("The start could not be created from " + 
                                   "the dialogs values.")
            else:
                raise RuntimeError("The series could not be created from " + 
                                   "the dialogs values.")

        return start, series
    
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
        RuntimeError
            When the dialog returns unparsable values
        
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

        start, series, config = self._showDialog(
            None,
            configuration,
            0b01
        )

        if config is None:
            raise RuntimeError("Could not create the configuration from " + 
                               "the dialogs values.")

        return config
    
    def _showDialog(self, 
                    measurement_variables: typing.Optional[typing.Union[list, dict]]=None, 
                    configuration: typing.Optional[AbstractConfiguration]=None, 
                    dialog_type: typing.Optional[int]=0b11):
        """Show the dm-script dialog.

        Parameters
        ----------
        dialog_type : int, optional
            Define which dialog to show, use
            - `0b01` for showing the configuration dialog
            - `0b10` for showing the series dialog
            - `0b01 | 0b10 = 0b11` for showing the series dialog but the user 
              can switch to the configuration dialog and back
        """

        path = os.path.join(self._rel_path, "dm_view_dialog.s")
        sync_vars = {"start": dict, 
                     "series": dict, 
                     "configuration": dict, 
                     "success": bool}
        libs = (os.path.join(self._rel_path, "pylolib.s"), )

        if (dialog_type & 0b01) > 0 and (dialog_type & 0b10) > 0:
            dialog_startup = ""
        elif (dialog_type & 0b01) > 0:
            dialog_startup = "configuration"
        else:
            dialog_startup = "series"
        
        if isinstance(measurement_variables, list):
            m_vars = {}
            for var in measurement_variables:
                m_vars[var.unique_id] = var
            measurement_variables = m_vars

        m_vars = []
        
        # add all measurement variables if there are some
        if isinstance(measurement_variables, dict):
            var_keys = ("unique_id", "name", "unit", "min_value", "max_value",
                        "start", "end", "step")
            num_keys = ("start", "step", "end", "min_value", "max_value")
            for var in measurement_variables.values():
                m_var = {}

                for name in var_keys:
                    if name == "start":
                        if var.min_value == None:
                            val = 0
                        else:
                            val = var.min_value
                    elif name == "end":
                        if var.max_value == None:
                            val = 100
                        else:
                            val = var.max_value
                    elif name == "step":
                        if (var.min_value == None or var.max_value == None or 
                            var.min_value == var.max_value):
                            val = 1
                        else:
                            val = "{:.4}".format(
                                abs(var.min_value - var.max_value) / 10
                            )
                    else:
                        val = getattr(var, name)
                    
                    if val == None:
                        val = ""
                    elif not isinstance(val, (bool, str, float, int)):
                        val = str(val)
                    
                    m_var[name] = val

                    if name in num_keys and val != "":
                        if (var.format != None and var.format != str and 
                            hasattr(var.format, "format") and 
                            callable(var.format.format)):
                            m_var["formatted_{}".format(name)] = (
                                var.format.format(val)
                            )
                
                if var.format != None:
                    m_var["format"] = get_datatype_name(var.format)
                
                m_vars.append(m_var)
        
        config_vars = {}
        if isinstance(configuration, AbstractConfiguration):
            for group in configuration.getGroups():
                if (not group in config_vars or not 
                    isinstance(config_vars[group], dict)):
                    config_vars[group] = {}

                for key in configuration.getKeys(group):
                    try:
                        val = configuration.getValue(group, key)
                    except KeyError:
                        val = ""
                    
                    var_type = configuration.getDatatype(group, key)
                    var_type_name = get_datatype_name(var_type)

                    if (var_type != str and hasattr(var_type, "format") and 
                        callable(var_type.format)):
                        val = var_type.format(val)
                    
                    try:
                        default_value = configuration.getDefault(group, key)
                    except KeyError:
                        default_value = ""
                    
                    try:
                        description = configuration.getDescription(group, key)
                    except KeyError:
                        description = ""
                    
                    config_vars[group][key] = {
                        "value": val,
                        "default_value": default_value,
                        "datatype": var_type_name,
                        "description": str(description),
                        "ask_if_not_present": bool(configuration.getAskIfNotPresent(group, key)),
                        "restart_required": bool(configuration.getRestartRequired(group, key)),
                    }
        
        variables = {
            "m_vars": m_vars,
            "config_vars": config_vars,
            "dialog_startup": dialog_startup
        }
        start = None
        series = None
        config = None
        success = None

        # shows the dialog (as a dm-script dialog) in dm_view_series_dialog.s
        # and sets the start and series variables
        with exec_dmscript(*libs, path, readvars=sync_vars, setvars=variables) as script:
            try:
                success = bool(script["success"])
            except KeyError:
                success = False

            if isinstance(measurement_variables, dict):
                try:
                    start = script["start"]
                except KeyError:
                    start = None
                
                if start is not None:
                    start, errors = self.parseStart(
                        measurement_variables, start, add_defaults=False,
                        parse=True, uncalibrate=True
                    )

            if isinstance(measurement_variables, dict):
                try:
                    series = script["series"]
                except KeyError:
                    series = None
                
                if series is not None:
                    series, errors = self.parseSeries(
                        measurement_variables, series, add_defaults=False,
                        parse=True, uncalibrate=True
                    )

            try:
                config = script["configuration"]
            except KeyError:
                config = None
        
        if success and ((start is not None and series is not None) or 
           config is not None):
            return start, series, config
        else:
            raise StopProgram
        
