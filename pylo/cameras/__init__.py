from .camera_interface import CameraInterface
from ..execution_outside_environment_error import ExecutionOutsideEnvironmentError

try:
    from .pyjem_camera import PyJEMCamera
except ExecutionOutsideEnvironmentError:
    PyJEMCamera = None

try:
    from .dummy_camera import DummyCamera
except ExecutionOutsideEnvironmentError:
    DummyCamera = None
    
try:
    from .dm_camera import DMCamera
except ExecutionOutsideEnvironmentError:
    DMCamera = None
    
try:
    from .dm_test_camera import DMTestCamera
except ExecutionOutsideEnvironmentError:
    DMTestCamera = None