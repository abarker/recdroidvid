#!/usr/bin/python3
"""

Usage: recdroidvid.py

Be sure to install scrcpy and set phone to allow for ADB communication over
USB.  See the video recording notes in ardour directory for details.

Note: Phone cannot be powered down.

"""

# TODO:::: Do we really have TWO numbers to keep track of????   Each video is
# like 001.020 where you are incrementing over both invocations of scrcpy AND
# the individual pulls (stops and starts) associated with each invocation???
# Need to document and update the numbering.

# TODO: Maybe improve sync of the multiprocessing by having a shared var (or use
# threading if no shared vars)

# TODO: scrcpy always in center

VERSION = "0.1.0"

# NOTE: To find this path, look at the info from an OpenCamera video saved on the phone.
OPENCAMERA_SAVE_DIR = "/storage/emulated/0/DCIM/OpenCamera/" # Where OpenCamera writes video.
OPENCAMERA_PACKAGE_NAME = "net.sourceforge.opencamera"

VIDEO_FILE_EXTENSION = ".mp4"
AUTO_START_RECORDING = False

# Extra command-line args passed to scrcpy, in addition to those passed in from
# the command line.  Some useful ones: --always-on-top --max-size=1200
# --rotation=0 --lock-video-orientation=initial --stay-awake
# --disable-screensaver --display-buffer=50
SCRCPY_EXTRA_COMMAND_LINE_ARGS = ("--stay-awake --disable-screensaver --display-buffer=50 "
                                  "--power-off-on-close --window-y=440 --window-height=540 ")

#VIDEO_PLAYER_CMD = "pl"
#VIDEO_PLAYER_CMD_JACK = "pl --jack"
BASE_VIDEO_PLAYER_CMD = ["mpv", "--loop=inf",
                                "--autofit=1080", # Set the width of displayed video.
                                "--geometry=50%:70%", # Set initial position on screen.
                                "--autosync=30", "--cache=yes",
                                "--osd-duration=200",
                                "--osd-bar-h=0.5",
                                #"--really-quiet",  # Turn off when debugged; masks errors.
                                f"--title='{'='*40} VIDEO PREVIEW {'='*40}'"]

VIDEO_PLAYER_CMD = BASE_VIDEO_PLAYER_CMD + ["--ao=sdl"]
VIDEO_PLAYER_CMD_JACK = VIDEO_PLAYER_CMD + ["--ao=jack"]
DETECT_JACK_PROCESS_NAMES = ["qjackctl"] # Search `ps -ef` for these to detect Jack running.

DATE_AND_TIME_IN_VIDEO_NAME = True
PREVIEW_VIDEO = True
QUERY_PREVIEW_VIDEO = False

EXTRACT_AUDIO = False # Whether to ever extract a AUDIO file from the video.
QUERY_EXTRACT_AUDIO = False # Ask before extracting AUDIO file.
EXTRACTED_AUDIO_EXTENSION = ".wav"

# TODO: Now, need to run a BG process that starts a popup always-on-top with a single toggle button.
# The button then starts ardour and calls adb to push record button when its button is pressed.
# Wish list: add a track marker at the spot.  Maybe xdotool could do it, calling menu item and
# entering the text???
TOGGLE_DAW_TRANSPORT_CMD = 'xdotool key --window "$(xdotool search --onlyvisible --class Ardour | head -1)" space'
#TOGGLE_DAW_TRANSPORT_CMD = 'xdotool windowactivate "$(xdotool search --onlyvisible --class Ardour | head -1)"'
RAISE_ARDOUR_TO_TOP = "xdotool search --onlyvisible --class Ardour windowactivate %@"

SYNC_DAW_TRANSPORT = False # Note this can increase CPU usage on computer and phone (polling).
SYNC_DAW_SLEEP_TIME = 4 # Lag between video on/off button and DAW transport syncing (load/time tradeoff)

# This option records with the ADB screenrecord command.  It is limited to
# screen resolution(?) and 3min, no sound.
# https://stackoverflow.com/questions/21938948/how-to-increase-time-limit-of-adb-screen-record-of-android-kitkat
# Deprecated and may be removed at some point.
USE_SCREENRECORD = False

POSTPROCESS_VIDEOS = False
POSTPROCESSING_CMD = [] # Enter cmd as separate string arguments.

import sys
import os
from time import sleep
import subprocess
import argparse
import datetime

