import math
import logging

import pylo

# for debugging
logger = pylo.logginglib.get_logger("tilt_correction", create_msg=False)

tilt_correction_needed = False
tilt_correction_enabled = None
tilt_correction_config_name = "tilt-correction"

tilt_correction_x = None
tilt_correction_y = None
tilt_correction_tilt_ids = None
tilt_correction_last_tilts = None
tilt_correction_show_dialog = None

def tilt_correction_before_start(controller):
    """Define the configuration options for the tilt correction before the 
    program loop is started.
    """

    pylo.logginglib.log_debug(logger, ("Defining configuration options for " + 
                                       "tilt correction plugin"))

    controller.configuration.addConfigurationOption(
        tilt_correction_config_name, "enabled", datatype=bool, 
        default_value=False, 
        description="Enable or disable the tilt correction")
    
    # not yet implemented
    # controller.configuration.addConfigurationOption(
    #     tilt_correction_config_name, "stage-x", datatype=float, default_value=0,
    #     description=("The stage correction in x direction after every tilt " + 
    #                  "step in the stage units.\n\n" + 
    #                  "The given value here is the distance from the feature " + 
    #                  "to surveil to the rotational center. The distance the " + 
    #                  "stage is moved by x(a)=l_x cos(a) from the initial " + 
    #                  "point (where a=0°).\n\n" + 
    #                  "l_x easily be calculated by using two reference angles " + 
    #                  "with the corresponding x translation. For a rough " + 
    #                  "calibration you can tilt the sample by 1° and measure " + 
    #                  "the moved horizontal distance between the two images. " + 
    #                  "Since cos(0°)=1 and cos(1°)~1 this is good enough for " + 
    #                  "most of the lorentz images."))
    
    # controller.configuration.addConfigurationOption(
    #     tilt_correction_config_name, "stage-y", datatype=float, default_value=0,
    #     description=("The stage correction in y direction after every tilt " + 
    #                  "step in the stage units.\n\n" + 
    #                  "The given value here is the distance from the feature " + 
    #                  "to surveil to the rotational center. The distance the " + 
    #                  "stage is moved by y(a)=l_y cos(a) from the initial " + 
    #                  "point (where a=0°).\n\n" + 
    #                  "l_x easily be calculated by using two reference angles " + 
    #                  "with the corresponding y translation. For a rough " + 
    #                  "calibration you can tilt the sample by 1° and measure " + 
    #                  "the moved vertical distance between the two images. " + 
    #                  "Since cos(0°)=1 and cos(1°)~1 this is good enough for " + 
    #                  "most of the lorentz images."))
    
    controller.configuration.addConfigurationOption(
        tilt_correction_config_name, "show-confirm-dialog", datatype=bool, 
        default_value=True,
        description=("Whehter to show a confirm dialog to correct manually too."))
    
    controller.configuration.addConfigurationOption(
        tilt_correction_config_name, "tilt-ids", datatype=str, 
        default_value="x-tilt,y-tilt,tilt,tilt-x,tilt-y,alpha,beta,stage-tilt",
        description=("Do not change this if you are not sure! The " + 
                     "measurement variable ids that are treated as tilts. " + 
                     "This is needed since the variable names are " + 
                     "not standardized and can be set by the microscope. " + 
                     "Only change this if your microscope supports tilting " + 
                     "but the tilting measurement variable is not one of " + 
                     "the ones listed above. You have to find this out by " + 
                     "looking in the code or by checking the logs.\n\n" + 
                     "The value is a comma separated list of allowed tilt " + 
                     "ids. Try not to remove values, only add them."))

if tilt_correction_before_start not in pylo.events.before_start:
    pylo.events.before_start.append(tilt_correction_before_start)

def tilt_correction_series_ready(controller):
    """Check if there is a tilt series done when the series is ready."""

    global tilt_correction_enabled, tilt_correction_needed, tilt_correction_tilt_ids

    pylo.logginglib.log_debug(logger, ("Checking if tilt correction is " + 
                                       "needed at all"))

    tilt_correction_tilt_ids = controller.configuration.getValue(
        tilt_correction_config_name, "tilt-ids", datatype=str)
    tilt_correction_tilt_ids = tilt_correction_tilt_ids.split(",")

    if isinstance(controller.measurement.steps, pylo.MeasurementSteps):
        # measurement steps object contains a set of all used variables for 
        # direct access
        iterator = controller.measurement.steps.series_variables
    else:
        # use a map in a normal list of dicts
        iterator = map(lambda s: s["variable"], controller.measurement.steps)

    tilt_correction_needed = False
    for variable_id in iterator:
        if variable_id in tilt_correction_tilt_ids:
            pylo.logginglib.log_debug(logger, ("Found a tilt id '{}' in the " + 
                                               "measurement steps, tilt " + 
                                               "correction is available").format(
                                                   variable_id))
            tilt_correction_needed = True
            break

    if not tilt_correction_needed:
        pylo.logginglib.log_debug(logger, ("No tilt id found in the current " + 
                                           "measurement steps, switching off"))
    
    # force checking the settings on the first measurement step, the 
    # configuration may have changed or GMS has cached the variable value
    tilt_correction_enabled = None

