"""Test that the example config file works with the option parser."""

import os
import sys
import runpy

from recdroidvid import settings_and_options

EXAMPLE_RC_PATH = os.path.join(os.path.dirname(__file__), "..", "examples",
                               "recdroidvid_rc.py")

def test_example_config_parses(monkeypatch):
    """Test that the options in the example config file are all accepted."""
    rdv_options = runpy.run_path(EXAMPLE_RC_PATH)["rdv_options"]
    monkeypatch.setattr(settings_and_options, "read_python_rc_file", lambda: rdv_options)
    monkeypatch.setattr(sys, "argv", ["recdroidvid"])

    args = settings_and_options.parse_command_line()

    assert args.wait_loop and args.loop # The wait-loop option implies loop.
    assert args.sync_daw_transport_with_video_recording
    assert args.scrcpy_cmd[0].startswith("scrcpy ")
