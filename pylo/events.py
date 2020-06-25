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
stop = Event()