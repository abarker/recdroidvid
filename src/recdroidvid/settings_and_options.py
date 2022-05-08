"""

Fixed options and command-line options.

"""

# NOTE: To find this path, look at the info from an OpenCamera video saved on the phone.
OPENCAMERA_SAVE_DIR = "/storage/emulated/0/DCIM/OpenCamera/" # Where OpenCamera writes video.
OPENCAMERA_PACKAGE_NAME = "net.sourceforge.opencamera" # Look in URL of PlayStore page to find.

VIDEO_FILE_EXTENSION = ".mp4"

# The default command-line args passed to scrcpy.
# Note the title macro is substituted-in later.
SCRCPY_CMD_DEFAULT = ["scrcpy", "--stay-awake", "--disable-screensaver", "--display-buffer=50",
                                "--window-y=440", "--window-height=540",
                                "--window-title=RDB%SCRCPY-TITLE", "--always-on-top",
                                "--max-size=1200", "--rotation=0",
                                "--lock-video-orientation=initial"]

#VIDEO_PLAYER_CMD = "pl"
#VIDEO_PLAYER_CMD_JACK = "pl --jack"
BASE_VIDEO_PLAYER_CMD = ["mpv", "--loop=inf",
                                "--autofit=1080", # Set the width of displayed video.
                                "--geometry=50%:70%", # Set initial position on screen.
                                "--autosync=30", "--cache=yes",
                                "--osd-duration=200",
                                "--osd-bar-h=0.5",
                                #"--really-quiet",  # Turn off when debugged; masks errors.
                                f"--title='{'='*8} VIDEO PREVIEW: RDV%FILENAME {'='*40}'"]

VIDEO_PLAYER_CMD = BASE_VIDEO_PLAYER_CMD + ["--ao=sdl"]
VIDEO_PLAYER_CMD_JACK = VIDEO_PLAYER_CMD + ["--ao=jack"]

DETECT_JACK_PROCESS_NAMES = ["qjackctl"] # Search `ps -ef` for these to detect Jack running.

QUERY_PREVIEW_VIDEO = False # Ask before previewing video.
QUERY_EXTRACT_AUDIO = False # Ask before extracting AUDIO file.

EXTRACTED_AUDIO_EXTENSION = ".wav"

TOGGLE_DAW_TRANSPORT_CMD = 'xdotool key --window "$(xdotool search --onlyvisible --class Ardour | head -1)" space'
#TOGGLE_DAW_TRANSPORT_CMD = 'xdotool windowactivate "$(xdotool search --onlyvisible --class Ardour | head -1)"'

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

import sys
import os
import argparse
import ast

args_list = [] # Mutable containter to hold the parsed arguments.

def args():
    """Return the parsed arguments.  The `parse_command_line` function must be called
    first."""
    if not args_list:
        print("ERROR: Command-line arguments have not been parsed.", file=sys.stderr)
        raise IndexError
    return args_list[0]

def parse_command_line():
    """Create and return the argparse object to read the command line."""

    parser = argparse.ArgumentParser(
                        description="Record a video on mobile via ADB and pull result.")

    parser.add_argument("video_file_prefix", type=str, nargs="?", metavar="PREFIXSTRING",
                        default="rdv", help="""The basename or prefix of the pulled video
                        file.  Whether name or prefix depends on the method used to
                        record.""")

    parser.add_argument("--scrcpy-cmd", "-y", type=str, nargs=1, metavar="CMD-STRING",
                        default=[SCRCPY_CMD_DEFAULT], help="""The command, including
                        arguments, to be used to launch the scrcpy program.  Otherwise a
                        default version is used with some common arguments.  Note that
                        the string `--window-title=RDB%SCRCPY-TITLE` can be used to
                        substitute-in a more descriptive title for the window.""")

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
                        default=False, help="""Preview each video that is downloaded.   Currently
                        uses the mpv program.""")

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

    parser.add_argument("--raise-daw-on-camera-app-open", "-q", action="store_true",
                        default=False, help="""Raise the DAW to the top
                        of the window stack when the camara app is opened on the mobile device.
                        Works well when scrcpy is also passed the `--always-on-top` option.""")

    parser.add_argument("--raise-daw-on-transport-toggle", "-r", action="store_true",
                        default=False, help="""Raise the DAW to the top
                        of the window stack whenever the DAW transport is toggled by the `--sync-to-daw`
                        option.  Works well when scrcpy is also passed the `--always-on-top` option.""")

    parser.add_argument("--raise-daw-to-top-cmd", type=str, nargs=1, metavar="CMD-STRING",
                        default=[RAISE_DAW_TO_TOP_CMD], help="""A system command to raise the
                        DAW windows to the top of the window stack.  Used when either of the
                        `--raise_daw_on_camera_app_open` or `--raise-daw-on-transport-toggle`
                        options are selected.  The default uses xdotool to activate any Ardour
                        windows.""")

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

    rc_file_args = read_rc_file()
    #print("\nrc_file_args", rc_file_args) # DEBUG prints, remove when tested more.
    #print("\nsys.argv[1:]", sys.argv[1:])
    combined_args = rc_file_args + sys.argv[1:]
    #print("\ncombined args", combined_args)
    cmdline_args = parser.parse_args(args=combined_args)
    #print("\n--scrcpy_cmd", cmdline_args.scrcpy_cmd)
    args_list.clear()
    args_list.append(cmdline_args)
    return cmdline_args

def read_rc_file():
    """Read and parse the ~/.recdroidvid_rc file."""
    rc_path = os.path.abspath(os.path.expanduser("~/.recdroidvid_rc"))
    if not os.path.isfile(rc_path):
        return []

    with open(rc_path, "r", encoding="utf-8") as f:
        text = f.read()

    try:
        args_list = ast.literal_eval("[" + text + "]")
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as e:
        print(f"\nError parsing ~/.recdroidvid_rc:\n   ", e, file=sys.stderr)
        print("\nExiting.")
        sys.exit()

    for a in args_list: # Make sure everything evaluated as a string.
        if not isinstance(a, str):
            print(f"\nError parsing ~/.recdroidvid_rc: The option or value '{a}' is not "
                    "a quoted string.", file=sys.stderr)
            print("\nExiting.")
            sys.exit(1)

    return args_list

