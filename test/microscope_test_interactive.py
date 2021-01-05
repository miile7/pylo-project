import os
import sys
import time
import inspect
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mini_cli
import pylo
import pylo.config
import pylo.microscopes

class DummyConfiguration(pylo.AbstractConfiguration):
    def __init__(self):
        super().__init__()
        self.logging = False
        self.log = []
        self.define_log = []
    
    def getValue(self, group, key, fallback_default=True):
        if self.logging:
            self.log.append((key, group))

        return super().getValue(group, key, fallback_default)
    
    def addConfigurationOption(self, group, key, **kwargs):
        if self.logging:
            self.define_log.append((key, group))

        return super().addConfigurationOption(
            group, key, **kwargs
        )
    
    def loadConfiguration(self):
        pass
    
    def saveConfiguration(self):
        pass

class DummyView(pylo.AbstractView):
    def askFor(self, *inputs):
        ret = []

        for inp in inputs:
            ret.append(input("View::askFor({}):".format(inp)))
    
        return ret

controller = pylo.Controller(DummyView(), DummyConfiguration())

###############################################################################
###                                                                         ###
###         Change only this for testing a different microscope             ###
###                                                                         ###
###############################################################################

microscope_class = pylo.microscopes.PyJEMMicroscope
microscope_args = (controller,)

######################## general test code starts here ########################

mini_cli.maxlen = 79
tabc = 4
tabs = " " * tabc

def print_configuration_options(configuration, groups_and_keys):
    global tabs

    for i, (group, key) in enumerate(groups_and_keys):
        text = "Group '{group}' and key '{key}'"
        add_text = []
        descr_text = ""
        try:
            datatype = configuration.getDatatype(group, key)
            add_text.append("type: {datatype}")
        except KeyError:
            datatype = None

        try:
            default = configuration.getDescription(group, key)
            add_text.append(" default: {default}")
        except KeyError:
            default = None

        try:
            description = configuration.getDescription(group, key)
            descr_text += " -- {description}"
        except KeyError:
            description = None
        
        if len(add_text) > 0:
            add_text = " (" + ", ".join(add_text) + ")"
        else:
            add_text = ""
        
        mini_cli.prnt(("\b\b\b{i}. " + text + add_text + descr_text).format(i=i + 1, 
                       group=group, key=key, datatype=datatype, default=default, 
                       description=description), inset=tabs + " " * 3)

