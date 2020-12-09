"""A python module to do magnetic measuremnets in the Lorentz-Mode with TEMs.

This provides both, the GUI and the backend for measuring. Multiple GUIs are 
offered together with various cameras and TEM implementations.
"""

import io
import csv
import logging

# create logger
logger = logging.getLogger('pylo')
logger.setLevel(logging.DEBUG)

class InvertedFilter(logging.Filter):
    """Allow all records except those with the given `name`."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def filter(self, record):
        if record.name != self.name:
            return 1
        else:
            return 0
class CsvFormatter(logging.Formatter):
    """Format the log output as a csv."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = io.StringIO()
        self.writer = csv.writer(self.output, quoting=csv.QUOTE_ALL)

    def format(self, record: logging.LogRecord):
        self.writer.writerow([record.name, record.funcName, record.levelname,
                              record.message, record.threadName, 
                              record.filename, record.lineno, record.asctime,
                              record.pathname, record.exc_info, record.exc_text,
                              record.stack_info])
        data = self.output.getvalue()
        self.output.truncate(0)
        self.output.seek(0)
        return data.strip()

# create file handler which logs even debug messages
from .config import PROGRAM_LOG_FILE
# dfm = logging.Formatter('%(name)s - %(funcName)s: %(levelname)s: %(message)s | %(threadName)s - %(filename)s - %(lineno)d - %(asctime)s - %(pathname)s - %(exc_info)s')
dfm = CsvFormatter()
fh = logging.FileHandler(PROGRAM_LOG_FILE, mode="a+", encoding="utf-8")
fh.setLevel(logging.DEBUG)
fh.setFormatter(dfm)
# exclude from loggings
fh.addFilter(InvertedFilter("pylo.Datatype"))
fh.addFilter(InvertedFilter("pylo.OptionsDatatype"))

# create console handler with a higher log level
ifm = logging.Formatter('%(name)s - %(funcName)s: %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(ifm)

# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

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

from .errors import DeviceImportError
from .errors import DeviceCreationError
from .errors import BlockedFunctionError
from .errors import DeviceClassNotDefined
from .errors import FallbackModuleNotFoundError
from .errors import ExecutionOutsideEnvironmentError

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
from .abstract_configuration import AbstractConfiguration

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
        logger.debug("Creating new loader instance")
        loader = DeviceLoader(*args, **kwargs)
    
    return loader

loader = get_loader()
from .config import DEFAULT_DEVICE_INI_PATHS
for p in DEFAULT_DEVICE_INI_PATHS:
    if (os.path.exists(p) and os.path.isfile(p) and 
        not p in loader.device_ini_files):
        logger.debug("Adding ini file '{}' to loader".format(p))
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
    logger.debug("Creating new controller instance")
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