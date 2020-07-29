if __name__ == "__main__":
    # For direct call only
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import pylo

class DummyConfiguration(pylo.AbstractConfiguration):
    def getValue(self, *args, **kwargs):
        return "DEFAULT_CONFIGURATION_VALUE"

pylo.config.CONFIGURATION = DummyConfiguration()


class TestCameraInterface:
    def test_for_not_implemented(self):
        camera = pylo.cameras.CameraInterface(pylo.Controller())

        with pytest.raises(NotImplementedError):
            camera.recordImage()