# PyLo

A Python script for measuring magnetic domains, in particular Skyrmions, in the Lorentz 
Mode with transmission electron microscopes. 

The software is written for the JEOL NeoArm F200 with Gatan Microscopy Suite as the 
displaying software but can be extended to use any microscope. Also it comes with a 
command line view, that does not need Gatan Microscopy Suite.

PyLo provides an easy to understand GUI to create highly customizable measurement series 
to automatically record changes in magnetic orders. With the JEOL NeoArm F200, PyLo allows
creating series over the tilt in x and y direction, the (de-)focus and the magnetic field
applied by activating the objective lenses.

PyLo is easily extended. It provides an Event system to hook in before or after specific
actions. It allows to use and change all settings at any time. Also it provides an easy to 
use settings manager where plugins can add their settings which will be shown to the user 
before every measurement run. Microscopes and cameras can be customized or replaced by 
creating own classes that implement an interface. This way PyLo can deal with every 
microscope and camera. 

With PyLo there come two different views, one only usable in Gatans Microscopy Suite, the 
other one for using PyLo in the command line. Also here PyLo provides an easy to implement
interface to create own views.

## Dependencies

PyLo is written with python 3.5.6+ (tested with 3.5.6 and 3.7.1).

- PyJEM by JEOL (needs the following packages, not installed by default)
  - [httplib2](https://github.com/httplib2/httplib2) 
    ([pip](https://pypi.org/project/httplib2/), 
    [conda](https://anaconda.org/conda-forge/httplib2))
  - [cv2 (OpenCV)](https://opencv.org/) 
    ([pip](https://pypi.org/project/opencv-python/), 
    [conda](https://anaconda.org/conda-forge/opencv))
  - [matplolib](https://matplotlib.org/) 
    ([pip](https://pypi.org/project/matplotlib/), 
    [conda](https://anaconda.org/conda-forge/matplotlib))
    - [sip](https://www.riverbankcomputing.com/software/sip/) 
      ([pip](https://pypi.org/project/sip/),
      [conda](https://anaconda.org/anaconda/sip))
- [NumPy](https://numpy.org/) ([pip](https://pypi.org/project/numpy/), 
  [conda](https://anaconda.org/anaconda/numpy))
- [PIL (Pillow)](https://python-pillow.org/) 
  ([pip](https://pypi.org/project/Pillow/), 
  [conda](https://anaconda.org/anaconda/pillow))
- [execdmscript](https://github.com/miile7/execdmscript)
  ([pip](https://pypi.org/project/execdmscript/))

## Usage

This chapter will come soon.

To use PyLo from the start, download and execute the `cli_main.py` in the command line or 
open Gatan Microscopy Suite (GMS) and execute the `dm_main.py` there. Note that PyLo 
cannot be installed as a menu option at the moment (coming soon).

## Internal structure

### Class structure 

<img src="docs/pylo-Page-1.svg" />

### Program flow

<img src="docs/pylo-Page-2.svg" />