if __name__ == "__main__":
    title = "Interactive test for microscope"
    mini_cli.prnt(title + "\n" + "*" * len(title) + "\n")

    controller.configuration.logging = True
    controller.configuration.log = []
    controller.configuration.define_log = []
    if (hasattr(microscope_class, "defineConfigurationOptions") and
        callable(microscope_class.defineConfigurationOptions)):
        microscope_class.defineConfigurationOptions(controller.configuration)

    microscope = microscope_class(*microscope_args)

    mini_cli.prnt("Your microscope has {} variables: ".format(
        len(microscope.supported_measurement_variables)
    ))
    names = ["{} ({})".format(var.name, var.unique_id) for var in 
             microscope.supported_measurement_variables]
    collen = max([len(n) for n in names])
    for i, var in enumerate(microscope.supported_measurement_variables):
        mini_cli.prnt(("{}. {:" + str(collen) + "} {: d} <= value <= {: d}, " + 
                       "unit: {}").format(i + 1, names[i] + ":", var.min_value, 
                       var.max_value, var.unit), inset=tabs)
    
    if len(controller.configuration.define_log) > 0:
        mini_cli.prnt("")
        mini_cli.prnt(("It defines the following configuration {} values on " + 
               "startup:").format(len(controller.configuration.define_log)))
        print_configuration_options(
            controller.configuration, 
            controller.configuration.define_log
        )
    
    if len(controller.configuration.log) > 0:
        mini_cli.prnt("")
        mini_cli.prnt(("It asks for the following configuration {} values on " + 
               "startup:").format(len(controller.configuration.log)))
        print_configuration_options(
            controller.configuration, 
            controller.configuration.log
        )

    controller.configuration.log = []
    controller.configuration.define_log = []
    controller.configuration.logging = False
    
    mini_cli.prnt("")
    mini_cli.prnt("= " * 3)
    # mini_cli.inpt("Press Enter to start the interactive test")

    test_log = []

    # test setting lorentz mode
    # mini_cli.prnt("")
    # mini_cli.prnt("Setting to lorentz mode...", end=" ")
    # t = time.time()
    # microscope.setInLorentzMode(True)
    # mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

    # s = mini_cli.input_yn("Please confirm: Is the microscope in lorentz mode?", 
    #                       lines_before=0, inset=0, add_inset=tabc)
    # test_log.append(("Switch to lorentz mode", s))
    
    select = None
    logging = False
    current_state = None
    while True:
        controls = {
            "g": "toggling log ({})".format(logging),
            "z": "toggling lorentz mode ({})".format(microscope.getInLorentzMode()),
            "c": "current state test ({})".format("not set" if current_state is None else "set"),
            "s": "setting to safe state",
            "e": "setting to EMERGENCY state"
        }
        variables = []
        for v in microscope.supported_measurement_variables:
            val = microscope.getMeasurementVariableValue(v.unique_id)

            if isinstance(v.format, pylo.Datatype):
                val = v.format.format(val)

            variables.append("{} ({})".format(v.name, val))

        options = list(controls.items()) + [(None, None)] + list(enumerate(variables))
        choices = {
            "q": "q"
        }
        for k in controls:
            choices[k] = k

        select = mini_cli.input_int(
            ("Select what you want to test or enter [q] for quit:\n" + 
            "\n".join(["[{}] for {}".format(i, name) if name is not None else ""
                        for i, name in options])),
            short_text="Number or {" + (", ".join(choices.keys())) + "};",
            min_value=0,
            max_value=len(variables) - 1,
            add_choices=choices
        )

        if isinstance(select, str) and select.lower().strip() == "q":
            break
        elif isinstance(select, str) and select.lower().strip() in controls:
            select = select.lower().strip()

            if select == "g":
                mini_cli.prnt("")
                mini_cli.prnt("Now testing toggling whether to log or not.")
            
                value = mini_cli.input_yn(
                    "Do you want to log the test results?", 
                    lines_before=0, inset=0, add_inset=tabc
                )

                if value:
                    logging = True
                    mini_cli.prnt("Logging is switched on.")
                else:
                    logging = False
                    mini_cli.prnt("Logging is switched off.")
            elif select == "z":
                mini_cli.prnt("")
                mini_cli.prnt("Now testing toggling of the lorentz mode.")
            
                value = mini_cli.input_yn(
                    "Do you want to set the TEM into lorentz mode?",
                    "Activate lorentz mode?", 
                    lines_before=0, inset=0, add_inset=tabc, 
                    add_choices={"s": None}
                )

                if value is not None:
                    if value:
                        mini_cli.prnt("Setting microscope to lorentz mode...")
                        msg = "Is the microscope in lorentz mode?"
                    else:
                        mini_cli.prnt("Ending lorentz mode...")
                        msg = "Is the microscope NOT in lorentz mode anymore?"
                    
                    t = time.time()
                    microscope.setInLorentzMode(value)
                    mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

                    if logging:
                        s = mini_cli.input_yn(
                            ("Please confirm: {}").format(msg), 
                            lines_before=0, inset=0, add_inset=tabc
                        )
                    else:
                        mini_cli.prnt("Skipping log.", inset=tabs)
                        s = None
                else:
                    mini_cli.prnt("Skipping test.", inset=tabs)
                    s = None
                
                test_log.append(("Setting {} ({})".format(var.name, var.unique_id), s, 
                                value))
            elif select == "c":
                mini_cli.prnt("")
                mini_cli.prnt("Now testing current state.")

                value = mini_cli.input_inline_choices(
                    "Press 's' for [s]aving the current state. Press [r] to " + 
                    "restore the saved state (if there is one). Press [d] for " + 
                    "deleting the current state.",
                    ("s", "r", "d")
                )

                if value == 0:
                    current_state = microscope.getCurrentState()
                    mini_cli.prnt("Saved the current state")
                elif value == 1:
                    if isinstance(current_state, dict):
                        mini_cli.prnt("Restoring the current state.")

                        t = time.time()
                        microscope.setCurrentState(current_state)
                        mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

                        if logging:
                            s = mini_cli.input_yn(
                                ("Please confirm: Has the microscope the " + 
                                "saved state?"), 
                                lines_before=0, inset=0, add_inset=tabc
                            )
                        else:
                            mini_cli.prnt("Skipping log.", inset=tabs)
                            s = None
                            
                        test_log.append(("Restoring state", s, str(current_state)))
                        current_state = None
                    else:
                        mini_cli.prnt("No sate is saved, skipping.")
                elif value == 2:
                    current_state = None
                    mini_cli.prnt("Deleted current state.")
            elif select == "s":
                mini_cli.prnt("Setting to safe state.")

                t = time.time()
                microscope.resetToSafeState()
                mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

                if logging:
                    s = mini_cli.input_yn(
                        ("Please confirm: Is the microscope in the safe state?"), 
                        lines_before=0, inset=0, add_inset=tabc
                    )
                else:
                    mini_cli.prnt("Skipping log.", inset=tabs)
                    s = None
                    
                test_log.append(("Set to safe state", s, None))
            elif select == "e":
                value = mini_cli.input_yn(
                    "Setting to EMERGENCY state.", 
                    "yes to continue, no for cancel", 
                    lines_before=0, inset=0, add_inset=tabc
                )

                if value:
                    t = time.time()
                    microscope.resetToEmergencyState()
                    mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

                    if logging:
                        s = mini_cli.input_yn(
                            ("Please confirm: Is the microscope in the EMERGENCY state?"), 
                            lines_before=0, inset=0, add_inset=tabc
                        )
                    else:
                        mini_cli.prnt("Skipping log.", inset=tabs)
                        s = None
                        
                    test_log.append(("Set to EMERGENCY state", s, None))
                else:
                    mini_cli.prnt("Cancelling EMERGENCY state")

        elif isinstance(select, int):
            var = microscope.supported_measurement_variables[select]
            mini_cli.prnt("")
            mini_cli.prnt(
                ("Now testing {}. Please remember to be carefully with " + 
                    "the values on the first test run!").format(var.name)
            )

            args = {
                "text": ("Please type in a value for the {} ({}) in {}-units. " + 
                    "Remember the limits {} <= {} <= {}. Also make sure " + 
                    "nothing can be damaged. Use 's' for [S]kip.").format(
                    var.name, var.unique_id, var.unit, var.min_value, 
                    var.unique_id, var.max_value), 
                "short_text": "{} [{}]".format(var.name, var.unit), 
                "lines_before": 0, 
                "inset": 0, 
                "add_inset": tabc, 
                "add_choices": {"s": None}
            }

            if isinstance(var.format, pylo.Datatype):
                args["datatype"] = var.format
                value = mini_cli.input_datatype(**args)
            else:
                value = mini_cli.input_float(**args)

            if value is not None:
                mini_cli.prnt("Setting to {} to {}{}...".format(
                    var.name, value, var.unit), end=" "
                )
                t = time.time()
                microscope.setMeasurementVariableValue(var.unique_id, value)
                mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

                if isinstance(var.format, pylo.Datatype):
                    value = "{} ({})".format(value, var.format.format(value))
                if logging:
                    s = mini_cli.input_yn(
                        ("Please confirm: Is the microscopes {} now " + 
                            "{} {}?").format(var.name, value, var.unit), 
                        lines_before=0, inset=0, add_inset=tabc
                    )
                else:
                    mini_cli.prnt("Skipping log.", inset=tabs)
                    s = None
            else:
                mini_cli.prnt("Skipping test.", inset=tabs)
                s = None
            
            test_log.append(("Setting {} ({})".format(var.name, var.unique_id), s, 
                            value))
    
    if logging:
        mini_cli.prnt("")
        mini_cli.prnt("Log")

        col_widths = []

        for cols in test_log:
            for i, c in enumerate(cols):
                if len(col_widths) <= i:
                    col_widths.append(0)
                
                col_widths[i] = max(col_widths[i], len("{}".format(c)))

        sep = " | "
        template = sep.join([("{:" + str(cw) + "}") for cw in col_widths])

        mini_cli.prnt(template.format("Task", "Success", "Value"))
        mini_cli.prnt((sum(col_widths) + (len(col_widths) - 1) * len(sep)) * "=")

        for task, success, value in test_log:
            mini_cli.prnt(template.format(task, success, value))