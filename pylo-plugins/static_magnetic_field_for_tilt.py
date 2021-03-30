import math
import pylo

class StaticMagneticFieldForTilt(pylo.Device):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.init_event_id = "static_magnetic_field_init"
        self.modify_step_event_id = "static_magnetic_field_modify_step"
        self.clearEvents()
        pylo.init_ready[self.init_event_id] = self.initialize
        pylo.before_approach[self.modify_step_event_id] = self.modifyStep

        self._logger = pylo.logginglib.get_logger(self)
        self.hint_shown = False
    
    def __del__(self) -> None:
        self.clearEvents()
    
    def clearEvents(self) -> None:
        """Clear the events from the bound functions"""
        if self.init_event_id in pylo.init_ready:
            del pylo.init_ready[self.init_event_id]
        if self.modify_step_event_id in pylo.before_approach:
            del pylo.before_approach[self.modify_step_event_id]
    
    def initialize(self, controller, *args, **kwargs) -> None:
        """Initialize the plugin."""
        # define the configuration options again, this time the contorller
        # is known and therefore options can be generated
        StaticMagneticFieldForTilt.defineConfigurationOptions(
            controller.configuration, self.config_group_name, 
            self.config_defaults, controller=controller)
        self.hint_shown = False
    
    def getMeasurementVariableIdByName(self, controller: pylo.Controller, 
                                       name: str) -> str:
        """Get the measurement variable id from the given measurement variable
        `name´.

        Raises
        ------
        KeyError
            When the `name` is not found

        Parameters
        ----------
        controller : pylo.Controller
            The controller
        name : str
            The measurement variable name
        
        Returns
        -------
        str
            The measurement variable id
        """
        for var in controller.microscope.supported_measurement_variables:
            if ((var.has_calibration and var.calibrated_name == name) or 
                var.name == name):
                return var.unique_id
        
        raise KeyError(("Could not find a measurement variable with the " + 
                       "name '{}'.").format(name))
    
    def modifyStep(self, controller: pylo.Controller, *args, **kwargs):
        """Modify the step to keep a constant field."""

        if self.hint_shown:
            return

        try:
            tilt_name = controller.configuration.getValue(self.config_group_name, 
                                                        "correct-variable")
        except KeyError:
            return
        
        try:
            tilt_id = self.getMeasurementVariableIdByName(controller, tilt_name)
        except KeyError:
            return
        
        try:
            field_name = controller.configuration.getValue(self.config_group_name, 
                                                        "magnetic-field")
        except KeyError:
            return
        try:
            field_id = self.getMeasurementVariableIdByName(controller, field_name)
        except KeyError:
            if not self.hint_shown:
                self.hint_shown = True
                controller.view.showHint("The magnetic field cannot be kept " + 
                                         "constant because the magnetic field " + 
                                         "measurement variable is not set. " + 
                                         "The tilt correction plugin is now " + 
                                         "switched off.")
            return
        
        constant = controller.configuration.getValue(self.config_group_name,
                                                     "keep-constant")
        in_deg = controller.configuration.getValue(self.config_group_name,
                                                   "tilt-in-degree",
                                                   datatype=bool)

        pylo.logginglib.log_debug(self._logger, ("Preparing to correct H-field " + 
                                                 "to keep it constant. Found " + 
                                                 "tilt id '{}' and field id " + 
                                                 "'{}', '{}'-field should be " + 
                                                 "kept constant and tilt is " + 
                                                 "{}measured in degrees").format(
                                                     tilt_id, field_id, 
                                                     constant, "" if in_deg else "not "))

        if (tilt_id in controller.measurement.current_step and 
            field_id in controller.measurement.current_step and
            isinstance(controller.measurement.current_step[tilt_id], (int, float)) and 
            isinstance(controller.measurement.current_step[field_id], (int, float))):
            tilt = controller.measurement.current_step[tilt_id]
            field = controller.measurement.current_step[field_id]

            if in_deg:
                calc = "[rad({})".format(tilt)
                tilt = math.radians(tilt)
                calc += "={}]".format(tilt)
            else:
                calc = "{}".format(tilt)
            
            if constant == "In-plane":
                controller.measurement.current_step[field_id] = field / math.sin(tilt)
                calc = "sin({})".format(calc)
            elif constant == "Out-of-plane":
                controller.measurement.current_step[field_id] = field / math.cos(tilt)
                calc = "cos({})".format(calc)
            
            pylo.logginglib.log_debug(self._logger, ("Changing '{}' to new " + 
                                                     "value '{}' = {} / {}").format(
                                                         field_id, 
                                                         controller.measurement.current_step[field_id],
                                                         field, calc))
    
    @staticmethod
    def defineConfigurationOptions(configuration, group, defaults, *args, **kwargs):
        if ("controller" in kwargs and 
            isinstance(kwargs["controller"], pylo.Controller)):
            field_type = [v.calibrated_name 
                          if v.has_calibration and v.calibrated_name is not None 
                          else v.name for v 
                          in kwargs["controller"].microscope.supported_measurement_variables]
            correction_type = field_type.copy()

            field_type.insert(0, "Please select...")
            correction_type.insert(0, "Off")

            field_type = pylo.Datatype.options(field_type)
            correction_type = pylo.Datatype.options(correction_type)
        else:
            field_type = str
            correction_type = str
        
        configuration.addConfigurationOption(group, "correct-variable", 
            datatype=correction_type, 
            description=("The tilt measurement variable id to correct. "+ 
                         "Use 'Off' to prevent tilt correction"))
        
        configuration.addConfigurationOption(group, "magnetic-field", 
            datatype=field_type, 
            description=("The magnetic field measurement variable id. "+ 
                         "If the 'correct-variable' is 'Off', this value is " + 
                         "ignored."))
        
        configuration.addConfigurationOption(group, "keep-constant", 
            datatype=pylo.Datatype.options(("In-plane", "Out-of-plane")), 
            description=("The magnetic field to keep constant. Ignored if " + 
                         "'correct-variable' is 'Off'."))
        
        configuration.addConfigurationOption(group, "tilt-in-degree", 
            datatype=bool, default_value=True,
            description=("Whether the tilt (the value of the measurement " + 
                         "variable with the id of the 'correct-variable') is " + 
                         "measured in degree (True) or in radians (False). " + 
                         "Ignored if 'correct-variable' is 'Off'."))