"""A python module to do magnetic measuremnets in the Lorentz-Mode with TEMs.

This provides both, the GUI and the backend for measuring. Multiple GUIs are 
offered together with various cameras and TEM implementations.
"""

class __Docs(list):
    """A class for creating the docstring easily."""
    def __call__(self, name, text):
        self.append((name, text))
    
    def __str__(self):
        return "\n\n".join(["{}:\n{}".format(n, t) for n, t in self])

__doc__ += "\n\nConfiguration (.config)\n-----------------------\n"
__doc__ += """The following configurations are set in the config. They contain
the default values for the attributes that have to be known before the 
configuration object is loaded. In additions some default values for the 
configuration object are set here. This should only be modified when installing
the program once.\n\n"""
from .config import __config_docs__
__doc__ += str(__config_docs__)

from .event import Event
from .events import emergency
from .events import after_stop
from .events import before_start
from .events import before_init
from .events import init_ready
from .events import user_ready
from .events import series_ready
from .events import microscope_ready
from .events import before_record
from .events import after_record
from .events import measurement_ready

__doc__ += "\n\nEvents (.events)\n----------------\n"
__doc__ += """The following events are available after the program starts. You 
can add any kind of callable which will be executed when the event is fired.\n\n"""
from .events import __event_docs__
__doc__ += str(__event_docs__)

from .image import Image
from .device import Device
from .cli_view import CLIView
from .datatype import Datatype
from .datatype import OptionDatatype
from .log_thread import LogThread
from .controller import Controller
from .measurement import Measurement
from .stop_program import StopProgram
from .abstract_view import AbstractView
from .device_loader import DeviceLoader
from .blocked_function import BlockedFunction
from .camera_interface import CameraInterface
from .exception_thread import ExceptionThread
from .ini_configuration import IniConfiguration
from .measurement_steps import MeasurementSteps
from .vulnerable_machine import VulnerableMachine
from .measurement_variable import MeasurementVariable
from .microscope_interface import MicroscopeInterface
from .blocked_function_error import BlockedFunctionError
from .abstract_configuration import AbstractConfiguration
from .execution_outside_environment_error import ExecutionOutsideEnvironmentError

try:
    from .dm_view import DMView
    from .dm_image import DMImage
    from .dm_configuration import DMConfiguration
except ExecutionOutsideEnvironmentError:
    DMView = None
    DMImage = None
    DMConfiguration = None

import os
import typing

loader = None
def get_loader(*args, **kwargs) -> DeviceLoader:
    """Get the current device loader instance.

    Any arguments will directly be passed to the `DeviceLoader` constructor if
    the loader does not exist yet.

    Returns
    -------
    DeviceLoader
        The current loader or a new one if there is no loader yet
    """
    global loader
    if not isinstance(loader, DeviceLoader):
        loader = DeviceLoader(*args, **kwargs)
    
    return loader

loader = get_loader()
from .config import DEFAULT_DEVICE_INI_PATHS
for p in DEFAULT_DEVICE_INI_PATHS:
    if (os.path.exists(p) and os.path.isfile(p) and 
        not p in loader.device_ini_files):
        loader.device_ini_files.append(p)

# controller = None
def get_controller(view: typing.Optional[AbstractView]=None,
                   configuration: typing.Optional[AbstractConfiguration]=None) -> Controller:
    """Get the current instance of the controller.

    The `view` and the `configuration` are ignored if the controller exists 
    already.

    Parameter
    ---------
    view : AbstractView
        The view to use for handling user inputs and displaying the measurement
        status, if not given the `config.VIEW` will be used instead, default:
        None
    configuration : AbstractConfiguration
        The configuration that defines how values are saved persistently, if 
        not given the `config.CONFIGURATION` will be used instead, 
        default: None

    Returns
    -------
    Controller
        The current controller
    """

    # global controller
    # if controller is None or not isinstance(controller, Controller):
    controller = Controller(view, configuration)
    
    return controller

def setup(view: typing.Optional[AbstractView]=None,
          configuration: typing.Optional[AbstractConfiguration]=None) -> Controller:
    """Create the setup for the measurement.

    The `view` and the `configuration` are ignored if the controller exists 
    already.

    Parameter
    ---------
    view : AbstractView
        The view to use for handling user inputs and displaying the measurement
        status, if not given the `config.VIEW` will be used instead, default:
        None
    configuration : AbstractConfiguration
        The configuration that defines how values are saved persistently, if 
        not given the `config.CONFIGURATION` will be used instead, 
        default: None
    
    Returns
    -------
    Controller
        The current controller
    """
    
    return get_controller(view, configuration)

def start(view: typing.Optional[AbstractView]=None,
          configuration: typing.Optional[AbstractConfiguration]=None) -> Controller:
    """Start the measurement.

    The measurement is started in another thread, so it will run in the 
    background. To wait for the measurement to finish use the `execute()`
    function.

    Parameter
    ---------
    view : AbstractView
        The view to use for handling user inputs and displaying the measurement
        status, if not given the `config.VIEW` will be used instead, default:
        None
    configuration : AbstractConfiguration
        The configuration that defines how values are saved persistently, if 
        not given the `config.CONFIGURATION` will be used instead, 
        default: None
    
    Returns
    -------
    Controller
        The current controller
    """
    
    controller = setup(view, configuration)
    controller.startProgramLoop()

    return controller

def execute(view: typing.Optional[AbstractView]=None,
            configuration: typing.Optional[AbstractConfiguration]=None) -> Controller:
    """Start the measurement and wait until it has finished.

    To execute the measurement in another thread without waiting for it to 
    finish use the `start()` function.

    Parameter
    ---------
    view : AbstractView
        The view to use for handling user inputs and displaying the measurement
        status, if not given the `config.VIEW` will be used instead, default:
        None
    configuration : AbstractConfiguration
        The configuration that defines how values are saved persistently, if 
        not given the `config.CONFIGURATION` will be used instead, 
        default: None
    
    Returns
    -------
    Controller
        The current controller
    """

    controller = start(view, configuration)
    controller.waitForProgram()

    return controller