import os
import sys

import matplotlib.pyplot as plt

d = os.path.dirname(os.path.dirname(__file__))
if d not in sys.path:
    sys.path.append(d)

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