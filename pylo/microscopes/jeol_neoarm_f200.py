from .microscope_interface import MicroscopeInterface

class JEOLNeoARMF200(MicroscopeInterface):
    pass

# make sure to somehow save when a measurement variable is set, in the setsafemode
# wait until the measurement variable is set successfully, then set the 
# safe mode, use threading.Lock or queue.SimpleQueue