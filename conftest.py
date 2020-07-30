import pytest
import pathlib

def versiontuple(v):
    """Get the version as a tuple.

    Taken from https://stackoverflow.com/a/11887825/5934316
    """

    return tuple(map(int, (v.split("."))))

if versiontuple(pytest.__version__) < (3, 9, 0):
    # the tmp_path fixture does not exist, but it is widely used,
    # python 3.5.6 uses pytest < 3.9.0 so testig would not be possible without
    # this fix

    @pytest.fixture()
    def tmp_path(tmpdir):
        return pathlib.Path(str(tmpdir))