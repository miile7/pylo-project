import pylo
import pylo.config

pylo.config.VIEW = pylo.CLIView()
pylo.config.CONFIGURATION = pylo.IniConfiguration()

# pylo.config.CONFIGURATION.setValue("setup", "microscope-module", "pyjem_microscope.py")
# pylo.config.CONFIGURATION.setValue("setup", "microscope-class", "PyJEMMicroscope")
# pylo.config.CONFIGURATION.setValue("setup", "camera-module", "pyjem_camera.py")
# pylo.config.CONFIGURATION.setValue("setup", "camera-class", "PyJEMCamera")

pylo.execute()

# import pylo.microscopes

# controller = pylo.Controller()
# controller.microscope = pylo.microscopes.PyJEMMicroscope(controller)
# cliview = pylo.CLIView()
# cliview._showCreateMeasurementLoop(controller)