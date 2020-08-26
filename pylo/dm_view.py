import os
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
from .abstract_view import AbstractView
from .abstract_configuration import AbstractConfiguration

from .pylolib import get_datatype_name

if DM is not None:
    from .pylodmlib import executeDMScript
else:
    def executeDMScript(*args, **kwargs):
        raise RuntimeError("This pylodmlib can only be imported inside the " + 
                           "Digital Micrograph program by Gatan.")

class DMView(AbstractView):
    def __init__(self) -> None:
        """Get the view object."""
        if DM == None:
            raise RuntimeError("This class can only be used inside the " + 
                               "Digital Micrograph program by Gatan.")
            
        super().__init__()

        self._rel_path = os.path.dirname(__file__)

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
        print("Error:", error)
        if isinstance(error, Exception):
            traceback.print_exc()
        print("  Fix:", how_to_fix)
        # script = "showAlert(\"{}\", 0);".format(msg)
    
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
        start, series, config = self._showDialog(
            controller.microscope.supported_measurement_variables,
            controller.configuration,
            0b10 | 0b01
        )

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

        return config
    
    def _escapeCodeString(self, string: str) -> str:
        """Escape all characters that make problems when they are in a
        dm-script string.

        Parameters
        ----------
        string : str
            The string to escape
        
        Returns
        -------
        str
            The escaped string
        """
        return (str(string)
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\t", "\\t"))
    
    def _showDialog(self, measurement_variables: typing.Optional[list]=None, 
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
        sync_vars = {"start": "TagGroup", "series": "TagGroup", 
                     "configuration": "TagGroup", "success": "Number"}
        libs = (os.path.join(self._rel_path, "pylolib.s"), )

        if (dialog_type & 0b01) > 0 and (dialog_type & 0b10) > 0:
            dialog_str_type = ""
        elif (dialog_type & 0b01) > 0:
            dialog_str_type = "configuration"
        else:
            dialog_str_type = "series"

        script_prefix = [
            "TagGroup m_vars = NewTagList();", 
            "TagGroup config_vars = NewTagGroup();", 
            "TagGroup tg;", 
            "TagGroup tg2;", 
            "number index;",
            "string dialog_startup = \"{}\";".format(dialog_str_type)
        ]
        
        # add all measurement variables if there are some
        if isinstance(measurement_variables, list):
            var_keys = ("unique_id", "name", "unit", "min_value", "max_value",
                        "start", "end", "step")
            num_keys = ("start", "step", "end", "min_value", "max_value")
            for var in measurement_variables:
                script_prefix.append("tg = NewTagGroup();")

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

                    if name in num_keys and val != "":
                        script_prefix += [
                            "index = tg.TagGroupCreateNewLabeledTag(\"{}\");".format(
                                self._escapeCodeString(name)
                            ),
                            "tg.TagGroupSetIndexedTagAsNumber(index, {});".format(
                                self._escapeCodeString(val)
                            )
                        ]

                        if (var.format != None and var.format != str and 
                            hasattr(var.format, "format") and 
                            callable(var.format.format)):
                            formatted_val = self._escapeCodeString(
                                var.format.format(val)
                            )
                            script_prefix += [
                                "index = tg.TagGroupCreateNewLabeledTag(\"formatted_{}\");".format(name),
                                "tg.TagGroupSetIndexedTagAsString(index, \"{}\");".format(formatted_val)
                            ]
                    else:
                        script_prefix += [
                            "index = tg.TagGroupCreateNewLabeledTag(\"{}\");".format(name),
                            "tg.TagGroupSetIndexedTagAsString(index, \"{}\");".format(
                                self._escapeCodeString(val)
                            )
                        ]
                
                if var.format != None:
                    script_prefix += [
                        "index = tg.TagGroupCreateNewLabeledTag(\"format\");",
                        "tg.TagGroupSetIndexedTagAsString(index, \"{}\");".format(get_datatype_name(var.format))
                    ]
                
                script_prefix.append("m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);")
        
        if isinstance(configuration, AbstractConfiguration):
            for group in configuration.getGroups():
                script_prefix.append("tg = NewTagGroup();")

                for key in configuration.getKeys(group):
                    script_prefix += [
                        "tg2 = NewTagGroup();"
                        "index = tg2.TagGroupCreateNewLabeledTag(\"value\");"
                    ]

                    try:
                        val = configuration.getValue(group, key)
                    except KeyError:
                        val = ""
                    var_type = configuration.getDatatype(group, key)
                    var_type_name = get_datatype_name(var_type)

                    if var_type == int or var_type == float:
                        if val == "":
                            val = 0
                        
                        script_prefix.append(
                            "tg2.TagGroupSetIndexedTagAsNumber(index, {});".format(val)
                        )
                    else:
                        if (var_type != str and hasattr(var_type, "format") and 
                            callable(var_type.format)):
                            val = var_type.format(val)
                        val = self._escapeCodeString(val)
                        
                        script_prefix.append(
                            "tg2.TagGroupSetIndexedTagAsString(index, \"{}\");".format(val)
                        )
                    
                    try:
                        default_value = self._escapeCodeString(
                            configuration.getDefault(group, key)
                        )
                    except KeyError:
                        default_value = ""
                    try:
                        description = self._escapeCodeString(
                            configuration.getDescription(group, key)
                        )
                    except KeyError:
                        description = ""
                        
                    script_prefix += [
                        "index = tg2.TagGroupCreateNewLabeledTag(\"default_value\");",
                        "tg2.TagGroupSetIndexedTagAsString(index, \"{}\");".format(default_value),
                        "index = tg2.TagGroupCreateNewLabeledTag(\"datatype\");",
                        "tg2.TagGroupSetIndexedTagAsString(index, \"{}\");".format(var_type_name),
                        "index = tg2.TagGroupCreateNewLabeledTag(\"description\");",
                        "tg2.TagGroupSetIndexedTagAsString(index, \"{}\");".format(description),
                        "index = tg2.TagGroupCreateNewLabeledTag(\"ask_if_not_present\");",
                        "tg2.TagGroupSetIndexedTagAsBoolean(index, {});".format(int(configuration.getAskIfNotPresent(group, key))),
                        "index = tg2.TagGroupCreateNewLabeledTag(\"restart_required\");",
                        "tg2.TagGroupSetIndexedTagAsBoolean(index, {});".format(int(configuration.getRestartRequired(group, key))),
                        "index = tg.TagGroupCreateNewLabeledTag(\"{}\");".format(self._escapeCodeString(key)),
                        "tg.TagGroupSetIndexedTagAsTagGroup(index, tg2);"
                    ]
                
                script_prefix += [
                    "index = config_vars.TagGroupCreateNewLabeledTag(\"{}\");".format(group),
                    "config_vars.TagGroupSetIndexedTagAsTagGroup(index, tg);"
                ]
        
        script_prefix = "\n".join(script_prefix)

        start = None
        series = None
        config = None
        success = None

        # shows the dialog (as a dm-script dialog) in dm_view_series_dialog.s
        # and sets the start and series variables
        with executeDMScript(path, sync_vars, libs, script_prefix) as script:
            try:
                success = bool(script["success"])
            except KeyError:
                success = False
            
            # get the start tag group
            try:
                start_tg = script["start"]
            except KeyError:
                start_tg = None
            
            if start_tg != None and start_tg.IsValid():
                start = {}

                for var in measurement_variables:
                    s, v = start_tg.GetTagAsString(var.unique_id)

                    if s:
                        # convert value from formatted to numeric value
                        if isinstance(var.format, Datatype):
                            v = var.format.parse(v)
                        
                        start[var.unique_id] = var.ensureUncalibratedValue(v)
            
            # get the series tag group
            try:
                series_tg = script["series"]
            except KeyError:
                series_tg = None
            
            print("{{Debug}} DMView::_showDialog(): script[series]: ", series_tg)
            
            if series_tg != None:
                print("{{Debug}} DMView::_showDialog(): parsing series")
                # convert the series tag group to a dict
                series = {}
                series_act = series
                keys = ("start", "end", "step-width")
                safety_counter = 0
                while series_act != None and safety_counter < 1000:
                    var = None
                    s, unique_id = series_tg.GetTagAsString("variable")
                    print("{{Debug}} DMView::_showDialog(): getting variable: ", s, unique_id)
                    if s:
                        for v in measurement_variables:
                            if v.unique_id == unique_id:
                                var = v
                                break
                    
                    if var == None:
                        # the current variable is invalid, stop parsing
                        series_act = None
                        print("{{Debug}} DMView::_showDialog(): couldn't find variable")
                        break
                        
                    for k in keys:
                        # go through start, end and step-width and save the 
                        # values
                        s, v = series_tg.GetTagAsString(k)
                        print("{{Debug}} DMView::_showDialog(): for key", k, "getting value", s, v)

                        if s:
                            # convert value from formatted to numeric value
                            if isinstance(var.format, Datatype):
                                v = var.format.parse(v)
                            
                            series_act[k] = var.ensureUncalibratedValue(v)
                            print("{{Debug}} DMView::_showDialog(): series_act[k] is now", series_act[k])
                    
                    # check if there is an on-each-point tag group
                    s, v = series_tg.GetTagAsTagGroup("on-each-point")
                    if s:
                        series_act["on-each-point"] = {}
                        series_tg = v
                    else:
                        series_act = None
                        break
                    
                    safety_counter += 1
            else:
                print("{{Debug}} DMView::_showDialog(): series_tg is not valid or None", series_tg)

            # get the configuration tag group
            try:
                configuration_tg = script["configuration"]
            except KeyError:
                configuration_tg = None
            
            if configuration_tg != None and configuration_tg.IsValid():
                config = {}
                for i in range(configuration_tg.CountTags()):
                    group = configuration_tg.GetTagLabel(i)
                    s, group_tg = configuration_tg.GetTagAsTagGroup(group)

                    if s:
                        for j in range(group_tg.CountTags()):
                            key = group_tg.GetTagLabel(j)

                            s, val = group_tg.GetTagAsString(key)

                            if s:
                                if group not in config:
                                    config[group] = {}
                                
                                try:
                                    dt = configuration.getDatatype(group, key)
                                except KeyError:
                                    dt = str
                                
                                if callable(dt):
                                    val = dt(val)
                                
                                config[group][key] = val
        
        print("{Debug} DMView::_showDialog():", success, start, series, config)

        if success and ((start is not None and series is not None) or 
           config is not None):
            return start, series, config
        else:
            raise StopProgram