import importlib
import typing
import os

from .abstract_configuration import Savable
from .config import CONFIGURATION
from .config import PROGRAM_NAME
from .config import VIEW

CONFIG_SETUP_GROUP = "setup"

class Controller:
    """This is the controller for the pylo program.

    This object contains all the other objects and is the main entry point for 
    the program.

    Attributes
    ----------
    view : AbstractView
        The view
    microscope : MicroscopeInterface
        The microscope that is used for measuring
    configuration : AbstractConfiguration
        The configuration
    camera : CameraInterface
        The camera that is used for receiving the images
    measurement : Measurement or None
        The measurement to do
    """

    def __init__(self):
        self.configuration = CONFIGURATION
        self.view = VIEW

        # add the option for the microscope module
        self.configuration.addConfigurationOption(
            CONFIG_SETUP_GROUP, "microscope-module", str, description=("The " + 
            "module name where the microscope to use is defined. This must " + 
            "be a valid python module name relative to the {name} root. So " + 
            "if you are outside {name}, you should type pylo<your input>" + 
            "(usually including the first dot). For example use " + 
            ".microscopes.my_custom_microscope. (The file  is then in " + 
            "pylo/microscopes/my_custom_microscope.py)").format(name=PROGRAM_NAME)
        )

        default_module_path = os.path.join(os.path.dirname(__file__), 
                                           "microscopes")
        modules = filter(lambda x: (x.endswith(".py") and
                                    x != "microscope_interface.py" and 
                                    x != "__init__.py"), 
                        os.listdir(default_module_path))

        self.microscope = self._dynamicCreateClass("microscope-module", 
                                                   "microscope-class",
                                                   modules)
    
    def _dynamicCreateClass(self, config_key_module: str, config_key_class: str, 
                              module_options: typing.Optional[typing.Collection]=None, 
                              class_options: typing.Optional[typing.Collection]=None,
                              constructor_args: typing.Optional[typing.Collection]=None):
        """Dynamically create the an object of the given module and class where
        the module and class are loaded form the config.

        If the config does not contain the keys or there are not the values 
        given, the module and class are asked from the user.

        Parameters
        ----------
        config_key_module : str
            The key name in the configuration of the module to load the object 
            from
        config_key_class : str
            The key name in the configuration of the class
        module_options : Collection, optional
            The options of the modules to show to the user if the key is not 
            given
        class_options : Collection, optional
            The options of the classes to show to the user if the key is not 
            given
        constructor_args : tuple, optional
            The arguments to pass to the constructor
        """

        module_name, class_name = self.getConfigurationValuesOrAsk(
            (CONFIG_SETUP_GROUP, config_key_module, module_options),
            (CONFIG_SETUP_GROUP, config_key_class, class_options)
        )

        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)

        if isinstance(constructor_args, typing.Collection):
            return class_(*constructor_args)
        else:
            return class_()
    
    def getConfigurationValuesOrAsk(self, *config_lookup: typing.List[str, str, typing.Optional[typing.Collection]]) -> typing.Tuple[Savable]:
        """Get the configuration values or ask for them if they are not given.

        Parameters
        ----------
        tuple : 
            A tuple with the group at index 0, the key at index 1 and optional
            the allowed options at index 2
        """

        # the values to return
        values = {}
        # the values to ask
        input_params = {}

        for i, (group, key, *_) in enumerate(config_lookup):
            try:
                values[i] = self.configuration.getValue(group, key)
            except KeyError:
                # set the name to ask for
                input_param = {"name": "{} ({})".format(key, group)}

                try:
                    # try to get a description for the user asking
                    input_param["description"] = self.configuration.getDescription(
                        group, key
                    )
                except KeyError:
                    pass
                
                try:
                    # try to get the datatype
                    input_param["datatype"] = self.configuration.getDatatype(
                        group, key
                    )
                except KeyError:
                    input_param["datatype"] = str
                
                if len(_) > 0 and isinstance(_[0], typing.Iterable):
                    # check if there are options for this ask
                    input_param["options"] = list(_[0])
                
                # save the index and the ask parameters
                input_params[i] = input_param
        
        # check if there are values to ask for
        if len(input_params) > 0:
            # save the results of the user
            results = self.view.askFor(list(input_params.values()))
            # check where the results should be saved in
            target_keys = list(input_params.keys())

            for i, result in enumerate(results):
                # replace the missing value with the asked result
                values[target_keys[i]] = result
        
        return tuple(values.values())