from .microscope_interface import MicroscopeInterface
from ..execution_outside_environment_error import ExecutionOutsideEnvironmentError

try:
    from .pyjem_microscope import PyJEMMicroscope
except ExecutionOutsideEnvironmentError:
    PyJEMMicroscope = None

try:
    from .pyjem_test_microscope import PyJEMTestMicroscope
except ExecutionOutsideEnvironmentError:
    PyJEMTestMicroscope = None