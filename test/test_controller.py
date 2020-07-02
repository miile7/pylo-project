import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pylo

@pytest.fixture
def get_controller():
    controller = pylo.Controller()

class TestController:
    @pytest.usefixture()
    def test_parse_series(self):