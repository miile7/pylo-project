if __name__ == "__main__":
    # For direct call only
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import pytest
import pylo

class TestCameraInterface:
    def test_for_not_implemented(self):
        camera = pylo.CameraInterface()

        with pytest.raises(NotImplementedError):
            asyncio.run(camera.recordImage())