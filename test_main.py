import pylo

view = pylo.CLIView()
configuration = pylo.IniConfiguration()

# set the microscope to use the PyJEM microscope
configuration.setValue("setup", "microscope-module", "pylo.microscopes")
configuration.setValue("setup", "microscope-class", "PyJEMTestMicroscope")

# use the DMCamera as the camera
configuration.setValue("setup", "camera-module", "pylo.cameras")
configuration.setValue("setup", "camera-class", "DummyCamera")

# change file extension
configuration.setValue("measurement", "save-file-format", "{counter}_{time:%Y-%m-%d_%H-%M-%S}_lorentz-measurement.tif")
# causes a bug when missing, this should be fixed later
configuration.setValue("pyjem-microscope", "magnetic-field-unit", 1)

pylo.execute(view, configuration)