if tilt_correction_series_ready not in pylo.events.series_ready:
    pylo.events.series_ready.append(tilt_correction_series_ready)

def tilt_correction_equal_tilts(t1, t2, rel_tol=0, abs_tol=1e-6):
    """Get whether the `t1` and `t2` dicts have the same keys with the same 
    values. Float values are used with the `math.isclose` function with the 
    given absolute and relative tolerance.

    Deep comparism is not supported.

    Parameters
    ----------
    t1, t2 : dict
        The dicts to compare
    rel_tol, abs_tol : float
        The relative and absolute tolerance which are directly passed to the 
        `math.isclose()` function

    Returns
    -------
    bool
        Whether the dicts are close or not
    """

    keys = list(t1.keys()) + list(t2.keys())
    for key in keys:
        if not key in t1 or not key in t2:
            return False
        elif (isinstance(t1[key], (int, float)) and 
              isinstance(t2[key], (int, float))):
            return math.isclose(t1[key], t2[key], rel_tol=rel_tol, 
                                abs_tol=abs_tol)
        else:
            return t1[key] == t2[key]

def tilt_correction_before_record(controller):
    """Realign the stage before every measurement step."""

    global tilt_correction_enabled, tilt_correction_needed, tilt_correction_tilt_ids
    global tilt_correction_x, tilt_correction_y, tilt_correction_show_dialog, tilt_correction_last_tilts

    pylo.logginglib.log_debug(logger, ("Checking if tilt correction is " + 
                                       "needed: '{}'").format(
                                           tilt_correction_needed))

    if tilt_correction_needed:
        # cache all the values to prevent calling the configuration over and 
        # over again
        
        tilts = {}
        for tilt_id in tilt_correction_tilt_ids:
            try:
                v = controller.microscope.getMeasurementVariableValue(tilt_id)
            except ValueError:
                v = None
            
            tilts[tilt_id] = v
        
        if (tilt_correction_last_tilts is None or 
            tilt_correction_equal_tilts(tilt_correction_last_tilts, tilts)):
            pylo.logginglib.log_debug(logger, ("Skipping tilt correction, the " + 
                                               "tilts did not change since " + 
                                               "the last step."))
            tilt_correction_last_tilts = tilts
            return

        if tilt_correction_enabled is None:
            tilt_correction_enabled = controller.configuration.getValue(
                tilt_correction_config_name, "enabled", datatype=bool,
                default_value=False)
            tilt_correction_x = None
            tilt_correction_y = None
            tilt_correction_show_dialog = None
            tilt_correction_last_tilts = None
            pylo.logginglib.log_debug(logger, ("Tilt is enabled in the " + 
                                               "settings: '{}'.".format(
                                                   tilt_correction_enabled)))

        pylo.logginglib.log_debug(logger, ("Checking if tilt correction is " + 
                                           "enabled: '{}'").format(
                                               tilt_correction_enabled))
        
        if tilt_correction_enabled:
            if tilt_correction_x is None:
                tilt_correction_x = controller.configuration.getValue(
                    tilt_correction_config_name, "stage-x", datatype=float,
                    default_value=0)
            
            if tilt_correction_y is None:
                tilt_correction_y = controller.configuration.getValue(
                    tilt_correction_config_name, "stage-y", datatype=float,
                    default_value=0)

            if tilt_correction_show_dialog is None:
                tilt_correction_show_dialog = controller.configuration.getValue(
                    tilt_correction_config_name, "show-confirm-dialog", 
                    datatype=bool, default_value=True)

            if (not math.isclose(tilt_correction_x, 0, rel_tol=0, abs_tol=1e-6) or 
                not math.isclose(tilt_correction_y, 0, rel_tol=0, abs_tol=1e-6)):
                # fix floating point inaccuracy
                pylo.logginglib.log(logger, logging.ERROR, ("The automatic " + 
                                                            "correction is " + 
                                                            "not yet " + 
                                                            "implemented."))
            elif not tilt_correction_show_dialog:
                # stage correction is 0 and no dialog should be shown, so 
                # there is nothing to do
                tilt_correction_enabled = False
                pylo.logginglib.log_info(logger, ("The stage correction is " + 
                                                  "empty for x and y " + 
                                                  "(x: '{}', y: '{}') and " + 
                                                  "a dialog should not be " + 
                                                  "shown ('{}'). Therefore " +
                                                  "there is nothing to do for " + 
                                                  "the tilt correction: " + 
                                                  "Switching off.").format(
                                                      tilt_correction_x,
                                                      tilt_correction_y,
                                                      tilt_correction_show_dialog))
            
            if tilt_correction_show_dialog:
                controller.view.showHint("Pausing for tilt correction.\n\n" + 
                                         "Please realign the stage to " + 
                                         "compensate translation caused by " + 
                                         "tilting. Press 'Ok' if you want to " + 
                                         "continue.")
                pylo.logginglib.log_debug(logger, "Showing correction tilt " + 
                                                  "dialog.")
    
        tilt_correction_last_tilts = tilts
                
if tilt_correction_before_record not in pylo.events.before_record:
    pylo.events.before_record.append(tilt_correction_before_record)