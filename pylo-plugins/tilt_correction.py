import math
import logging

import pylo

tilt_corrector = None
def create_tilt_corrector(controller):
    global tilt_corrector
    tilt_corrector = TiltCorrection(controller)

    if tilt_corrector.reset not in pylo.events.series_ready:
        pylo.events.series_ready.append(tilt_corrector.reset)

    if tilt_corrector.correctTilts not in pylo.events.before_record:
        pylo.events.before_record.append(tilt_corrector.correctTilts)
    
if create_tilt_corrector not in pylo.events.init_ready:
    pylo.events.init_ready.append(create_tilt_corrector)

class TiltCorrection:
    def __init__(self, controller):
        """Create a new oject"""

        self.controller = controller

        # for debugging
        self.logger = pylo.logginglib.get_logger(self)

        self.config_name_general = "tilt-correction"
        self.tilt_directions = ("x", "y")

        self.correction_types = ("Off", "Automatic", "Manual", "Automatic+Manual")
        self.measurememt_variable_ids = list(map(lambda x: x.unique_id,
                                            self.controller.microscope.supported_measurement_variables))
        
        self.tilt_cache_values = {}
        for d in self.tilt_directions:
            self.tilt_cache_values[d] = {}

        self.defineConfigurationOptions()
    
    def _getTiltConfigName(self, direction):
        return "{}-{}".format(self.config_name_general, direction)

    def defineConfigurationOptions(self, *args, **kwargs):
        """Define the configuration options for the tilt correction before the 
        program loop is started.
        """

        pylo.logginglib.log_debug(self.logger, ("Defining configuration " + 
                                                "options for tilt correction "+ 
                                                "plugin"))

        for d in self.tilt_directions:
            n = self._getTiltConfigName(d)

            self.controller.configuration.addConfigurationOption(
                n, "correction-type", 
                datatype=pylo.Datatype.options(self.correction_types), 
                default_value=self.correction_types[0], 
                description=("Enable or disable the tilt correction for " + 
                             "tilts in the {} direction.\n\n" + 
                             "Use off for no correction. Use Automatic for " + 
                             "an automatic correction. Use Manual for a " + 
                             "dialog that will show up and pause the " + 
                             "measurement until the correction is done " + 
                             "manually. Use Automatic+Manual to do the " + 
                             "automatic correction and then show the dialog " + 
                             "to allow manual interaction.").format(d))
            
            self.controller.configuration.addConfigurationOption(
                n, "tilt-id", 
                datatype=pylo.Datatype.options(list(self.measurememt_variable_ids)), 
                description=("The {} tilt measurement variable id. This " + 
                             "variable is used to tilt in the {} direction. " + 
                             "If this is not given or invalid, the correction " + 
                             "cannot be done automatically.").format(d, d))

            for sd in ("x", "y"):
                self.controller.configuration.addConfigurationOption(
                    n, "stage-{}-variable-id".format(sd), 
                    datatype=pylo.Datatype.options(list(self.measurememt_variable_ids)), 
                    description=("The id of the measurement variable to " + 
                                "modify the {} value of the stage. Ignored for " + 
                                "manual correction.").format(sd))
                
                self.controller.configuration.addConfigurationOption(
                    n, "stage-{}".format(sd), datatype=float, default_value=0,
                    description=("The stage correction in {sd} direction after " + 
                                 "every tilt step in the stage units. Ignored " + 
                                 "in manual mode.\n\n" + 
                                 "The given value here is the distance from " + 
                                 "the feature on the specimen to surveil to " + 
                                 "the rotational center. The distance the " + 
                                 "stage is moved by {sd}(a)=l_{sd} cos(a) from " + 
                                 "the initial point (where a=0°).\n\n" + 
                                 "l_{sd} easily be calculated by using two " + 
                                 "reference angles with the corresponding {sd} " + 
                                 "translation. " + 
                                # this is just wrong
                                #  "For a rough calibration you " + 
                                #  "can tilt the sample by 1° in {d} direction " + 
                                #  "and measure the moved horizontal distance " + 
                                #  "between the two images. Since cos(0°)=1 and " + 
                                #  "cos(1°)~1 this is good enough for " + 
                                #  "most of the lorentz images."
                                ""
                                 ).format(sd=sd, d=d))

    def reset(self, *args, **kwargs):
        """Check if there is a tilt series done when the series is ready."""

        pylo.logginglib.log_debug(self.logger, ("Checking if the current " + 
                                                "series contains tilts."))
        self.tilt_cache_values = {}
        for d in self.tilt_directions:
            self.tilt_cache_values[d] = {}
        
        if isinstance(self.controller.measurement.steps, pylo.MeasurementSteps):
            # measurement steps object contains a set of all used variables for 
            # direct access
            iterator = self.controller.measurement.steps.series_variables
        else:
            # use a map in a normal list of dicts
            iterator = map(lambda s: s["variable"], 
                           self.controller.measurement.steps)
        
        for d in self.tilt_directions:
            self.tilt_cache_values[d]["type"] = self.controller.configuration.getValue(
                self._getTiltConfigName(d), "correction-type", datatype=str, 
                default_value=None)
            
            pylo.logginglib.log_info(self.logger, ("Tilt correction " + 
                                                    "in '{}' direction " + 
                                                    "is '{}'").format(d,
                                                    self.tilt_cache_values[d]["type"]))
                                                
            if self.tilt_cache_values[d]["type"] == "Off":
                continue

            self.tilt_cache_values[d]["id"] = self.controller.configuration.getValue(
                self._getTiltConfigName(d), "tilt-id", datatype=str, 
                default_value=None)

            self.tilt_cache_values[d]["present-in-series"] = False

            if self.tilt_cache_values[d]["id"] in iterator:
                pylo.logginglib.log_info(self.logger, ("Found a tilt id '{}' in "+ 
                                                       "the measurement steps, " + 
                                                       "tilt correction for '{}' " + 
                                                       "tilt is available").format(
                                                           self.tilt_cache_values[d]["id"], 
                                                           d))
                self.tilt_cache_values[d]["present-in-series"] = True

            if not self.tilt_cache_values[d]["present-in-series"]:
                pylo.logginglib.log_debug(self.logger, ("Tilt id '{}' is not " + 
                                                        "used in the current " + 
                                                        "series. No tilt " + 
                                                        "correction for the " + 
                                                        "'{}' direction").format(
                                                            self.tilt_cache_values[d]["id"],
                                                            d))

    def correctTilts(self, *args, **kwargs):
        """Realign the stage before every measurement step."""

        for d in self.tilt_directions:
            if (self.tilt_cache_values[d]["type"] != "Off" and 
                self.tilt_cache_values[d]["present-in-series"]):
                try:
                    tilt = self.controller.microscope.getMeasurementVariableValue(
                        self.tilt_cache_values[d]["id"])
                except ValueError:
                    continue
                
                if ("last-value" not in self.tilt_cache_values[d] or 
                    math.isclose(self.tilt_cache_values[d]["last-value"], tilt)):
                    self.tilt_cache_values[d]["last-value"] = tilt
                    pylo.logginglib.log_debug(self.logger, ("Skipping tilt " + 
                                                            "correction in '{}' " + 
                                                            "direction, the " + 
                                                            "tilts did not " + 
                                                            "change since " + 
                                                            "the last step " + 
                                                            "or this is the " + 
                                                            "first step."))
                    continue
                
                if "Automatic" in self.tilt_cache_values[d]["type"]:
                    for sd in ("x", "y"):
                        stage_key = "stage-{}".format(sd)
                        if not stage_key in self.tilt_cache_values[d]:
                            self.tilt_cache_values[d][stage_key] = self.controller.configuration.getValue(
                                self._getTiltConfigName(d), 
                                "stage-{}-variable-id".format(sd), datatype=str,
                                default_value=None)
                            
                        l_key = "l{}".format(sd)
                        if not l_key in self.tilt_cache_values[d]:
                            self.tilt_cache_values[d][l_key] = self.controller.configuration.getValue(
                                self._getTiltConfigName(d), "stage-{}".format(sd), 
                                datatype=float, default_value=0)
                        
                        if (isinstance(self.tilt_cache_values[d][l_key], (int, float)) and 
                            not math.isclose(self.tilt_cache_values[d][l_key], 0, abs_tol=1e-6) and
                            self.tilt_cache_values[d][stage_key] is not None and
                            self.tilt_cache_values[d][stage_key] != ""):

                            stage_d = (self.tilt_cache_values[d][l_key] * 
                                    (math.cos(math.radians(self.tilt_cache_values[d]["last-value"])) - 
                                     math.cos(math.radians(tilt))))
                            
                            pylo.logginglib.log_debug(self.logger, 
                                ("Calculating stage difference by " + 
                                 "d = {} * (cos(a) - cos(b)) with " + 
                                 "{}='{}', a='{}' and b='{}' => d='{}'").format(
                                     l_key, l_key, 
                                     self.tilt_cache_values[d][l_key],
                                     self.tilt_cache_values[d]["last-value"],
                                     tilt, stage_d))

                            try:
                                stage_value = self.controller.microscope.getMeasurementVariableValue(
                                    self.tilt_cache_values[d][stage_key])
                            except KeyError:
                                # stage variable is invalid, disable for future
                                # runs
                                self.tilt_cache_values[d][stage_key] = None
                                self.tilt_cache_values[d][l_key] = 0
                                continue

                            try:
                                self.controller.microscope.setMeasurementVariableValue(
                                    self.tilt_cache_values[d][stage_key], 
                                    stage_value + stage_d)
                                pylo.logginglib.log_info(self.logger, 
                                    ("Correcting '{}' tilt in '{}' direction, " + 
                                    "by moving stage by '{}' (target value " + 
                                    "is '{}').").format(d, sd, stage_d,
                                        stage_value + stage_d))
                            except ValueError as e:
                                pylo.logginglib.log_error(e)
                        else:
                            pylo.logginglib.log_debug(self.logger, 
                                ("Skipping '{}' tilt correction in '{}' direction, " + 
                                 "the either the stage variable id '{}' or " + 
                                 "the stage correction factor '{}' is " + 
                                 "invalid.").format(d, sd, 
                                    self.tilt_cache_values[d][stage_key], 
                                    self.tilt_cache_values[d][l_key]))

                if "Manual" in self.tilt_cache_values[d]["type"]:
                    self.controller.view.showHint("Pausing for tilt " + 
                                                  "correction.\n\n" + 
                                                  "Please move the stage " + 
                                                  "to compensate translation "+ 
                                                  "caused by tilting. Press " + 
                                                  "'Ok' if you want to " + 
                                                  "continue.")
                    pylo.logginglib.log_debug(self.logger, ("Showing correction " + 
                                                            "tilt dialog."))
                
                self.tilt_cache_values[d]["last-value"] = tilt