YES_ANSWERS = {"Y", "y", "yes", "YES", "Yes"}
NO_ANSWERS = {"N", "n", "no", "NO", "No"}

#
# Android ADB commands.
#

def adb(cmd, print_cmd=True, return_stdout=False, return_stderr=False):
    """Run the ADB command, printing out diagnostics.  Setting `return_output`
    returns the stdout of the command, but the command must be redirectable to
    a temp file.  Returned string is a direct read, with no splitting."""
    # TODO: This should be done with subprocess.Popen, but it works.
    if print_cmd:
        print(f"\nCMD: {cmd}")

    if not (return_stdout or return_stderr):
        os.system(cmd)
        return

    tmp_adb_cmd_output_file = "zzzz_tmp_adb_cmd_output_file"
    if return_stdout and return_stderr:
        redirect = "1> 2>"
    elif return_stdout:
        redirect = ">"
    elif return_stderr:
        redirect = "2>"

    os.system(f"{cmd} {redirect} {tmp_adb_cmd_output_file}")
    with open(tmp_adb_cmd_output_file, "r") as f:
        cmd_output = f.read()
    os.remove(tmp_adb_cmd_output_file)
    return cmd_output

def adb_ls(path, all=False, extension_whitelist=None):
    """Run the ADB ls command and return the filenames time-sorted from oldest
    to newest.   If `all` is true the `-a` option to `ls` is used (which gets dotfiles
    too).  The `extension_whitelist` is an optional iterable of required file
    extensions such as `[".mp4"]`."""
    tmp_ls_path = "zzzz_tmp_adb_ls_path"
    # NOTE NOTE: `adb shell ls` is DIFFERENT FROM `adb ls`, you need also hidden files with
    # `shell adb` to get `.pending....mp4` files, and there are still a few more in `shell ls`.
    if all:
        ls_output = adb(f"adb shell ls -ctra {path}", return_stdout=True)
    else:
        ls_output = adb(f"adb shell ls -ctr {path}", return_stdout=True)
    ls_list = ls_output.splitlines()

    if extension_whitelist:
        for e in extension_whitelist:
            ls_output = [f for f in ls_output if f.endswith(e)]
    return ls_list

def adb_tap_screen(x, y):
    """Generate a screen tap at the given position."""
    #https://stackoverflow.com/questions/3437686/how-to-use-adb-to-send-touch-events-to-device-using-sendevent-command
    adb(f"adb shell input tap {x} {y}")

def adb_force_stop_opencamera():
    """Issue a force-stop command to OpenCamera app.  Note this made the Google
    camera open by default afterward with camera button."""
    adb("adb shell am force-stop net.sourceforge.opencamera")

def adb_tap_camera_button():
    """Tap the button in the camera to start it or stop it from recording."""
    adb(f"adb shell input keyevent 27")

def adb_toggle_power():
    """Toggle the power.  See also the `adb_device_wakeup` function."""
    adb("adb shell input keyevent KEYCODE_POWER")

def adb_device_wakeup():
    """Issue an ADB wakeup command."""
    # TODO: Maybe consolidate code with corresponding sleep command.
    output = adb(f"adb shell input keyevent KEYCODE_WAKEUP", return_stderr=True)
    if output.strip():
        print(output)
    if output.startswith("error: no devices"): # TODO: Maybe get exit code in adb function.
        print("ERROR: No devices found, is the phone plugged in via USB?", file=sys.stderr)
        sys.exit(1)
    sleep(2)

def adb_device_sleep():
    """Issue an ADB sleep command."""
    output = adb(f"adb shell input keyevent KEYCODE_SLEEP", return_stderr=True)
    if output.strip():
        print(output)
    if output.startswith("error: no devices"):
        print("ERROR: No devices found, is the phone plugged in via USB?", file=sys.stderr)
        sys.exit(1)
    sleep(2)

def adb_unlock_screen():
    """Swipes screen up, assuming no passcode."""
    # Note 82 is the menu key.
    #adb(f"adb shell input keyevent 82 && adb shell input keyevent 66")
    adb(f"adb shell input keyevent 82")
    sleep(1)

