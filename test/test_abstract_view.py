import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest

import pylo

@pytest.fixture()
def view():
    return pylo.AbstractView()

class TestAbstractView:
    @pytest.mark.usefixtures("view")
    @pytest.mark.parametrize("progress", [
        10, 90, -1, 101, 0, 100
    ])
    def test_progress_limits(self, view, progress):
        """Test if the progress progress is >= 0 and <= limit (100)"""

        view.progress_max = 100
        view.progress = progress

        assert 0 <= view.progress
        assert view.progress <= 100
    
    @pytest.mark.usefixtures("view")
    def test_show_create_measurement_raise_not_implemented(self, view):
        """Test if all the functions raise NotImplementedErrors"""
        
        with pytest.raises(NotImplementedError):
            view.showCreateMeasurement(pylo.Controller(view, 
                                       pylo.AbstractConfiguration()))
    
    @pytest.mark.usefixtures("view")
    def test_show_settings_raise_not_implemented(self, view):
        """Test if all the functions raise NotImplementedErrors"""
        
        with pytest.raises(NotImplementedError):
            view.showSettings(pylo.Controller(view, pylo.AbstractConfiguration()))
    
    @pytest.mark.usefixtures("view")
    def test_show_hint_raise_not_implemented(self, view):
        """Test if all the functions raise NotImplementedErrors"""
        
        with pytest.raises(NotImplementedError):
            view.showHint("hint")
    
    @pytest.mark.usefixtures("view")
    def test_show_error_raise_not_implemented(self, view):
        """Test if all the functions raise NotImplementedErrors"""
        
        with pytest.raises(NotImplementedError):
            view.showError("hint")
    
    @pytest.mark.usefixtures("view")
    def test_print_raise_not_implemented(self, view):
        """Test if all the functions raise NotImplementedErrors"""
        
        with pytest.raises(NotImplementedError):
            view.print("Text", "to", "print")
    
    @pytest.mark.usefixtures("view")
    def test_ask_for_not_implemented(self, view):
        """Test if all the functions raise NotImplementedErrors"""
        
        with pytest.raises(NotImplementedError):
            view.askFor({"name": "test"})
    
    @pytest.mark.usefixtures("view")
    @pytest.mark.parametrize("input_dict,expected_dict", [
        ({"name": "Test 1", "datatype": pylo.Datatype.options(["Opt1", "Opt2"]), 
          "description": "Test description"}, "same"),
        ({"name": "Test 2", "datatype": pylo.Datatype.options((1.2, 1.3)), 
          "description": "Test description"}, "same"),
        ({"name": "Test 4"}, "same"),
        ({"name": "Test 5", "datatype": None, "description": None}, 
         {"name": "Test 5"})
    ])
    def test_format_ask_for(self, view, input_dict, expected_dict):
        """Test the format function for the askFor input"""

        if expected_dict == "same":
            expected_dict = input_dict.copy()
        
        assert view._formatAskForInput(input_dict) == expected_dict
    
    @pytest.mark.usefixtures("view")
    @pytest.mark.parametrize("input_dict,expected_error", [
        ({"datatype": int, "description": "Test description", 
          "options": ("Opt 1", "Opt 2"), "allow_custom": True}, KeyError),
        ({"name": 1}, TypeError),
        ({"name": "Test 1", "datatype": "str"}, TypeError),
        ({"name": "Test 1", "datatype": str, "description": False}, TypeError)
    ])
    def test_format_ask_for_errors(self, view, input_dict, expected_error):
        """Test the format function for the askFor input"""
        
        with pytest.raises(expected_error):
            view._formatAskForInput(input_dict)
