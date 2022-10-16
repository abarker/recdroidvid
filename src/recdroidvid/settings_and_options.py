"""

Fixed options and command-line options.

Note: The keycodes for xdotool.
   https://gitlab.com/cunidev/gestures/-/wikis/xdotool-list-of-key-codes

"""

# NOTE: To find this path, look at the info from an OpenCamera video saved on the phone.
OPENCAMERA_SAVE_DIR = "/storage/emulated/0/DCIM/OpenCamera/" # Where OpenCamera writes video.
OPENCAMERA_PACKAGE_NAME = "net.sourceforge.opencamera" # Look in URL of PlayStore page to find.

VIDEO_FILE_EXTENSION = ".mp4"

# The default command-line args passed to scrcpy.
# Note the title macro is substituted-in later.
SCRCPY_CMD_DEFAULT = ["scrcpy", "--stay-awake",
                                "--disable-screensaver",
                                "--display-buffer=20",
                                "--window-title=RDV_SCRCPY_TITLE",
                                "--always-on-top",
                                "--rotation=0",
                                "--max-size=1200",
                                "--lock-video-orientation=initial",]

BASE_VIDEO_PLAYER_CMD = ["mpv", "--loop=inf",
                                "--autofit=1080", # Set the width of displayed video.
                                #"--geometry=50%:70%", # Set initial position on screen.
                                #"--autosync=30",
                                "--cache=yes",
                                "--osd-duration=200",
                                "--osd-bar-h=0.5",
                                #"--really-quiet", # Turn off when debugged; masks errors.
                                f"--title='{'='*8} VIDEO PREVIEW: RDV_PREVIEW_FILENAME {'='*40}'"]

VIDEO_PLAYER_CMD = BASE_VIDEO_PLAYER_CMD # + ["--ao=sdl"]
VIDEO_PLAYER_CMD_JACK = VIDEO_PLAYER_CMD + ["--ao=jack"]

#DETECT_JACK_PROCESS_NAMES = [" qjackctl "] # Search `ps -ef` for these to detect Jack running.
DETECT_JACK_CMD = "jack_lsp -A" # Cmd to detect jack; nonzero return code if not running.

QUERY_PREVIEW_VIDEO = False # Ask before previewing video.
QUERY_EXTRACT_AUDIO = False # Ask before extracting AUDIO file.

EXTRACTED_AUDIO_EXTENSION = ".wav"

IS_DAW_RUNNING_CMD = 'xdotool search --onlyvisible --class Ardour'
TOGGLE_DAW_TRANSPORT_CMD = 'xdotool key --window "$(xdotool search --onlyvisible --class Ardour | head -1)" space'
#TOGGLE_DAW_TRANSPORT_CMD = 'xdotool windowactivate "$(xdotool search --onlyvisible --class Ardour | head -1)"'

ADD_DAW_MARK_CMD = 'xdotool key --window "$(xdotool search --onlyvisible --class Ardour | head -1)" Tab'

RAISE_DAW_TO_TOP_CMD = "xdotool search --onlyvisible --class Ardour windowactivate %@"

SYNC_DAW_SLEEP_TIME = 4 # Lag between video on/off & DAW transport sync (load/time tradeoff)

#RECORD_DETECTION_METHOD = "directory size increasing" # More general but requires two calls.
RECORD_DETECTION_METHOD = ".pending filename prefix" # May be specific to OpenCamera implemetation.

# This option records with the ADB screenrecord command.  It is limited to the
# screen's resolution(?) and 3 minutes, with no sound.  It is no longer tested
# and will be removed at some point.  https://stackoverflow.com/questions/21938948/
USE_SCREENRECORD = False # DEPRECATED.

POSTPROCESS_VIDEOS = False
POSTPROCESSING_CMD = [] # Enter cmd as separate string arguments.

RECDROIDVID_PYTHON_RC_FILENAME = ".recdroidvid_rc.py"

import sys
import os
import argparse
#import ast
import shutil
import tempfile

args_list = [] # A mutable container to hold the parsed arguments.

def args():
    """Return the parsed arguments.  The `parse_command_line` function must be called
    first."""
    # Note: Running `parse_command_line` at module import time would allow the
    # use of a global var `args` rather than a function `args()`.  Which is preferable?
    # Do you always want to parse the command-line args, or just sometimes when main calls
    # `parse_command_line`?
    if not args_list:
        print("ERROR: Command-line arguments have not been parsed.", file=sys.stderr)
        raise IndexError
    return args_list[0]

def fmt(text):
    """Format text for nicer-looking help messages."""
    # https://docs.python.org/3/library/textwrap.html
    import textwrap
    text_lines = textwrap.wrap(textwrap.dedent(text), width=70)
    print(text_lines)
    text = "\n".join(text_lines) + "\n\n"
    print(text)
    return text

