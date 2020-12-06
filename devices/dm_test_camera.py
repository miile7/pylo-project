import time

import numpy as np

# from .dm_camera import DMCamera
from pylo import loader
DMCamera = loader.getDeviceClass("Digital Micrograph Camera")

class _DMDummyCamera:
    def PrepareForAcquire(self):
        pass
    
    def AcquireImage(self, exposure_time, binning_x=1, binning_y=1, 
                     process_level=1, ccd_area_top=0, ccd_area_left=0,
                     ccd_area_bottom=4096, ccd_area_right=4096):
        
        time.sleep(exposure_time)
        data = np.random.random(((ccd_area_right - ccd_area_left) // binning_x,
                                 (ccd_area_bottom - ccd_area_top) // binning_y))
        time.sleep(0.1)
        img = DM.CreateImage(data)
        time.sleep(0.1)
        return img

class DMTestCamera(DMCamera):
    def __init__(self, *args, **kwargs) -> None:
        """Create a new dm camera object.
        
        Parameters
        ----------
        controller : Controller
            The controller
        """

        super(DMTestCamera, self).__init__(*args, **kwargs)
        self.camera = _DMDummyCamera()
    
    @staticmethod
    def defineConfigurationOptions(*args, **kwargs) -> None:
        DMCamera.defineConfigurationOptions(*args, **kwargs)