import time

import numpy as np

try:
    test_error = ModuleNotFoundError()
except NameError:
    # for python <3.6, ModuleNotFound error does not exist
    # https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError
    class ModuleNotFoundError(ImportError):
        pass

try:
    import DigitalMicrograph as DM
except (ModuleNotFoundError, ImportError) as e:
    DM = None

from .dm_camera import DMCamera

class __DMDummyCamera:
    def PrepareForAcquire(self):
        pass
    
    def AcquireImage(self, exposure_time, binning_x=1, binning_y=1, 
                     process_level=1, ccd_area_top=0, ccd_area_left=0,
                     ccd_area_bottom=4096, ccd_area_right=4096):
        
        time.sleep(exposure_time)
        data = np.random.random(((ccd_area_right - ccd_area_left) / binning_x,
                                 (ccd_area_bottom - ccd_area_top) / binning_y))
        return DM.CreateImage(data)

class DMTestCamera(DMCamera):
    def __init__(self, controller: "Controller") -> None:
        """Create a new dm camera object.
        
        Parameters
        ----------
        controller : Controller
            The controller
        """

        super(DMTestCamera, self).__init__(controller)
        self.camera = __DMDummyCamera()