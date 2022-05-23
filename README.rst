.. default-role:: code

reddroidvid
===========

Monitor and record video from Android devices remotely, pulling, renaming, and
optionally previewing the videos when recording stops.

Currently only works over USB (via ADB).  Only tested with OpenCamera on
Android controlled from Linux.  (Windows should work in principle, but there
are some Linux-specific commands that would need to be replaced.)

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
functions as the computer-screen monitor for what is being recorded on the phone.
The program is available in many linux repos, or can be compiled from the scrcpy
site (https://github.com/Genymobile/scrcpy).

On Ubuntu the command using apt is:

.. code-block:: bash

    sudo apt install scrcpy

Installing via snap is also possible (and may be a more recent version):

.. code-block:: bash

    sudo snap install scrcpy
    snap connect scrcpy:camera

Setup requires that developer mode be activated on the mobile device to allow
ADB commands via USB:

- Go to ``Settings > > About phone`` and tap the ``Build number`` at the bottom
  seven times to activate developer mode.

- Then go to ``Settings > System > Advanced > Developer Options`` and turn on
  USB debugging.

- Connect the mobile device via USB.

See the scrcpy Github page for more information.

ffmpeg
------

This is used to print out information about the pulled movies, as well as to optionally
extract audio from the video files:

.. code-block:: bash

    sudo apt install ffmpeg

previewing
----------

Previewing by default assumes the mpv movie player is installed (though there is an
option to set any movie player program from the command line):

.. code-block:: bash

    sudo apt install mpv

