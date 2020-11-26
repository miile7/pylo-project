import pylo

class DummyDevice(pylo.Device):
    def __init__(self, *args, **kwargs):
        super(DummyDevice, self).__init__(*args, **kwargs)

class TestDevice:
    def test_parameter_defaults(self):
        device = DummyDevice("test_kind")

        assert device.kind == "test_kind"
        assert device.name == "DummyDevice"
        assert device.config_group_name == "dummy-device"