import os
import sys
import time
import inspect
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mini_cli
import pylo
import pylo.microscopes

controller = pylo.Controller()

###############################################################################
###                                                                         ###
###         Change only this for testing a different microscope             ###
###                                                                         ###
###############################################################################

microscope_class = pylo.microscopes.PyJEMMicroscope
microscope_args = (controller,)

######################## general test code starts here ########################

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
    
    def addConfigurationOption(self, group, key, datatype=None, default_value=None, 
                                    ask_if_not_present=None, description=None,
                                    restart_required=None):
        if self.logging:
            self.define_log.append((key, group))

        return super().addConfigurationOption(
            group, key, datatype, default_value, ask_if_not_present, 
            description, restart_required
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

pylo.config.CONFIGURATION = DummyConfiguration()
pylo.config.VIEW = DummyView()

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
    mini_cli.inpt("Press Enter to start the interactive test")

    test_log = []

    # test setting lorenz mode
    mini_cli.prnt("")
    mini_cli.prnt("Setting to lorenz mode...", end=" ")
    t = time.time()
    microscope.setInLorenzMode(True)
    mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

    s = mini_cli.input_yn("Please confirm: Is the microscope in lorenz mode?", 
                          lines_before=0, inset=0, add_inset=tabc)
    test_log.append(("Switch to lorenz mode", s))

    # test measurement variables
    for var in microscope.supported_measurement_variables:
        mini_cli.prnt("")
        mini_cli.prnt(("Now testing {}. Please remember to be carefully with the " + 
               "values on the first test run!").format(var.name))
        value = mini_cli.input_int(("Please type in a value for the {} ({}) " + 
                            "in {}-units. Remember the limits {} <= {} <= {}. " + 
                            "Also make sure nothing can be damaged. Use " + 
                            "'s' for [S]kip.").format(
                                var.name, var.unique_id, var.unit, 
                                var.min_value, var.unique_id, var.max_value), 
                            "{} [{}]".format(var.name, var.unit), 
                            lines_before=0, inset=0, add_inset=tabc, 
                            add_choices={"s": None})

        if value is not None:
            mini_cli.prnt("Setting to {} to {}{}...".format(var.name, value, var.unit), end=" ")
            t = time.time()
            microscope.setMeasurementVariableValue(var.unique_id, value)
            mini_cli.prnt("Done. (took {:.3f}s)".format(time.time() - t))

            s = mini_cli.input_yn(("Please confirm: Is the microscopes {} now " + 
                                "{}{}?").format(var.name, value, var.unit), 
                                lines_before=0, inset=0, add_inset=tabc)
        else:
            mini_cli.prnt("Skipping test.", inset=tabs)
            s = None
        
        test_log.append(("Setting {} ({})".format(var.name, var.unique_id), s, 
                         value))