def parse_command_line():
    """Create and return the argparse object to read the command line."""

    parser = argparse.ArgumentParser(
                        prog="recdroidvid",
                        #formatter_class=argparse.RawTextHelpFormatter,
                        #formatter_class=argparse.RawDescriptionHelpFormatter,
                        description=

                        """Record a video on mobile via ADB and pull result.  All config
                        options can be set in a file `.recdroidvid_rc.py`.  The file is
                        evaluated and the list `rdv_options` in the file is used as the
                        options list.  See the example config file.""")

    parser.add_argument("video_file_prefix", type=str, nargs="?", metavar="PREFIXSTRING",
                        default="rdv", help="""The basename or prefix of the pulled video
                        file.  Whether name or prefix depends on the method used to
                        record.""")

    parser.add_argument("--scrcpy-cmd", "-y", type=str, nargs=1, metavar="CMD-STRING",
                        default=[" ".join(SCRCPY_CMD_DEFAULT)], help="""The command,
                        including arguments, to be used to launch the scrcpy program.
                        Otherwise a default version is used with some common arguments.
                        Note that the string `--window-title=RDV_SCRCPY_TITLE` can be used
                        to substitute-in a more descriptive title for the window.""")

    parser.add_argument("--numbering-start", "-n", type=int, nargs=1, metavar="INTEGER",
                        default=[1], help="""The number at which to start numbering
                        pulled videos.  The number is currently appended to the user-defined
                        prefix and defaults to 1.  Allows for restarting and continuing
                        a naming sequence across invocations of the program.""")

    parser.add_argument("--loop", "-l", action="store_true",
                        default=False, help="""Loop the recording, querying between
                        invocations of `scrcpy` as to whether or not to continue.  This
                        allows for shutting down the scrcpy display to save both
                        local CPU and remote device memory (videos are downloaded and
                        deleted from the device at the end of each loop), but then
                        restarting with the same options.  Video numbering (as
                        included in the filename) is automatically incremented over
                        all the videos, across loops.""")

    parser.add_argument("--autorecord", "-a", action="store_true",
                        default=False, help="""Automatically start recording when the scrcpy
                        monitor starts up.""")

    parser.add_argument("--preview-video", "-p", action="store_true",
                        default=False, help="""Preview each video that is downloaded.
                        Currently uses the mpv program.""")

    parser.add_argument("--preview-video-cmd", type=str, nargs=1, metavar="CMD-STRING",
                        default=[" ".join(VIDEO_PLAYER_CMD)], help="""The command used to
                        invoke a movie player to view the preview.  The default
                        uses the mpv movie viewer.  The string 'RDV_PREVIEW_FILENAME', if
                        present in the command, will be replaced with the title of the
                        video being previewed.""")

    parser.add_argument("--preview-video-cmd-jack", type=str, nargs=1, metavar="CMD-STRING",
                        default=[" ".join(VIDEO_PLAYER_CMD_JACK)], help="""The command used to
                        invoke a movie player to view the preview when the jack audio
                        system is detected to be running.  The default uses the mpv
                        movie viewer.  The string 'RDV_PREVIEW_FILENAME', if
                        present in the command, will be replaced with the title of the
                        video being previewed.""")

    parser.add_argument("--date-and-time-in-video-name", "-t", action="store_true",
                        default=False, help="""Include the date and time in the video names
                        in a readable format.""")

    parser.add_argument("--sync-daw-transport-with-video-recording", "-s", action="store_true",
                        default=False, help="""Start the DAW transport when
                        video recording is detected on the mobile device.  May increase
                        CPU loads on the computer and the mobile device.""")

    parser.add_argument("--toggle-daw-transport-cmd", type=str, nargs=1, metavar="CMD-STRING",
                        default=[TOGGLE_DAW_TRANSPORT_CMD], help="""A system command to toggle the
                        DAW transport.  Used when the `--sync-to-daw` option is chosen.  The
                        default uses xdotool to send a space-bar character to Ardour.""")

    parser.add_argument("--add-daw-mark-on-transport-start", "-m", action="store_true",
                        default=False, help="""Whether to add a mark in the DAW when the
                        transport starts, to help in syncing with the video.""")

    parser.add_argument("--add-daw-mark-cmd", type=str, nargs=1, metavar="CMD-STRING",
                        default=[ADD_DAW_MARK_CMD], help="""A system command to add
                        a mark to the DAW at the playhead.  The default uses xdotool to send
                        a tab character to Ardour.""")

    parser.add_argument("--raise-daw-on-camera-app-open", "-q", action="store_true",
                        default=False, help="""Raise the DAW to the top
                        of the window stack when the camara app is opened on the mobile device.
                        Works well when scrcpy is also passed the `--always-on-top` option.""")

    parser.add_argument("--raise-daw-on-transport-toggle", "-r", action="store_true",
                        default=False, help= """Raise the DAW to the top of the window
                        stack whenever the DAW transport is toggled by the `--sync-to-daw`
                        option.  Works well when scrcpy is also passed the
                        `--always-on-top` option.""")

    parser.add_argument("--raise-daw-to-top-cmd", type=str, nargs=1, metavar="CMD-STRING",
                        default=[RAISE_DAW_TO_TOP_CMD], help="""A system command to raise the
                        DAW windows to the top of the window stack.  Used when either of the
                        `--raise_daw_on_camera_app_open` or `--raise-daw-on-transport-toggle`
                        options are selected.  The default uses xdotool to activate any Ardour
                        windows.""")

    parser.add_argument("--is-daw-running-cmd", type=str, nargs=1, metavar="CMD-STRING",
                        default=[IS_DAW_RUNNING_CMD], help="""A system command to test if
                        the DAW is actually running.  A zero return code means it is, and
                        a nonzero return code means it isn't.""")

    parser.add_argument("--audio-extract", "-w", action="store_true", default=False,
                        help="""Extract a separate audio file (currently always a WAV file)
                        from each video.""")

    parser.add_argument("--camera-save-dir", "-d", type=str, nargs=1, metavar="DIRPATH",
                        default=[OPENCAMERA_SAVE_DIR], help="""The directory on the remote
                        device where the camera app saves videos.  Record a video and look
                        at the information about the video to find the path.   Defaults
                        to the OpenCamera default save directory.""")

    parser.add_argument("--camera-package-name", "-c", type=str, nargs=1, metavar="PACKAGENAME",
                        default=[OPENCAMERA_PACKAGE_NAME], help="""The Android package name of
                        the camera app.  Defaults to "net.sourceforge.opencamera", the
                        OpenCamera package name.  Look in the URL of the app's PlayStore
                        web site to find this string.""")

    parser.add_argument("--config-conditional", type=str, nargs=1, metavar="STRING",
                        default=["default"], help="""The `.recdroidvid_rc.py` config file
                        contains interpreted Python code, so conditionals can be set for different
                        use-cases.  This option allows one to set a string value from the command
                        line which can then be used to choose a case in the config file.  To set
                        such a variable, pass the value to this option.  The default value is
                        the string "default".  To access this variable, use
                        `from recdroidvid import config_conditional` at the top of the config
                        file.
                        """)

    # Set the variable for the `--config-conditional` option, based ONLY on cmdline args.
    parsed_cmdline_only_args = parser.parse_args()
    import recdroidvid as rdv
    if parsed_cmdline_only_args.config_conditional:
        rdv.config_conditional = parsed_cmdline_only_args.config_conditional[0]
    else:
        rdv.config_conditional = "default"

    # Now parse the commandline again, with the combined config args and cmdline args.
    rc_file_args = read_python_rc_file()
    #rc_file_args = read_rc_file()
    combined_args = rc_file_args + sys.argv[1:]
    parsed_args = parser.parse_args(args=combined_args)

    # Reset the module-scope list args_list to contain the parsed args object (where the
    # `args()` function will be able to access it).
    args_list.clear()
    args_list.append(parsed_args)

    return parsed_args

