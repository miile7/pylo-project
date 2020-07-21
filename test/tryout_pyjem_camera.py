import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import matplotlib.pyplot as plt

import pylo
import pylo.config
import pylo.cameras

pylo.config.CONFIGURATION = pylo.IniConfiguration()
pylo.config.VIEW = pylo.CLIView()

controller = pylo.setup()

pylo.cameras.PyJEMCamera.defineConfigurationOptions(controller.configuration)
controller.configuration.setValue("pyjem-camera", "detector-name", "camera")
controller.configuration.setValue("pyjem-camera", "image-size", 1024)
camera = pylo.cameras.PyJEMCamera(controller)

# record pyjem example image
image = camera.recordImage()

# show example image
plt.imshow(image.image_data)
plt.show()