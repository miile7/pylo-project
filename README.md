# PyLo

![PyLo measurement series start](docs/pylo-promotion.gif)

PyLo is a Python module and program for recording Lorentz-TEM image series.

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

**Key Features**:

1. Record LTEM image series automatically (e.g. field series + focus series for induction maps)
2. Integration in [Gatan Microscopy Suite Software](https://www.gatan.com/products/tem-analysis/gatan-microscopy-suite-software)
3. Alternative Command Line Interface
4. Adaptable for all TEMs and connected camera systems
5. Easily extendable parameter control
6. Plug-In and Event system integrated
1. Offline installation possible

## Installation

### GMS (Internet connection required)

For PyLo with the GMS integration, follow the instructions in the 
[PyLo GMS Frontend](https://github.com/miile7/pylo-gms) repository.

### Command line interface (Internet connection required)

For the command line installation install Python (<https://www.python.org/>). 

Then use 
```cmd
python -m pip install pylo
```
to install PyLo.

After [installing the devices](#install-devices) (camera and microscope) you can start 
PyLo by invoking
```cmd
python -m pylo
```

### Install devices

> **TL;DR**: Download `devices/` directory and `devices.ini`, move to both files to
> `%programfiles%\Gatan\Plugins\` for the GMS installation and to `%username%\pylo\`
> for windows or to `~/pylo/` for Unix CLI installation.

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

### Manual installation (No Internet connection needed)

To install PyLo manually [download this repository](/archive/master.zip) and extract it. 

For executing PyLo in GMS, move the `pylo-master` directory to 
`%programfiles\Gatan\Plugins`. Now open the `pylo-gms` directory. Follow the installation 
instructions from the [PyLo GMS Frontend](https://github.com/miile7/pylo-gms) installation 
but use the files from the `pylo-gms` directory instead of downloading files (the files to
download are the files in the `pylo-gms` directory).

For the command line usage move the extracted `pylo-master` directory anywhere 
(`%userdata%` recommended for Windows, `~` recommended for Unix). Open the command line,
move to this directory and start pylo by invoking it as a module:

**Windows**
```cmd
cd %userdata%\pylo-master\
python -m pylo
```

**Unix**
```bash
cd ~/pylo-master
python -m pylo
```

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