def adb_open_video_camera():
    """Open the video camera, rear facing."""
    # Note that the -W option waits for the launch to complete.

    # NOTE: Below line fails sometimes when opening the menu instead of camera???
    #adb("adb shell am start -W net.sourceforge.opencamera --ei android.intent.extras.CAMERA_FACING 0")

    # Below depends on the default camera app, above forces OpenCamera.
    #adb(f"adb shell am start -W -a android.media.action.VIDEO_CAMERA --ei android.intent.extras.CAMERA_FACING 0")

    # This command seems to avoid opening in a menu, etc., for now....
    # https://android.stackexchange.com/questions/171490/start-application-from-adb
    # https://stackoverflow.com/questions/4567904/how-to-start-an-application-using-android-adb-tools
    adb(f"adb shell am start -W -n {args.camera_package_name[0]}/.MainActivity --ei android.intent.extras.CAMERA_FACING 0")
    sleep(1)

def adb_directory_size_increasing(dirname, wait_secs=1):
    """Return true if the save directory is growing in size (i.e., file is being
    recorded there)."""
    DEBUG = False # Print commands to screen when debugging.
    first_du = adb(f"adb shell du {dirname}", print_cmd=DEBUG, return_stdout=True)
    first_du = first_du.split("\t")[0]
    sleep(wait_secs)
    second_du = adb(f"adb shell du {dirname}", print_cmd=DEBUG, return_stdout=True)
    second_du = second_du.split("\t")[0]
    return int(second_du) > int(first_du)

#
# Local machine startup functions.
#

def parse_command_line():
    """Create and return the argparse object to read the command line."""

    parser = argparse.ArgumentParser(
                    description="Record a video on mobile via ADB and pull result.")

    parser.add_argument("video_file_prefix", type=str, nargs="?", metavar="PREFIXSTRING",
                        default=["rdv"], help="""The basename or prefix of the pulled video
                        file.  Whether name or prefix depends on the method used to
                        record.""")

    parser.add_argument("--scrcpy-args", "-y", type=str, nargs=1, metavar="STRING-OF-ARGS",
                        default=[""], help="""An optional string of extra arguments to pass
                        directly to the `scrcpy` program.""")

    parser.add_argument("--numbering-start", "-n", type=int, nargs=1, metavar="INTEGER",
                        default=[1], help="""The number at which to start numbering
                        pulled videos.  The number is currently appended to the user-defined
                        prefix and defaults to 1.""")

    parser.add_argument("--loop", "-l", action="store_true",
                        default=False, help="""Loop the recording, querying between
                        invocations of `scrcpy` as to whether or not to continue.
                        Video numbering (as included in the filename) is incremented
                        on each loop.""")

    parser.add_argument("--autorecord", "-r", action="store_true",
                        default=AUTO_START_RECORDING, help="""Automatically start recording
                        when the scrcpy monitor starts up.""")

    parser.add_argument("--sync-to-daw", "-s", action="store_true",
                        default=SYNC_DAW_TRANSPORT, help="""Start the DAW transport when
                        video recording is detected on the mobile device.  May increase
                        CPU loads on the computer and the mobile device.""")

    parser.add_argument("--audio-extract", "-a", action="store_true",
                        default=EXTRACT_AUDIO, help="""Extract a separate audio file from
                        each video.""")

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

    cmdline_args = parser.parse_args()
    return cmdline_args

def print_startup_message():
    """Print out the initial greeting message."""
    print(f"{'='*78}")
    print(f"\nrecdroidvid, version {VERSION}")
    print(f"\n{'='*78}")

def detect_if_jack_running():
    """Determine if the Jack audio system is currently running; return true if it is."""
    ps_output = subprocess.check_output(["ps", "-ef"])
    ps_output = ps_output.decode("utf-8")
    ps_output = ps_output.splitlines()
    for p in ps_output:
        #print(p)
        for pname in DETECT_JACK_PROCESS_NAMES:
            if pname in p:
                return True
    return False

#
# Functions for syncing with DAW.
#

def toggle_daw_transport():
    """Toggle the transport state of the DAW.  Used to sync with recording."""
    os.system(TOGGLE_DAW_TRANSPORT_CMD)

def sync_daw_transport_when_video_recording():
    """Start the DAW transport when video recording is detected on the Android
    device.  Meant to be run as a thread or via multiprocessing to execute at the
    same time as the scrcpy monitor."""
    # TODO: Another way to do this might be to monitor the output of
    #     adb shell getevent -l
    # and look for a BTN_TOUCH DOWN followed by BTN_TOUCH UP
    # But, you'd need to continuously get the output.
    rolling = False
    while True:
        if not rolling and adb_directory_size_increasing(args.camera_save_dir[0]):
            toggle_daw_transport()
            rolling = True
        if rolling and not adb_directory_size_increasing(args.camera_save_dir[0]):
            toggle_daw_transport()
            rolling = False
        sleep(SYNC_DAW_SLEEP_TIME)

