import time

import numpy as np

# for python <3.6
from pylo import FallbackModuleNotFoundError

try:
    import DigitalMicrograph as DM
except (FallbackModuleNotFoundError, ImportError) as e:
    DM = None

# from .dm_camera import DMCamera
from pylo import loader
DMCamera = loader.getDeviceClass("Digital Micrograph Camera")

class _DMDummyCamera:
    def PrepareForAcquire(self):
        self.SetInserted(True)
    
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
    
    def IsRetractable(self):
        return True
    
    def SetInserted(self, inserted):
        self.inserted = inserted
        
        if not inserted:
            try:
                import DigitalMicrograph as DM
            except Exception:
                DM = None
            
            text = "Camera {} is now retracted!".format(self.__class__.__name__)
            if DM is not None:
                DM.OkDialog(text)
            else:
                print(text)

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