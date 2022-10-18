.. default-role:: code

reddroidvid
===========

Monitor and record video from Android devices remotely, pulling, renaming, and
optionally previewing the videos when recording stops.  Has very basic integration
capability with DAW software (Ardour is currently the default setting).

Currently only works over USB (via the ADB interface).  Only tested with
OpenCamera on Android, controlled from Linux.  (Windows could work in
principle, but there are various Linux-specific commands which would need to be
replaced.) No attempt is made to unlock a locked phone.

Disclaimer:  This is beta-level software that works for what I need it to do.
It is, however, written fairly generally to be customizable.

Screenshot of the program being used to record music a performance:

.. image:: https://github.com/abarker/recdroidvid/blob/main/doc/rdv_screenshot_example.png
    :width: 500px
    :align: center
    :alt: [screenshot of recdroidvid in action]

Installation
============

The easiest way to install the basic program is to install from PyPI using pip:

.. code-block:: bash

   pip install recdroidvid

Dependencies
============

The required and optional dependencies are described below.

scrcpy
------

The scrcpy program needs to be installed and set up to be runnable via USB.  It
functions as the computer-screen monitor for what is being recorded on the
phone.  (All the actual recording is done on the phone, however.) The program
is available in many linux repos, or can be compiled from the scrcpy site
at https://github.com/Genymobile/scrcpy.

On Ubuntu the command to install from the repos is:

.. code-block:: bash

    sudo apt install scrcpy

Installing via snap is also possible (and may be a more recent version):

.. code-block:: bash

    sudo snap install scrcpy
    snap connect scrcpy:camera

Setup requires that developer mode be activated on the mobile device to allow
ADB commands via USB:

- Go to ``Settings > About phone`` and tap the ``Build number`` at the bottom
  seven times to activate developer mode.

- Then go to ``Settings > System > Advanced > Developer Options`` and turn on
  USB debugging.

- Connect the mobile device via USB and authorize it on the Android
  notification.

See the scrcpy Github page for more information.  Use ``scrcpy --help | more``
for information about the available options.

ffmpeg
------

The ffmpeg program is used to print out information about the pulled movies, as
well as to optionally extract audio from the video files:

.. code-block:: bash

    sudo apt install ffmpeg

previewing
----------

Previewing by default assumes the mpv movie player is installed (though there is an
option to set any movie player program from the command line):

.. code-block:: bash

    sudo apt install mpv

Options and Customization
=========================

.. In vim use this to get output:
       :read !recdroidvid -h

