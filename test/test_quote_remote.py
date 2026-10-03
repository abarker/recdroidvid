"""Tests for quoting paths on the device in `adb shell` commands."""

import shlex

import pytest

from recdroidvid.adb_commands import quote_remote

@pytest.mark.parametrize("path", ["/storage/emulated/0/DCIM/OpenCamera/",
                                  "/sdcard/my take's  dir/VID 1.mp4",
                                  "/sdcard/$HOME;rm -rf x"])
def test_quote_remote_survives_both_shells(path):
    """Test that a quoted path is a single, unchanged argument on the device.
    The local shell splits the command, adb joins the arguments after `shell`
    with spaces, and the device's shell splits the result again."""
    local_args = shlex.split(f"adb shell rm {quote_remote(path)}")
    remote_args = shlex.split(" ".join(local_args[2:]))
    assert remote_args == ["rm", path]
