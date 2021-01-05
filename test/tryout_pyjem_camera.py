import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import matplotlib.pyplot as plt

import pylo

path = os.path.join(__file__, "..", "devices", "pyjem_camera.py")
pylo.loader.addDeviceFromFile("camera", "PyJEM Camera", path, "PyJEMCamera", 
                              {"detector-name": "camera", "image-size": 1024})

controller = pylo.setup(pylo.CLIView(), pylo.IniConfiguration())
camera = pylo.loader.getDevice("PyJEM Camera", controller)

# record pyjem example image
image = camera.recordImage()

# show example image
plt.imshow(image.image_data)
plt.show()