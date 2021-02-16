from .event import Event
from . import __Docs

__event_docs__ = __Docs()

__event_docs__("after_stop", 
"""Fired when the measurement is stopped but not finished. The current 
`controller` will be the first argument.""")
after_stop = Event()

__event_docs__("emergency", 
"""Fired when all the attatched machines should go in the safe state. The 
current `controller` will be the first argument.""")
emergency = Event()

__event_docs__("before_start", 
"""Fired before everything. This event is fired in the constructor of the
controller which should be the first object that is created.. The current 
`controller` will be the first argument.""")
before_start = Event()

__event_docs__("before_init", 
"""Fired when the program is started but nothing is initialized yet. The 
current `controller` will be the first argument.""")
before_init = Event()

__event_docs__("init_ready", 
"""Fired when the view and the configuration are loaded but before everything 
else isn't and before the program dialogs are shown. The current `controller` 
will be the first argument.""")
init_ready = Event()

__event_docs__("user_ready", 
"""Fired when the user has entered all the settings and presses the measurement
start button. Note that this event may be fired multiple times when the user 
inputs an invalid measurement. Due to python philosophy (Ask for forgivness, 
not for permission) the measurement is created with possibly wrong data which 
then will raise an error. This will be shown to the user and he will be asked
to repeat the measurement. The current `controller` will be the first 
argument.""")
user_ready = Event()

__event_docs__("series_ready", 
"""Fired when the Measurement series is created. The current `controller` will 
be the first argument.""")
series_ready = Event()

__event_docs__("microscope_ready", 
"""Fired when the microscope is in lorentz mode the measurement is right about 
starting. The current `controller` will be the first argument.""")
microscope_ready = Event()

__event_docs__("before_approach", 
"""Fired before approaching the microscope to the the next measurement points 
values. The current `controller` will be the first argument.""")
before_approach = Event()

__event_docs__("before_record", 
"""Fired after the measurement points values are reached but before recording 
the image. The current `controller` will be the first argument.""")
before_record = Event()

__event_docs__("after_record", 
"""Fired after setting the microscope to measurement point and recording an 
image but before saving the image to the directory. The current `controller` 
will be the first argument.""")
after_record = Event()

__event_docs__("measurement_ready", 
"""Fired when the measurement has fully finished. The current `controller` 
will be the first argument.""")
measurement_ready = Event()