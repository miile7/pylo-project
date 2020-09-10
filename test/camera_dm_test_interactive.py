import DigitalMicrograph as DM
import numpy as np

import matplotlib.pyplot as plt

# Get the current camera and ensure it is ready for acquisition
cam = DM.GetActiveCamera()
cam.PrepareForAcquire()

fig = plt.figure(figsize=(8, 8))
columns = 2
rows = 1
for i in range(1, columns*rows +1):
    DM.OkDialog("Start recording image")

    exposure = 0.1
    bin_x = 1
    bin_y = 1
    process_level = 1
    ccd_area_top = 0
    ccd_area_right = 4096
    ccd_area_bottom = 4096
    ccd_area_left = 0
    # cam.AcquireImage(exposure, bin_x, bin_y, process_level, ccd_area_top,
    #                  ccd_area_left, ccd_area_bottom, ccd_area_right).ShowImage()
    # data = cam.AcquireImage(exposure, bin_x, bin_y, process_level, ccd_area_top,
    #                         ccd_area_left, ccd_area_bottom, ccd_area_right).GetNumArray()
    data = np.random.random((ccd_area_right - ccd_area_left, ccd_area_bottom - ccd_area_top));

    fig.add_subplot(rows, columns, i)
    plt.imshow(data)

plt.show()
    