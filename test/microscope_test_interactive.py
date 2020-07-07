import os
import sys
import easygui
import inspect
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pylo
import pylo.microscopes

pylo_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pylo")

class DummyConfiguration(pylo.AbstractConfiguration):
    def loadConfiguration(self):
        self.configuration = {}
    
    def getValue(self, group, key):
        descr = "Enter value for roup {}, key {}".format(group, key)
        
        descr_extended = self.getDescription(group, key)
        if isinstance(descr_extended, str) and descr_extended != "":
            descr += "\n\n" + descr_extended

        value = easygui.enterbox(descr, "Set configuration value")
        if value is not None:
            self.setValue(group, key, value)

        return super().getValue(group, key)

pylo.config.CONFIGURATION = DummyConfiguration()
pylo.config.VIEW = None

class DummyController():
    def __init__(self):
        self.configuration = pylo.config.CONFIGURATION

if __name__ == "__main__":
    files = list(map(
        lambda x: str(x), filter(
            lambda x: (x.endswith(".py") and x != "__init__.py" and 
                       x != "microscope_interface.py"),
            os.listdir(os.path.join(pylo_root, "microscopes"))
        )
    ))
    module_name = easygui.choicebox("Enter the micrscope file to test.", choices=files)

    if module_name is not None:
        if module_name.endswith(".py"):
            module_name = module_name[:-3]
        
        module = importlib.import_module("pylo.microscopes.{}".format(module_name))

        available_classes = []
        for name in dir(module):
            o = getattr(module, name)
            if inspect.isclass(o) and inspect.getmodule(o) == module:
                available_classes.append(name)
        
        if len(available_classes) > 1:
            class_name = easygui.choicebox("Select the class that defines the " +
                                           "microscope.", choices=available_classes)
        elif len(available_classes) == 1:
            class_name = available_classes[0]
        else:
            class_name = None
        
        if class_name != None:
            class_ = getattr(module, class_name)

            controller = DummyController()

            if (hasattr(class_, "defineConfigurationOptions") and 
                callable(class_.defineConfigurationOptions)):
                class_.defineConfigurationOptions(pylo.config.CONFIGURATION)

            micrsocpe = class_(controller)

            focus = easygui.integerbox("Input the focus to set")