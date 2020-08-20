import os
import typing

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
    # raise RuntimeError("This class can onle be used inside Digital Micrograph.")
    pass

from .datatype import Datatype
from .stop_program import StopProgram
from .abstract_view import AbstractView
from .pylodmlib import executeDMScript

class DMView(AbstractView):
    def __init__(self) -> None:
        """Get the view object."""
        super().__init__()

        self._rel_path = os.path.dirname(__file__)
    
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
        path = os.path.join(self._rel_path, "dm_view_series_dialog.s")
        sync_vars = {"start": "TagGroup", "series": "TagGroup"}
        libs = (os.path.join(self._rel_path, "pylolib.s"), )
        script_prefix = ["TagGroup m_vars = NewTagList();", "TagGroup tg;", 
                         "number index"]
        
        var_keys = ("unique_id", "name", "unit", "min_value", "max_value",
                    "start", "end", "step")
        for var in controller.microscope.supported_measurement_variables:
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
                        val = "{:.4}".format(abs(var.min_value - var.max_value) / 10)
                else:
                    val = getattr(var, name)
                
                if val == None:
                    val = ""

                if (name in ("start", "step", "end", "min_value", "max_value") and
                    val != ""):
                    script_prefix += [
                        "index = tg.TagGroupCreateNewLabeledTag(\"{}\");".format(name),
                        "tg.TagGroupSetIndexedTagAsNumber(index, {});".format(val)
                    ]

                    if (var.format != None and hasattr(var.format, "format") and 
                        callable(var.format.format)):
                        script_prefix += [
                            "index = tg.TagGroupCreateNewLabeledTag(\"formatted_{}\");".format(name),
                            "tg.TagGroupSetIndexedTagAsString(index, \"{}\");".format(var.format.format(val))
                        ]
                else:
                    script_prefix += [
                        "index = tg.TagGroupCreateNewLabeledTag(\"{}\");".format(name),
                        "tg.TagGroupSetIndexedTagAsString(index, \"{}\");".format(val)
                    ]
            
            if var.format != None and hasattr(var.format, "name"):
                script_prefix += [
                    "index = tg.TagGroupCreateNewLabeledTag(\"format\");",
                    "tg.TagGroupSetIndexedTagAsString(index, \"{}\");".format(var.format.name)
                ]
            
            script_prefix.append("m_vars.TagGroupInsertTagAsTagGroup(infinity(), tg);")
        
        script_prefix = "\n".join(script_prefix)

        start = None
        series = None

        # shows the dialog (as a dm-script dialog) in dm_view_series_dialog.s
        # and sets the start and series variables
        with executeDMScript(path, sync_vars, libs, script_prefix) as script:
            # get the start tag group
            try:
                start_tg = script["start"]
            except KeyError:
                start_tg = None
            
            if start_tg != None and start_tg.IsValid():
                start = {}

                for var in controller.microscope.supported_measurement_variables:
                    if start_tg.DoesTagExist(var.unique_id):
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
            
            if series_tg != None and series_tg.IsValid():
                # convert the series tag group to a dict
                series = {}
                series_act = series
                keys = ("start", "end", "step-width")
                safety_counter = 0
                while series_act != None and safety_counter < 1000:
                    if "variable" not in series_act:
                        try:
                            var = controller.microscope.getMeasurementVariableById(series_act["variable"])
                        except KeyError:
                            var = None
                    
                    if var == None:
                        # the current variable is invalid, stop parsing
                        series_act = None
                        break
                        
                    for k in keys:
                        # go through start, end and step-width and save the 
                        # values
                        if series_tg.DoesTagExist(k):
                            s, v = series_tg.GetTagAsString(k)

                            if s:
                                # convert value from formatted to numeric value
                                if isinstance(var.format, Datatype):
                                    v = var.format.parse(v)
                                
                                series_act[k] = var.ensureUncalibratedValue(v)
                    
                    # check if there is an on-each-point tag group
                    if series_tg.DoesTagExist("on-each-point"):
                        series_act["on-each-point"] = {}
                        series_act = series_act["on-each-point"]
                    else:
                        series_act = None
                        break
                    
                    safety_counter += 1
        
        if start == None or len(start) == 0 or series == None or len(series) == 0:
            raise StopProgram
        else:
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
        path = os.path.join(self._rel_path, "dm_view_configuration_dialog.s")
        sync_vars = {"configuration": "TagGroup"}
        libs = (os.path.join(self._rel_path, "pylolib.s"), )

        configuration = None

        # shows the dialog (as a dm-script dialog) in dm_view_series_dialog.s
        # and sets the start and series variables
        with executeDMScript(path, sync_vars, libs) as script:
            pass

        if configuration == None or len(configuration) == 0:
            raise StopProgram
        else:
            return configuration