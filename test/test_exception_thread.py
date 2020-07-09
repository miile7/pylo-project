import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import random
import time

import pylo

class DummyException(Exception):
    pass

class TestExceptionThread:
    def thread_callback(self):
        """The callback for the thread."""

        for i in range(10):
            print(i)
            self.counter = i
            time.sleep(0.01)

            # raise an exception before the counter reaches the end
            if random.randint(0, 8) < i:
                raise DummyException("Test exception")

    def get_thread(self):
        """Get the ExceptionThread for testing."""
        self.counter = -1;
        t = pylo.ExceptionThread(target=self.thread_callback)

        t.start()
        t.join()

        return t
    
    def test_exception_received(self):
        """Check if the ExceptionThread contains exceptions."""

        self.counter = -1;
        t = self.get_thread()

        assert len(t.exceptions) == 1
        assert isinstance(t.exceptions[0], DummyException)
        assert str(t.exceptions[0]) == "Test exception"
        # thread function is executed
        assert self.counter >= 0
        # counter never reaches the end
        assert self.counter < 9
