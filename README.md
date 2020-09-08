# PyLo

A Python script for measuring magnetic domains, in particular Skyrmions, in the Lorenz 
Mode with transmission electron microscopes. 

The software is written for the JEOL NeoArm F200 with Gatan as the displaying software. It 
contains Events on image recording to add plugins that change the measuring behaviour
<sup>1</sup>. PyLo also contains the following security mechanisms:

- When the Camera image gets an Intensity above 10.000 in more than 100px, the measurement
  will be stopped<sup>1</sup>
- The operator will be asked to confirm the limits of the measurement types<sup>1</sup>

<sup>1</sup>Not yet implemented

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

### General

### gatan-view.py
- Digital Micrograph Library

## Internal structure

### Class structure 

<img src="docs/pylo-Page-1.svg" />

### Program flow

<img src="docs/pylo-Page-2.svg" />