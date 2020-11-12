import pylo

view = pylo.CLIView()
configuration = pylo.IniConfiguration()

# set the microscope to use the PyJEM microscope
configuration.setValue("setup", "microscope-module", "pylo.microscopes")
configuration.setValue("setup", "microscope-class", "PyJEMTestMicroscope")

# use the DMCamera as the camera
configuration.setValue("setup", "camera-module", "pylo.cameras")
configuration.setValue("setup", "camera-class", "DummyCamera")

pylo.execute(view, configuration)