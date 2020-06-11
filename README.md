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

PyLo is written with python 3.2.

### General

### gatan-view.py
- Digital Micrograph Library