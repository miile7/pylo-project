from .event import Event

"""Fired when all the attatched machines should go in the safe state"""
emergency = Event()

"""Fired when the microscope is in lorenz mode the measurement is right about 
starting"""
microscope_ready = Event()

"""Fired when the measurement has fully finished"""
measurement_ready = Event()

"""Fired before setting the microscope to the the next measurement point"""
before_record = Event()

"""Fired after setting the microscope to measurement point and recording an 
image but before saving the image to the directory"""
after_record = Event()

"""Fired when the measurement is stopped but not finished"""
after_stop = Event()

"""Fired when the view and the configuration are loaded but before everything 
else."""
init_ready = Event()

"""Fired when the user has entered all the settings and presses the measurement
start button. Note that this event may be fired multiple times when the user 
inputs an invalid measurement. Due to python philosophy (Ask for forgivness, 
not for permission) the measurement is created with possibly wrong data which 
then will raise an error. This will be shown to the user and he will be asked
to repeat the measurement."""
user_ready = Event()

"""Fired when the Measurement series is created."""
series_ready = Event()

"""Fired before everything. This event is fired in the constructor of the
controller which should be the first object that is created."""
before_start = Event()

"""Fired when the program is started but nothing is initialized yet."""
before_init = Event()