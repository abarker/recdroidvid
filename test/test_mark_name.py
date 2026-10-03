"""Tests for generating the names of DAW marks."""

import datetime

from recdroidvid.recdroidvid_main import generate_mark_name

NOW = datetime.datetime(2026, 10, 3, 11, 58, 2)

def test_mark_name_without_date():
    """Test that the mark name is the prefix and the zero-padded video number."""
    assert generate_mark_name("rdv", 3, False, now=NOW) == "rdv_03"

def test_mark_name_with_date():
    """Test that the date is appended in the same format as in the video names."""
    assert generate_mark_name("rdv", 3, True, now=NOW) == "rdv_03_2026-10-03"

def test_mark_name_matches_start_of_video_name():
    """Test that the mark name matches the start of a saved video's name."""
    video_name = "rdv_02_2026-10-03_11.58.02_VID_20261003_114910.mp4"
    assert video_name.startswith(generate_mark_name("rdv", 2, True, now=NOW))

def test_mark_name_large_number():
    """Test that numbers past 99 are not truncated."""
    assert generate_mark_name("take", 123, False) == "take_123"
