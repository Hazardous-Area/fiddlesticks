import subprocess

import pytest

from .helpers import IS_WINDOWS


@pytest.mark.skipif(IS_WINDOWS, reason="I haven't figured out the 7zip CLI on Windows yet")
def test_is_7zip_installed():
    args = ["7z", "--help"]
    subprocess.check_call(args)
