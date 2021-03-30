if __name__ == "__main__":
    # For direct call only
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pylo

class TestEvent:
    def setup_method(self):
        self.event = pylo.Event()
        self.reset_triggered_handler()
    
    def reset_triggered_handler(self):
        """Reset whether the all the handlers have been triggered or not."""
        self.handler_1_triggered = False
        self.handler_2_triggered = False
    
    def handler1(self):
        """Event handler 1."""
        self.handler_1_triggered = True
    
    def handler2(self):
        """Event handler 2."""
        self.handler_2_triggered = True
    
    def test_handlers_executed(self):
        """Test if handlers are executed."""
        # remove all handlers, reset handlers
        self.event.clear()
        self.reset_triggered_handler()

        # add handlers
        self.event["handler_1"] = self.handler1
        self.event["handler_2"] = self.handler2

        # trigger event
        self.event()

        # check if both handlers were executed
        assert self.handler_1_triggered
        assert self.handler_2_triggered
    
    def test_not_triggering_after_remove(self):
        """Test if hanlders are not triggered anymore if they are added and 
        then removed again."""
        # remove all handlers, reset handlers
        self.event.clear()
        self.reset_triggered_handler()

        # add handlers
        self.event["handler_1"] = self.handler1
        self.event["handler_2"] = self.handler2

        # remove handler again
        del self.event["handler_1"]

        # trigger event
        self.event()

        # check if handler 1 is executed but not handler 2
        assert not self.handler_1_triggered
        assert self.handler_2_triggered
    
    def test_triggered_multiple_times(self):
        """Test if hanlders are triggered multiple times."""
        # remove all handlers, reset handlers
        self.event.clear()
        self.reset_triggered_handler()

        # add handlers
        self.event["handler_1"] = self.handler1
        self.event["handler_2"] = self.handler2

        # trigger event
        self.event()

        # check if both handlers are executed
        assert self.handler_1_triggered
        assert self.handler_2_triggered

        # reset for testing again
        self.reset_triggered_handler()

        # trigger event again
        self.event()

        # check if both handlers are executed again
        assert self.handler_1_triggered
        assert self.handler_2_triggered