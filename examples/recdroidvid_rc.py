# Example recdroidvid config file.  Copy it to `~/.recdroidvid_rc.py` and edit.
#
# The file can contain arbitrary Python code, which will be executed.  The
# value of the variable `rdv_options` is then used as the initial options to
# recdroidvid.  Any command-line options are applied after these, and override
# the same options here.  Run `recdroidvid --help` to see all the options.

# The `--config-conditional` option can be used to choose between different
# settings from the command line, for example:
#
#    from recdroidvid import config_conditional as case
#    if case == "default": ...

rdv_options = [

   "--wait-loop",

   "--date-and-time-in-video-name",

   # Start and stop recording in the DAW (Ardour, via OSC) along with the video.
   "--sync-daw-transport-with-video-recording",
   "--add-daw-mark-on-transport-start",

   # Raise the DAW window (uses xdotool).
   "--raise-daw-on-camera-app-open",
   "--raise-daw-on-transport-toggle",

   "--preview-video",

   # Python joins the indented strings below into a single string, so each
   # one needs a space at the end.  The string RDV_PREVIEW_FILENAME is replaced
   # with the name of the video.
   "--preview-video-cmd", "mpv "
                          "--loop=inf "
                          "--autofit=1080 "
                          "--geometry=50%:70% "
                          "--ontop "
                          "--title='PREVIEW: RDV_PREVIEW_FILENAME' ",

   # The preview command to use when the Jack audio system is running.
   "--preview-video-cmd-jack", "mpv "
                               "--loop=inf "
                               "--autofit=1080 "
                               "--geometry=50%:70% "
                               "--ontop "
                               "--title='PREVIEW: RDV_PREVIEW_FILENAME' "
                               "--ao=jack ",

   # The string RDV_SCRCPY_TITLE is replaced with the video file prefix.  Use
   # the full path to scrcpy if it is not on your PATH.
   "--scrcpy-cmd", "scrcpy "
                   "--stay-awake "
                   "--disable-screensaver "
                   "--video-buffer=50 "
                   "--window-title='RDV_SCRCPY_TITLE' "
                   "--always-on-top "
                   "--orientation=0 "
                   "--max-size=1200 ",
]
