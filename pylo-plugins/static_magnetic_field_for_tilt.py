import math
import pylo

class StaticMagneticFieldForTilt(pylo.Device):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.clearEvents()
        pylo.init_ready.append(self.initialize)
        pylo.before_approach.append(self.modifyStep)

        self._logger = pylo.logginglib.get_logger(self)
    
    def __del__(self):
        self.clearEvents()
    
    def clearEvents(self):
        """Clear the events from the bound functions"""
        if self.initialize in pylo.init_ready:
            pylo.init_ready.remove(self.initialize)
        if self.modifyStep in pylo.before_approach:
            pylo.before_approach.remove(self.modifyStep)
    
    def initialize(self, controller, *args, **kwargs):
        """Initialize the plugin."""
        # define the configuration options again, this time the contorller
        # is known and therefore options can be generated
        StaticMagneticFieldForTilt.defineConfigurationOptions(
            controller.configuration, self.config_group_name, 
            self.config_defaults, controller=controller)
    
    def modifyStep(self, controller, *args, **kwargs):
        """Modify the step to keep a constant field."""

        tilt_id = controller.configuration.getValue(self.config_group_name, 
                                                    "correction")
        if tilt_id == "Off":
            return
        
        field_id = controller.configuration.getValue(self.config_group_name, 
                                                     "magnetic-field-id")
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
            field_type = [v.unique_id for v in 
                          kwargs["controller"].microscope.supported_measurement_variables]
            correction_type = field_type.copy()
            correction_type.insert(0, "Off")

            field_type = pylo.Datatype.options(field_type)
            correction_type = pylo.Datatype.options(correction_type)
        else:
            field_type = str
            correction_type = str
        
        configuration.addConfigurationOption(group, "correction", 
            datatype=correction_type, 
            description=("The tilt measurement variable id to correct. "+ 
                         "Use 'Off' to prevent tilt correction"))
        
        configuration.addConfigurationOption(group, "magnetic-field-id", 
            datatype=field_type, 
            description=("The magnetic field measurement variable id. "+ 
                         "If the 'correction' is 'Off', this value is " + 
                         "ignored."))
        
        configuration.addConfigurationOption(group, "keep-constant", 
            datatype=pylo.Datatype.options(("In-plane", "Out-of-plane")), 
            description=("The magnetic field to keep constant. Ignored if " + 
                         "'correction' is 'Off'."))
        
        configuration.addConfigurationOption(group, "tilt-in-degree", 
            datatype=bool, default_value=True,
            description=("Whether the tilt (the value of the measurement " + 
                         "variable with the id of the 'correction') is " + 
                         "measured in degree (True) or in radians (False). " + 
                         "Ignored if 'correction' is 'Off'."))