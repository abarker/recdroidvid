.. default-role:: code

reddroidvid
===========

Monitor and record video from Android devices remotely, and pulling and
renaming the videos when recording stops.

Currently only works over USB (via ADB).  Only tested with OpenCamera on
Android controlled from Linux.  (Windows should work in principle, but there
are some Linux-specific commands that would need to be replaced.)

Installation
============

The easiest way to install the basic program is to install from PyPI using pip:

.. code-block:: bash

   pip install recdroidvid

Then be sure that all the dependencies are installed.

scrcpy
------

This program needs to be installed and set up to be runnable via USB.  This means
you need to connect the mobile device via USB and set it up in developer mode
to allow ADB commands.

https://github.com/Genymobile/scrcpy

