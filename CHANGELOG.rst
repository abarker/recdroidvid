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

* The DAW-running check now looks for an Ardour process instead of a visible
  Ardour window, so DAW syncing also works when Ardour is minimized or on
  another workspace.

* The ``--camera-package-name`` option is now used (it was ignored).

* The camera app no longer sometimes opens in its settings screen.  The menu
  key is no longer sent to dismiss the lock screen (it could reach OpenCamera,
  which opens its settings), and the camera app is now force-stopped before it
  is opened, so it always starts on its main screen.

* Filenames and the video prefix are now quoted in system and ADB commands,
  so a prefix with spaces works.

* Recording detection now works if the camera directory has subdirectories.

* Failing to get the video information with ffprobe now gives a warning
  instead of exiting.

* Python 3.8 or later is now required (this was already true of the code).

* Added an example config file, ``examples/recdroidvid_rc.py``, fixed the
  README screenshot link, and updated the docs.

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

