History
=======

0.2.0 (2026-10-03)
------------------

* The DAW (Ardour) is now controlled by sending OSC messages with the
  ``oscsend`` program instead of sending keystrokes with xdotool.  This works
  with Ardour 9, where the keystrokes could be captured by a dialog.  OSC must
  be enabled in Ardour, and the liblo-tools package must be installed.  See the
  README.

* DAW marks are now named to match the start of the saved video names, such as
  ``rdv_03_2026-10-03``.

* Version numbers made consistent.  The 0.1.0 release on PyPI was an older
  (2022) release, uploaded before 0.0.3.

0.0.3 (2025-12-11)
------------------

Update some scrcpy option names which were renamed in the scrcpy program.  Now
works with scrcpy version 3.3.2.

0.0.2 (2023)
------------

New features:

* New options to select.

* Color printing of output added.

0.0.1
-----

First release.

