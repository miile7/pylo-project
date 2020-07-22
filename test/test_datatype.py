import os

if __name__ == "__main__":
    # For direct call only
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import random
import pytest

import pylo

@pytest.fixture()
def hex_int_datatype():
    def format_hex(v, f):
        f = list(pylo.Datatype.split_format_spec(f))
        # alternative form, this will make 0x<number>
        f[3] = "#"
        # convert to hex
        f[8] = "x"

        return ("{" + "".join(f) + "}").format(v)

    return pylo.Datatype(
        "hex", 
        format_hex,
        lambda x: x if isinstance(x, int) else int(str(x), base=16)
    )

class TestDatatype:
    @pytest.mark.parametrize("spec,expected", [
        # examples taken from python format doc
        ("<30", (" ", "<", "", "", "", 30, "", "", "")),
        (">20", (" ", ">", "", "", "", 20, "", "", "")),
        ("*^10", ("*", "^", "", "", "", 10, "", "", "")),
        ("+f", (" ", "", "+", "", "", "", "", "", "f")),
        ("-f", (" ", "", "-", "", "", "", "", "", "f")),
        (" f", (" ", "", " ", "", "", "", "", "", "f")),
        ("+b", (" ", "", "+", "", "", "", "", "", "b")),
        ("-x", (" ", "", "-", "", "", "", "", "", "x")),
        (" o", (" ", "", " ", "", "", "", "", "", "o")),
        ("d", (" ", "", "", "", "", "", "", "", "d")),
        ("#x", (" ", "", "", "#", "", "", "", "", "x")),
        ("#o", (" ", "", "", "#", "", "", "", "", "o")),
        ("0,", (" ", "", "", "", "0", "", ",", "", "")),
        (".2%", (" ", "", "", "", "", "", "", 2, "%")),
    ])
    def test_split_format_spec(self, spec, expected):
        """Test if the split format function works."""

        assert pylo.Datatype.split_format_spec(spec) == expected

    @pytest.mark.usefixtures("hex_int_datatype")
    @pytest.mark.parametrize("parse,expected", [
        (0, 0),
        (-10, -10),
        ("-10", -16),
        ("-A", -10),
        ("-0xA", -10),
        ("-0XA", -10),
        ("-0xa", -10),
        ("-0xA", -10),
        ("0xFF", 255)
    ])
    def test_hex_int_parse(self, hex_int_datatype, parse, expected):
        """Test if the hex int datatype works."""

        assert hex_int_datatype.parse(parse) == expected
        assert hex_int_datatype(parse) == expected