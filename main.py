import pylo
import pylo.microscopes
import pylo.cameras
import pylo.config

pylo.config.VIEW = pylo.DMView()
pylo.config.CONFIGURATION = pylo.IniConfiguration()

# pylo.config.CONFIGURATION.setValue("setup", "microscope-module", "pyjem_microscope.py")
# pylo.config.CONFIGURATION.setValue("setup", "microscope-class", "PyJEMMicroscope")
# pylo.config.CONFIGURATION.setValue("setup", "camera-module", "pyjem_camera.py")
# pylo.config.CONFIGURATION.setValue("setup", "camera-class", "PyJEMCamera")

pylo.config.CONFIGURATION.setValue("pyjem-camera", "detector-name", "camera")
pylo.config.CONFIGURATION.setValue("pyjem-camera", "image-size", 1024)

controller = pylo.Controller()

pylo.microscopes.PyJEMMicroscope.defineConfigurationOptions(controller.configuration)
pylo.cameras.PyJEMCamera.defineConfigurationOptions(controller.configuration)

controller.microscope = pylo.microscopes.PyJEMMicroscope(controller)
controller.camera = pylo.cameras.PyJEMCamera(controller)

controller.startProgramLoop()

# pylo.execute()