#def read_rc_file():
#    """Read and parse the ~/.recdroidvid_rc file."""
#    rc_path = os.path.abspath(os.path.expanduser("~/.recdroidvid_rc"))
#    if not os.path.isfile(rc_path):
#        return []
#
#    with open(rc_path, "r", encoding="utf-8") as f:
#        text = f.read()
#
#    try:
#        args_list = ast.literal_eval("[" + text + "]")
#    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
#        print(f"\nError parsing ~/.recdroidvid_rc:\n   ", e, file=sys.stderr)
#        print("\nExiting.")
#        sys.exit()
#
#    for a in args_list: # Make sure everything evaluated as a string.
#        if not isinstance(a, str):
#            print(f"\nError parsing ~/.recdroidvid_rc: The option or value '{a}' is not "
#                    "a quoted string.", file=sys.stderr)
#            print("\nExiting.")
#            sys.exit(1)
#
#    return args_list

def read_python_rc_file():
    """Read and parse the ~/.recdroidvid_rc.py file."""
    rc_path = os.path.abspath(os.path.join(os.path.expanduser("~"),
                              RECDROIDVID_PYTHON_RC_FILENAME))
    if not os.path.isfile(rc_path):
        return []

    module_filename = RECDROIDVID_PYTHON_RC_FILENAME[1:] # Remove the dot.
    module_name = RECDROIDVID_PYTHON_RC_FILENAME[1:-3] # Remove the dot and .py extension.
    with tempfile.TemporaryDirectory() as tmpdirname:
        shutil.copyfile(rc_path,
                os.path.join(tmpdirname, module_filename))
        sys.path.insert(1, tmpdirname)

        try:
            rc_options_module = __import__(module_name)
        except ImportError:
            print(f"\n\nERROR: RC file at '{rc_path}' raised an error on import:\n\n",
                  file=sys.stderr)
            raise
        finally:
            del sys.path[1]

    return rc_options_module.rdv_options

