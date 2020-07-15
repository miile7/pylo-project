from .event import Event
from . import __Docs

__event_docs__ = __Docs()

__event_docs__("after_stop", 
"""Fired when the measurement is stopped but not finished""")
after_stop = Event()

__event_docs__("emergency", 
"""Fired when all the attatched machines should go in the safe state""")
emergency = Event()

__event_docs__("before_start", 
"""Fired before everything. This event is fired in the constructor of the
controller which should be the first object that is created.""")
before_start = Event()

__event_docs__("before_init", 
"""Fired when the program is started but nothing is initialized yet.""")
before_init = Event()

__event_docs__("init_ready", 
"""Fired when the view and the configuration are loaded but before everything 
else.""")
init_ready = Event()

__event_docs__("user_ready", 
"""Fired when the user has entered all the settings and presses the measurement
start button. Note that this event may be fired multiple times when the user 
inputs an invalid measurement. Due to python philosophy (Ask for forgivness, 
not for permission) the measurement is created with possibly wrong data which 
then will raise an error. This will be shown to the user and he will be asked
to repeat the measurement.""")
user_ready = Event()

__event_docs__("series_ready", 
"""Fired when the Measurement series is created.""")
series_ready = Event()

__event_docs__("microscope_ready", 
"""Fired when the microscope is in lorenz mode the measurement is right about 
starting""")
microscope_ready = Event()

__event_docs__("before_record", 
"""Fired before setting the microscope to the the next measurement point""")
before_record = Event()

__event_docs__("after_record", 
"""Fired after setting the microscope to measurement point and recording an 
image but before saving the image to the directory""")
after_record = Event()

__event_docs__("measurement_ready", 
"""Fired when the measurement has fully finished""")
measurement_ready = Event()