import subprocess
import sys

from epicsdb2bob import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "epicsdb2bob", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