To see the command-line options, run ``recdroidvid --help | more``.  The output
of that command follows.  Note that any options can also be set in the config
file `~/.recdroidvid_rc.py`.  The file will be imported and the strings on the
list `rdv_options` will be used as the default command-line options.  See the
example config file.

   usage: recdroidvid [-h] [--scrcpy-cmd CMD-STRING] [--numbering-start INTEGER]
                      [--loop] [--autorecord] [--preview-video]
                      [--preview-video-cmd CMD-STRING]
                      [--preview-video-cmd-jack CMD-STRING]
                      [--date-and-time-in-video-name]
                      [--sync-daw-transport-with-video-recording]
                      [--toggle-daw-transport-cmd CMD-STRING]
                      [--add-daw-mark-on-transport-start]
                      [--add-daw-mark-cmd CMD-STRING]
                      [--raise-daw-on-camera-app-open]
                      [--raise-daw-on-transport-toggle]
                      [--raise-daw-to-top-cmd CMD-STRING]
                      [--is-daw-running-cmd CMD-STRING] [--audio-extract]
                      [--camera-save-dir DIRPATH]
                      [--camera-package-name PACKAGENAME]
                      [--config-conditional STRING]
                      [PREFIXSTRING]

   Record a video on mobile via ADB and pull result. All config options can be
   set in a file `.recdroidvid_rc.py`. The file is evaluated and the list
   `rdv_options` in the file is used as the options list. See the example config
   file.

   positional arguments:
     PREFIXSTRING          The basename or prefix of the pulled video file.
                           Whether name or prefix depends on the method used to
                           record.

   optional arguments:
     -h, --help            show this help message and exit
     --scrcpy-cmd CMD-STRING, -y CMD-STRING
                           The command, including arguments, to be used to launch
                           the scrcpy program. Otherwise a default version is
                           used with some common arguments. Note that the string
                           `--window-title=RDV_SCRCPY_TITLE` can be used to
                           substitute-in a more descriptive title for the window.
     --numbering-start INTEGER, -n INTEGER
                           The number at which to start numbering pulled videos.
                           The number is currently appended to the user-defined
                           prefix and defaults to 1. Allows for restarting and
                           continuing a naming sequence across invocations of the
                           program.
     --loop, -l            Loop the recording, querying between invocations of
                           `scrcpy` as to whether or not to continue. This allows
                           for shutting down the scrcpy display to save both
                           local CPU and remote device memory (videos are
                           downloaded and deleted from the device at the end of
                           each loop), but then restarting with the same options.
                           Video numbering (as included in the filename) is
                           automatically incremented over all the videos, across
                           loops.
     --autorecord, -a      Automatically start recording when the scrcpy monitor
                           starts up.
     --preview-video, -p   Preview each video that is downloaded. Currently uses
                           the mpv program.
     --preview-video-cmd CMD-STRING
                           The command used to invoke a movie player to view the
                           preview. The default uses the mpv movie viewer. The
                           string 'RDV_PREVIEW_FILENAME', if present in the
                           command, will be replaced with the title of the video
                           being previewed.
     --preview-video-cmd-jack CMD-STRING
                           The command used to invoke a movie player to view the
                           preview when the jack audio system is detected to be
                           running. The default uses the mpv movie viewer. The
                           string 'RDV_PREVIEW_FILENAME', if present in the
                           command, will be replaced with the title of the video
                           being previewed.
     --date-and-time-in-video-name, -t
                           Include the date and time in the video names in a
                           readable format.
     --sync-daw-transport-with-video-recording, -s
                           Start the DAW transport when video recording is
                           detected on the mobile device. May increase CPU loads
                           on the computer and the mobile device.
     --toggle-daw-transport-cmd CMD-STRING
                           A system command to toggle the DAW transport. Used
                           when the `--sync-to-daw` option is chosen. The default
                           uses xdotool to send a space-bar character to Ardour.
     --add-daw-mark-on-transport-start, -m
                           Whether to add a mark in the DAW when the transport
                           starts, to help in syncing with the video.
     --add-daw-mark-cmd CMD-STRING
                           A system command to add a mark to the DAW at the
                           playhead. The default uses xdotool to send a tab
                           character to Ardour.
     --raise-daw-on-camera-app-open, -q
                           Raise the DAW to the top of the window stack when the
                           camara app is opened on the mobile device. Works well
                           when scrcpy is also passed the `--always-on-top`
                           option.
     --raise-daw-on-transport-toggle, -r
                           Raise the DAW to the top of the window stack whenever
                           the DAW transport is toggled by the `--sync-to-daw`
                           option. Works well when scrcpy is also passed the
                           `--always-on-top` option.
     --raise-daw-to-top-cmd CMD-STRING
                           A system command to raise the DAW windows to the top
                           of the window stack. Used when either of the
                           `--raise_daw_on_camera_app_open` or `--raise-daw-on-
                           transport-toggle` options are selected. The default
                           uses xdotool to activate any Ardour windows.
     --is-daw-running-cmd CMD-STRING
                           A system command to test if the DAW is actually
                           running. A zero return code means it is, and a nonzero
                           return code means it isn't.
     --audio-extract, -w   Extract a separate audio file (currently always a WAV
                           file) from each video.
     --camera-save-dir DIRPATH, -d DIRPATH
                           The directory on the remote device where the camera
                           app saves videos. Record a video and look at the
                           information about the video to find the path. Defaults
                           to the OpenCamera default save directory.
     --camera-package-name PACKAGENAME, -c PACKAGENAME
                           The Android package name of the camera app. Defaults
                           to "net.sourceforge.opencamera", the OpenCamera
                           package name. Look in the URL of the app's PlayStore
                           web site to find this string.
     --config-conditional STRING
                           The `.recdroidvid_rc.py` config file contains
                           interpreted Python code, so conditionals can be set
                           for different use-cases. This option allows one to set
                           a string value from the command line which can then be
                           used to choose a case in the config file. To set such
                           a variable, pass the value to this option. The default
                           value is the string "default". To access this
                           variable, use `from recdroidvid import
                           config_conditional` at the top of the config file.
