import pylo

dummy_device = """from pylo import {parent_class}

class {class_name}({parent_class}):
    def __init__(self, *args, **kwargs):
        super({class_name}, self).__init__(*args, **kwargs)
"""

dummy_device_ini = """[{name}]
kind=device
file={file_path}
class={class_name}
description=Test description
config-default.intval=1
config-default.boolval=No
config-default.strval=This is a test string
"""

class DummyDeviceObject(pylo.Device):
    def __init__(self, *args, **kwargs):
        super(DummyDeviceObject, self).__init__(*args, **kwargs)

class TestDeviceLoader:
    def check_loaded_device(self, loader, name, class_name, config_group, 
                            kind="device", config_defaults={
                                "intval": "1",
                                "boolval": "No",
                                "strval": "This is a test string"
                            }, description="Test description", controller=None):
        """Load the ini and perform the checks."""
        assert loader.getInstalledDeviceNames() == [name]
        assert loader.getInstalledDeviceNames(kind) == [name]
        
        device = loader.getDevice(name, controller)
        print(device)

        assert isinstance(device, pylo.Device)
        assert class_name in map(lambda c: c.__name__, device.__class__.__mro__)

        assert device.name == name
        assert device.kind == kind
        assert device.config_group_name == config_group
        assert device.description == description

        assert isinstance(device.config_defaults, dict)
        assert len(device.config_defaults) == len(config_defaults)
        assert device.config_defaults == config_defaults

        return device
    
    def test_load_ini_abs(self, tmp_path):
        """Test loading a class from an absolute path in an ini file."""
        name = "Dummy Device 1"
        class_name = "DummyDevice1"
        device_py_path = tmp_path / "dummy_device.py"
        device_ini_path = tmp_path / "devices.ini"

        with open(device_py_path, "w+") as f:
            f.write(dummy_device.format(class_name=class_name, name=name,
                                        parent_class="Device"))
        
        with open(device_ini_path, "w+") as f:
            f.write(dummy_device_ini.format(class_name=class_name, name=name,
                                            file_path=device_py_path))
        loader = pylo.DeviceLoader()
        loader.device_ini_files.add(device_ini_path)
        
        self.check_loaded_device(loader, name, class_name, "dummy-device-1")
    
    def test_load_ini_rel(self, tmp_path):
        """Test loading a class from an relative path in an ini file."""
        name = "Dummy Device 2"
        class_name = "DummyDevice2"
        device_py_path = tmp_path / "dummy_device_2.py"
        device_ini_path = tmp_path / "devices.ini"

        with open(device_py_path, "w+") as f:
            f.write(dummy_device.format(class_name=class_name, name=name,
                                        parent_class="Device"))
        
        with open(device_ini_path, "w+") as f:
            f.write(dummy_device_ini.format(class_name=class_name, name=name,
                                            file_path="./dummy_device_2.py"))
        
        loader = pylo.DeviceLoader()
        loader.device_ini_files.add(device_ini_path)
        
        self.check_loaded_device(loader, name, class_name, "dummy-device-2")
    
    def test_load_class(self, tmp_path):
        """Test loading a class file directly."""
        name = "Dummy Device 3"
        class_name = "DummyDevice"
        config_defaults = {
            "intval": "1",
            "boolval": "No",
            "strval": "This is a test string"
        }

        device_py_path = tmp_path / "dummy_device_3.py"
        with open(device_py_path, "w+") as f:
            f.write(dummy_device.format(class_name=class_name, name=name,
                                        parent_class="Device"))
        
        loader = pylo.DeviceLoader()
        loader.addDeviceFromFile("device", name, device_py_path, class_name,
                                 config_defaults, "Test description")
        
        self.check_loaded_device(loader, name, class_name, "dummy-device-3")
    
    def test_load_microscope(self, tmp_path):
        """Test loading a microscope from class file directly."""
        name = "Dummy Microscope"
        class_name = "DummyMicroscope"
        config_defaults = {
            "intval": "1",
            "boolval": "No",
            "strval": "This is a test string"
        }

        device_py_path = tmp_path / "dummy_microscope.py"
        with open(device_py_path, "w+") as f:
            f.write(dummy_device.format(class_name=class_name, name=name,
                                        parent_class="MicroscopeInterface"))
        
        loader = pylo.DeviceLoader()
        loader.addDeviceFromFile("microscope", name, device_py_path, class_name,
                                 config_defaults, "Test description")
        controller = pylo.Controller(None, pylo.AbstractConfiguration())

        device = self.check_loaded_device(loader, name, class_name, 
                                          "dummy-microscope", kind="microscope",
                                          controller=controller)
        
        assert hasattr(device, "controller")
        assert isinstance(device.controller, pylo.Controller)
        assert device.controller == controller

        assert isinstance(device, pylo.MicroscopeInterface)
    
    def test_load_camera(self, tmp_path):
        """Test loading a camera from class file directly."""
        name = "Dummy Camera"
        class_name = "DummyCamera"
        config_defaults = {
            "intval": "1",
            "boolval": "No",
            "strval": "This is a test string"
        }

        device_py_path = tmp_path / "dummy_camera.py"
        with open(device_py_path, "w+") as f:
            f.write(dummy_device.format(class_name=class_name, name=name,
                                        parent_class="CameraInterface"))
        
        loader = pylo.DeviceLoader()
        loader.addDeviceFromFile("camera", name, device_py_path, class_name,
                                 config_defaults, "Test description")
        controller = pylo.Controller(None, pylo.AbstractConfiguration())

        device = self.check_loaded_device(loader, name, class_name, 
                                          "dummy-camera", kind="camera",
                                          controller=controller)
        
        assert hasattr(device, "controller")
        assert isinstance(device.controller, pylo.Controller)
        assert device.controller == controller

        assert isinstance(device, pylo.CameraInterface)
    
    def test_load_device_from_object(self):
        """Test loading a camera from class file directly."""
        device = DummyDeviceObject("device")
        name = "Dummy Device Object"
        config_defaults = {
            "intval": "1",
            "boolval": "No",
            "strval": "This is a test string"
        }
        
        loader = pylo.DeviceLoader()
        loader.addDeviceObject("device", name, device, config_defaults, 
                               "Test description")

        load_device = self.check_loaded_device(loader, name, 
                                               "DummyDeviceObject", 
                                               "dummy-device-object")

        assert load_device == device