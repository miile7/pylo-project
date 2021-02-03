# PyLo

PyLo is a Python module and program for recording Lorentz-TEM images.

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
creating own classes that implement an interface. Those classes can be loaded dynamically.
This way PyLo can deal with every microscope and camera without having to learn the whole
program code. 

## Installation

### GMS

1. Download 

### Command line interface

> **TL;DR**: Execute `python -m pip install pylo`, then [install devices](#install-devices)

For the command line installation install Python (<https://www.python.org/>). Then use 
```cmd
python -m pip install pylo
```
to install PyLo.

The next step is to install a microscope and a camera. You can use one of the pre-defined
ones as described below in the [install devices](#install-devices) section. PyLo contains
a PyJEM Microscope and PyJEM Camera supporting JEOLs `PyJEM` library. For testing you can 
use the Dummy Microscope and Cameras. For all other microscope and cameras you will have 
to implement your own device adapter.

After installing the microscope and camera you can start the program by running 
`python -m pylo`.

### Install devices

> **TL;DR**: Download `devices/` directory and `devices.ini`, move to `%username%\pylo\`
> for windows, to `~/pylo/` for Unix

In PyLo the microscope and the camera (and potential other hardware machines) are called 
"devices". Those are loaded on runtime and can be selected by the users. Devices are 
defined in python standalone files that are not integrated in the PyLo source code. They 
are installed by adding their definitions to the `devices.ini` file(s) which can be 
located at various places.

PyLo offers 3 cameras and 3 microscopes:
1. Cameras
  1. Digital Micrograph Camera: Any camara that can be used in Gatans Microscopy Suite (only
    usable in GMS mode)
  2. Dummy Camera: A camera that creates images filled with random pixel data (for testing)
  3. PyJEM Camera: A camera using JEOLs `PyJEM` library (not well tested)
2. Microscopes
  1. Digital Micrograph Microscope: Any microscope that can be used in Gatans Microscopy
     Suite (only usable in GMS mode)
  2. Dummy Microscope: A microscope that has a focus measurement variable, an objectiv 
     lens current variable and a pressure variable that can be modified, each change in 
     one of those values does nothing (for testing)
  3. PyJEM Microscope: A microscope using JEOLs `PyJEM` library (not well tested)
To install those, download the `devices` directory and the `devices.ini` file. Move them 
into one of the devices directories listed below. To prevent one device showing up, you 
can either delete the python file or set the `disabled` value in the `devices.ini` to `No`.

PyLo will look for `devices.ini` files in the following locations. If there are multiple 
files, all of them are used. If there are multiple devices with the same name, the file
found first is used (not the order below):
1. The program data directory, Windows: `%username%\pylo\`, Unix: `~/pylo/`
   (**recommended for CLI installation**, create if necessary)
2. The current user directory, Windows: `%username%`, Unix: `~/`
3. The current working directory (the directory PyLo is executed in)
4. *GMS only:* GMS "plugin" directory, Windows: `%programfiles%\Gatan\Plugins`
   (**recommended for GMS installation**, create if necessary)
5. *GMS only:* GMS "application" directory, Windows: `%programfiles%\Gatan`

### Manual installation

To install PyLo manually download this repository. For executing PyLo in GMS use either
the `dm_main.s` or the `dm_main.py` (the former executes the latter). For executing PyLo
in the command line, execute the `main.py`.
#### Dependencies

PyLo is written with python 3.5.6+ (tested with 3.5.6 and 3.7.1).

- [NumPy](https://numpy.org/) ([pip](https://pypi.org/project/numpy/), 
  [conda](https://anaconda.org/anaconda/numpy))
- [PIL (Pillow)](https://python-pillow.org/) 
  ([pip](https://pypi.org/project/Pillow/), 
  [conda](https://anaconda.org/anaconda/pillow))
- [execdmscript](https://github.com/miile7/execdmscript)
  ([pip](https://pypi.org/project/execdmscript/))

Note that the devices may need more libraries.