#
# Recording and monitoring functions.
#

def start_screenrecording():
    """Start screenrecording via the ADB `screenrecord` command.  This process is run
    in the background.  The PID is returned along with the video pathname."""
    video_out_basename = args.video_file_prefix[0]
    video_out_pathname =  os.path.join(args.camera_save_dir[0], f"{video_out_basename}.mp4")
    tmp_pid_path = f"zzzz_screenrecord_pid_tmp"
    adb_ls(os.path.dirname(video_out_pathname)) # DOESNT DO ANYTHING?? DEBUG?? TODO

    adb(f"adb shell screenrecord {video_out_pathname} & echo $! > {tmp_pid_path}")

    sleep(1)
    with open(tmp_pid_path, "r") as f:
        pid = f.read()
    os.remove(tmp_pid_path)
    sleep(10)

    #adb shell screenrecord --size 720x1280 /storage/emulated/0/DCIM/OpenCamera/$1.mp4 & # TODO takes --size, but messes it up, density??
    return pid, video_out_pathname

def start_screen_monitor(block=True):
    """Monitor only, blocking before kill of screen recording when shuts down."""
    # Note cropping is width:height:x:y  [currently FAILS as below, video comes out
    # broken too]
    #
    # https://old.reddit.com/r/sidequest/comments/ed9xzc/what_crop_number_should_i_enter_in_scrcpy_if_i/
    #    The syntax is: --crop width:height:x:y. So if you pass 1920:1080:1440:720, you
    #    want a video 1920×1080, starting at (1440,720) and ending at (3360, 1800)
    #    [Last coords are the offsets added to the first coords, as an ordered pair.]
    #
    # Actual is 1600x720 (in landscape) for phone screen, so 720:1280:0:160  (260 before, worked mostly...)
    #
    # Note that capturing full 1600x720 is possible, but below cropped to 16:9.

    # NOTE the lock-video-orientation seems to apply to recorded media, but --rotation seems to just
    # affect the computer preview display.  Had to fiddle with the combo to get both right-side-up.
    #
    # --lock-video-orientation[=value]
    #      Lock video orientation to value.
    #      Possible values are "unlocked", "initial" (locked to the initial
    #      orientation), 0, 1, 2 and 3. Natural device orientation is 0, and each
    #      increment adds a 90 degrees rotation counterclockwise.
    #      Default is "unlocked".
    #      Passing the option without argument is equivalent to passing "initial".

    # Uncropped.
    #scrcpy --record=$1.mp4 --record-format=mp4 --rotation=0 --lock-video-orientation=initial --stay-awake --disable-screensaver --display-buffer=50 --crop 720:1280:0:160 # --crop 720:1600:0:0

    # Cropped to 16:9.
    #scrcpy --record=$1.mp4 --record-format=mp4 --rotation=0 --lock-video-orientation=initial --stay-awake --disable-screensaver --display-buffer=50 --crop 720:1280:0:320 # --crop 720:1600:0:0
    if not block:
        print("Sorry, not implemented.")
        sys.exit(1)

    cmd = f"scrcpy {SCRCPY_EXTRA_COMMAND_LINE_ARGS} {args.scrcpy_args[0]}"
    print("\nSYSTEM:", cmd)
    os.system(cmd)

