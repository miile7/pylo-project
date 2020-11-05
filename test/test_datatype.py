import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest

import pylo

class TestDatatypes:
    @pytest.mark.parametrize("spec,expected", [
        # examples taken from python format doc
        ("<30", ("", "<", "", "", "", 30, "", "", "")),
        (">20", ("", ">", "", "", "", 20, "", "", "")),
        ("*^10", ("*", "^", "", "", "", 10, "", "", "")),
        ("+f", ("", "", "+", "", "", "", "", "", "f")),
        ("-f", ("", "", "-", "", "", "", "", "", "f")),
        (" f", ("", "", " ", "", "", "", "", "", "f")),
        ("+b", ("", "", "+", "", "", "", "", "", "b")),
        ("-x", ("", "", "-", "", "", "", "", "", "x")),
        (" o", ("", "", " ", "", "", "", "", "", "o")),
        ("d", ("", "", "", "", "", "", "", "", "d")),
        ("#x", ("", "", "", "#", "", "", "", "", "x")),
        ("#o", ("", "", "", "#", "", "", "", "", "o")),
        ("0,", ("", "", "", "", "0", "", ",", "", "")),
        (".2%", ("", "", "", "", "", "", "", 2, "%")),
    ])
    def test_split_format_spec(self, spec, expected):
        """Test if the split format function works."""

        assert pylo.Datatype.split_format_spec(spec) == expected

    @pytest.mark.parametrize("parse,expected", [
        (0, 0),
        (-10, -10),
        (-15.5, -15),
        # this is treated as a hex number
        ("-10", -16),
        ("-A", -10),
        ("-0xA", -10),
        ("-0XA", -10),
        ("-0xa", -10),
        ("-0xA", -10),
        ("0xFF", 255),
        # this is treated as a hex number
        ("15.5", 21)
    ])
    def test_hex_int_parse(self, parse, expected):
        """Test if the hex int datatype works."""

        assert pylo.Datatype.hex_int.parse(parse) == expected
        assert pylo.Datatype.hex_int(parse) == expected
    
    @pytest.mark.parametrize("value,format_spec,expected", [
        (10, "", "0xa"),
        (0xb, "", "0xb"),
        (0xb, "g", "0xb"),
        (0xb, "b", "0xb"),
        (0xb, "*^5.2b", "*0xb*")
    ])
    def test_hex_int_format(self, value, format_spec, expected):
        """Test if the hex int datatype works."""

        assert pylo.Datatype.hex_int.format(value, format_spec) == expected

    @pytest.mark.parametrize("parse,expected", [
        (0, 0),
        (-10, -10),
        (-15.5, -15),
        ("-10", -10),
        ("15.5", 15)
    ])
    def test_int_parse(self, parse, expected):
        """Test if the int datatype works."""

        assert pylo.Datatype.int.parse(parse) == expected
        assert pylo.Datatype.int(parse) == expected
    
    @pytest.mark.parametrize("value,expected", [
        (10, "10"),
        (0xb, "11"),
        ("10.1", "10"),
        ("10.9", "10")
    ])
    def test_int_format(self, value, expected):
        """Test if the int datatype works."""

        assert pylo.Datatype.int.format(value, "") == expected

    @pytest.mark.parametrize("datatype,parse,expected", [
        (pylo.Datatype.options((1, 2, 3)), 1, 1),
        (pylo.Datatype.options((1, 2, 3)), "1", 1),
        (pylo.Datatype.options(("a", "b", "c")), "a", "a"),
        (pylo.Datatype.options(("a", "b", "c")), "B", "b"),
        (pylo.Datatype.options((1.2, 1.3, 1.4)), 1.2, 1.2),
        (pylo.Datatype.options((1, 2, 3, 4), abs_tol=0.5), 1.6, 2),
        (pylo.Datatype.options(("cccacc", "cbcc"), ignore_chars=["c"]), "accc", "cccacc"),
    ])
    def test_options_parse(self, datatype, parse, expected):
        """Test if the options datatype works."""

        assert datatype.parse(parse) == expected
        assert datatype(parse) == expected
    
    @pytest.mark.parametrize("datatype,value,expected", [
        (pylo.Datatype.options((1, 2, 3)), 1, 1),
        (pylo.Datatype.options((1, 2, 3)), "1", 1),
        (pylo.Datatype.options(("a", "b", "c")), "a", "a"),
        (pylo.Datatype.options(("a", "b", "c")), "B", "b"),
        (pylo.Datatype.options((1.2, 1.3, 1.4)), 1.2, 1.2),
        (pylo.Datatype.options((1, 2, 3, 4), abs_tol=0.5), 1.6, 2),
    ])
    def test_options_format(self, datatype, value, expected):
        """Test if the options datatype works."""

        assert datatype.format(value, "") == expected