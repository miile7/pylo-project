import threading

class ExceptionThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        self.exceptions = []
        super(ExceptionThread, self).__init__(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        try:
            super(ExceptionThread, self).run(*args, **kwargs)
        except Exception as e:
            self.exceptions.append(e)