def start_monitoring_and_button_push_recording():
    """Emulate a button push to start and stop recording."""

    # Get a snapshot of save directory before recording starts.
    before_ls = adb_ls(args.camera_save_dir[0], extension_whitelist=[VIDEO_FILE_EXTENSION])

    if args.autorecord:
        adb_tap_camera_button()
        sleep(0.5)
        if False:
            # Note, this was the original way to get a single video but always starts
            # recording right away and only allows one video at a time to be recorded
            # before closing scrcpy.  It still works as an error check of sorts.
            after_ls = adb_ls(args.camera_save_dir[0], all=True, extension_whitelist=[VIDEO_FILE_EXTENSION])
            new_video_files = [f for f in after_ls if f not in before_ls]
            if len(new_video_files) > 1:
                print("\nWARNING: Found multiple new files in args.camera_save_dir[0].", file=sys.stderr)
            if not(new_video_files):
                print("\nERROR: No new video files found.  Is phone connected via USB?\n", file=sys.stderr)
            # Previously used lines below.
            # NOTE: Below line is needed to convert `.pending...mp4` files to the final fname.
            #video_basename = new_video_files[0].split("-")[-1]
            #video_path = os.path.join(args.camera_save_dir[0], video_basename)

    if args.sync_to_daw:
        # Better maybe, for clean end, use a stop flag and threading:  <== or use stop flag/w multiprocessing...
        # https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread
        # Replace multiprocessing with threading, but add args as in above link.
        # https://thispointer.com/python-how-to-create-a-thread-to-run-a-function-in-parallel/
        import multiprocessing
        proc = multiprocessing.Process(target=sync_daw_transport_when_video_recording, args=())
        proc.start()

    start_screen_monitor(block=True) # This blocks until the screen monitor is closed.

    if args.sync_to_daw:
        sleep(SYNC_DAW_SLEEP_TIME) # Give the process time to detect any final changes.
        proc.terminate()

    if adb_directory_size_increasing(args.camera_save_dir[0]):
        adb_tap_camera_button() # Presumably still recording; turn off the camera.
        if args.sync_to_daw:
            toggle_daw_transport() # Presumably the DAW transport is still rolling.
        while adb_directory_size_increasing(args.camera_save_dir[0]):
            print("Waiting for save directory to stop increasing in size...")
            sleep(1)

    # Get a final snapshot of save directory after recording is finished.
    after_ls = adb_ls(args.camera_save_dir[0], extension_whitelist=[VIDEO_FILE_EXTENSION])

    new_video_files = [f for f in after_ls if f not in before_ls]
    new_video_paths = [os.path.join(args.camera_save_dir[0], v) for v in new_video_files]
    return new_video_paths

def monitor_record_and_pull_videos(video_start_number):
    """Record a video on the Android device and pull the resulting file."""
    if USE_SCREENRECORD:
        recorder_pid, video_path = start_screenrecording(args)
        start_screen_monitor(block=True)
        os.system(f"kill {recorder_pid}")
        video_path = pull_and_delete_file(video_path) # TODO: does this work with preview??? Haven't tested...
        return [video_path]

    else: # Use the method requiring a button push on phone, emulated or actual.
        video_paths = start_monitoring_and_button_push_recording()
        new_video_paths = []
        sleep(5) # Make sure video files have time to finish writing and close.
        # TODO: Separate out the video naming to a function.
        for count, vid in enumerate(video_paths):
            pulled_vid = pull_and_delete_file(vid) # Note file always written to CWD for now.
            sleep(0.3)
            if DATE_AND_TIME_IN_VIDEO_NAME:
                date_time_string = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S_')
            else:
                date_time_string = ""
            new_vid_name = f"{args.video_file_prefix[0]}_{count+video_start_number:02d}_{date_time_string}{pulled_vid}"
            print(f"\nSaving (renaming) video file as\n   {new_vid_name}")
            os.rename(pulled_vid, new_vid_name)
            new_video_paths.append(new_vid_name)
        return new_video_paths

#
# Video postprocessing functions.
#

def pull_and_delete_file(pathname):
    """Pull the file at the pathname and delete the remote file.  Returns the
    path of the extracted video."""
    # Pull.
    adb(f"adb pull {pathname}")

    # Delete.
    sleep(4)
    adb(f"adb shell rm {pathname}")
    sleep(1)
    adb(f"adb -d shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:{pathname}")
    return os.path.basename(pathname)

def preview_video(video_path):
    """Run a preview of the video at `video_path`."""
    if not (PREVIEW_VIDEO or QUERY_PREVIEW_VIDEO):
        return

    def run_preview(video_path):
        """Run a preview of the video."""
        if detect_if_jack_running():
            print("\nDetected jack running via qjackctl.")
            cmd = VIDEO_PLAYER_CMD_JACK + [f"{video_path}"]
        else:
            print("\nDid not detect jack running via qjackctl.")
            cmd = VIDEO_PLAYER_CMD + [f"{video_path}"]
        print(f"\nRunning:", " ".join(cmd))
        subprocess.run(cmd) # This FAILS for some reason.

    if QUERY_PREVIEW_VIDEO:
        preview = input("\nRun preview? ")
        if preview.strip() in YES_ANSWERS:
            run_preview(video_path)
    else:
        print("\nRunning preview...")
        run_preview(video_path)

def extract_audio_from_video(video_path):
    """Extract the audio from a video file, of the type with the given extension."""
    # Note screen recording doesn't have audio, only the "button" method.
    if not ((args.audio_extract or QUERY_EXTRACT_AUDIO) and os.path.isfile(video_path)
                                                   and not USE_SCREENRECORD):
        return

    def run_audio_extraction(video_path, extension=".wav"):
        dirname, basename = os.path.split(video_path)
        root_name, video_extension = os.path.splitext(basename)
        output_audio_path = os.path.join(dirname, root_name + extension)
        print(f"\nExtracting audio to file: '{output_audio_path}'")
        # https://superuser.com/questions/609740/extracting-wav-from-mp4-while-preserving-the-highest-possible-quality
        cmd = f"ffmpeg -i {video_path} -map 0:a {output_audio_path} -loglevel quiet"
        print("  ", cmd)
        os.system(cmd)
        print("\nAudio extracted.")

    if QUERY_EXTRACT_AUDIO:
        extract_audio = input("\nExtract audio from video? ")
        if extract_audio.strip() in YES_ANSWERS:
            run_audio_extraction(video_path, extension=EXTRACTED_AUDIO_EXTENSION)
    else:
        run_audio_extraction(video_path, extension=EXTRACTED_AUDIO_EXTENSION)

def postprocess_video_file(video_path):
    """Run a postprocessing algorithm on the video file at `video_path`."""
    if not POSTPROCESS_VIDEOS or not os.path.isfile(video_path):
        return
    postprocess_cmd = POSTPROCESSING_CMD + [f"{video_path}"]
    print("\nRunning:", " ".join(postprocess_cmd))
    subprocess.run(postprocess_cmd)

def print_info_about_pulled_video(video_path):
    """Print out some information about the resolution, etc., of a video."""
    # TODO: Capture output and indent at least.  Print container stuff ahead of codecs
    # of the streams stuff.
    # Format: ffprobe -show_format -v error -of default=noprint_wrappers=1 {video_path} | grep -v 'TAG:'
    # Stream codecs: ffprobe -v error -show_entries stream=codec_name,width,height,duration,size,bit_rate -of default=noprint_wrappers=1 jam3_gategate_roses_v2.mp4
    # You can also separate the different stream codecs, but codec name should differentiate.
    #
    # To get JSON: ffprobe -v quiet -print_format json -show_format -show_streams "lolwut.mp4" > "lolwut.mp4.json"
    # In Python search for examples or use library: https://docs.python.org/3/library/json.html
    cmd = (f"ffprobe -pretty -show_format -v error -show_entries"
           f" stream=codec_name,width,height,duration,size,bit_rate"
           f" -of default=noprint_wrappers=1 {video_path} | grep -v 'TAG:'")
    print("\nRunning ffprobe on saved video file:") # TODO, refine info and maybe print better.
    os.system(cmd)

#
# Main.
#

def startup_device_and_run(video_start_number):
    """Main script functionality."""
    adb_device_sleep() # Get a consistent starting state for repeatability.
    adb_device_wakeup()
    adb_unlock_screen()
    adb_open_video_camera()

    video_paths = monitor_record_and_pull_videos(video_start_number)
    adb_device_sleep() # Put the device to sleep after use.

    for vid in video_paths:
        print(f"\n{'='*12} {vid} {'='*30}")
        print_info_about_pulled_video(vid)
        preview_video(vid)
        extract_audio_from_video(vid)
        postprocess_video_file(vid)

    video_end_number = video_start_number + len(video_paths) - 1
    return video_end_number

def main():
    """Outer loop over invocations."""
    video_start_number = args.numbering_start[0]
    print_startup_message()

    count = 0
    while True:
        count += 1
        video_end_number = startup_device_and_run(video_start_number)
        video_start_number = video_end_number + 1
        if not args.loop:
            break
        else:
            cont = query_yes_no(f"\nFinished recdroidvid loop {count}, continue? [ynq]: ")
            if not cont:
                break

def query_yes_no(query_string):
    """Query the user for a yes or no response."""
    yes_answers = {"y", "Y", "yes", "Yes"}
    no_answers = {"n", "N", "no", "No", "q", "Q", "quit", "Quit"}

    answer = False
    while True:
        response = input(query_string)
        response = response.strip()
        if not (response in yes_answers or response in no_answers):
            continue
        if response in yes_answers:
            answer = True
        break
    return answer

if __name__ == "__main__":

    args = parse_command_line() # Put `args` in global scope so all funs can use it.
    main()


