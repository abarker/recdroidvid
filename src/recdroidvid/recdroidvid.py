#!/usr/bin/python3
"""

Usage: recdroidvid.py

Be sure to set phone to allow for ADB communication over USB.  See the video
recording notes in ardour directory for details.

Note: Phone cannot be powered down.

"""

# NOTE: Look at the info from an OpenCamera video saved on the phone to find this path.
OPENCAMERA_SAVE_DIR = "/storage/emulated/0/DCIM/OpenCamera/" # Where OpenCamera writes video.
OPENCAMERA_PACKAGE_NAME = "net.sourceforge.opencamera"

#RECORDING_METHOD = "screen" # Record with screenrecord; limited to screen resolution(?) and 3min, no sound.
# https://stackoverflow.com/questions/21938948/how-to-increase-time-limit-of-adb-screen-record-of-android-kitkat
RECORDING_METHOD = "button" # Record by emulating a button push and looking for new video file.
VIDEO_FILE_EXTENSION = ".mp4"
AUTO_START_RECORDING = False

SCRCPY_EXTRA_COMMAND_LINE_ARGS = "" #"--always-on-top --max-size=1200 --rotation=0 --lock-video-orientation=initial --stay-awake --disable-screensaver --display-buffer=50"

#VIDEO_PLAYER_CMD = "pl"
VIDEO_PLAYER_CMD = f"mplayer -loop 0 -really-quiet -title '{'='*40} VIDEO PREVIEW {'='*40}'"
#VIDEO_PLAYER_CMD_JACK = "pl --jack"
VIDEO_PLAYER_CMD_JACK = VIDEO_PLAYER_CMD + " -ao jack"
DETECT_JACK_PROCESS_NAMES = ["qjackctl"] # Search `ps -ef` for these to detect Jack running.

PREVIEW_VIDEO = True
QUERY_PREVIEW_VIDEO = False

AUDIO_EXTRACT = True # Whether to ever extract a AUDIO file from the video.
QUERY_AUDIO_EXTRACT = False # Ask before extracting AUDIO file.
EXTRACTED_AUDIO_EXTENSION = ".wav"

START_ARDOUR_TRANSPORT = 'xdotool key --window "$(xdotool search --onlyvisible --class Ardour | head -1)" space'

import sys
import os
from time import sleep
import subprocess
import argparse

YES_ANSWERS = {"Y", "y", "yes", "YES", "Yes"}
NO_ANSWERS = {"N", "n", "no", "NO", "No"}

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

def ls_diff(ls1, ls2):
    """Return the list of new files in ls2 that were not present in ls1."""

def adb_toggle_power():
    """Toggle the power.  See also the `wakeup_device` function."""
    adb("adb shell input keyevent KEYCODE_POWER")

def wakeup_device():
    """Unlock the screen without password."""
    output = adb(f"adb shell input keyevent KEYCODE_WAKEUP", return_stderr=True)
    if output.strip():
        print(output)
    if output.startswith("error: no devices"): # TODO: Maybe get exit code in adb function.
        print("ERROR: No devices found, is the phone plugged in via USB?", file=sys.stderr)
        sys.exit(1)
    sleep(2)

def unlock_screen():
    """Swipes screen up, assuming no passcode."""
    adb(f"adb shell input keyevent 82 && adb shell input keyevent 66")
    sleep(1)

def open_video_camera():
    """Open the video camera, rear facing."""
    # Note that the -W option waits for the launch to complete.

    # NOTE: Below line fails sometimes when opening the menu instead of camera???
    #adb("adb shell am start -W net.sourceforge.opencamera --ei android.intent.extras.CAMERA_FACING 0")

    # Below depends on the default camera app, above forces OpenCamera.
    #adb(f"adb shell am start -W -a android.media.action.VIDEO_CAMERA --ei android.intent.extras.CAMERA_FACING 0")

    # This command seems to avoid opening in a menu, etc., for now....
    # https://android.stackexchange.com/questions/171490/start-application-from-adb
    # https://stackoverflow.com/questions/4567904/how-to-start-an-application-using-android-adb-tools
    adb(f"adb shell am start -W -n {OPENCAMERA_PACKAGE_NAME}/.MainActivity --ei android.intent.extras.CAMERA_FACING 0")
    sleep(1)

def print_startup_message():
    print("="*70)
    print("\n(Make sure that OpenCamera is set to the native SCREEN resolution, 1600x720.)\n")
    print("="*70)

def start_screenrecording():
    """Start screenrecording via the ADB `screenrecord` command.  This process is run
    in the background.  The PID is returned along with the video pathname."""
    video_out_basename = args.file_basename_or_prefix[0]
    video_out_pathname =  os.path.join(OPENCAMERA_SAVE_DIR, f"{video_out_basename}.mp4")
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

def directory_size_increasing(dirname):
    """Return true if the save directory is growing in size (i.e., file is being
    recorded there)."""
    first_du = adb(f"adb shell du {dirname}", return_stdout=True)
    first_du = first_du.split("\t")[0]
    sleep(1)
    second_du = adb(f"adb shell du {dirname}", return_stdout=True)
    second_du = second_du.split("\t")[0]
    return int(second_du) > int(first_du)

def start_monitoring_and_button_push_recording(autostart_recording=True):
    """Emulate a button push to start and stop recording."""

    # Get a snapshot of save directory before recording starts.
    before_ls = adb_ls(OPENCAMERA_SAVE_DIR, extension_whitelist=[VIDEO_FILE_EXTENSION])

    if AUTO_START_RECORDING:
        # Note, this was the original way to get a single video but always starts
        # recording right away and only allows one video at a time to be recorded
        # before closing scrcpy.  It still works as an error check of sorts.
        adb_tap_camera_button()
        sleep(0.5)
        after_ls = adb_ls(OPENCAMERA_SAVE_DIR, all=True, extension_whitelist=[VIDEO_FILE_EXTENSION])
        new_video_files = [f for f in after_ls if f not in before_ls]
        if len(new_video_files) > 1:
            print("\nWARNING: Found multiple new files in OPENCAMERA_SAVE_DIR.", file=sys.stderr)
        if not(new_video_files):
            print("\nERROR: No new video files found.  Is phone connected via USB?\n", file=sys.stderr)
        # Previously used lines below.
        # NOTE: Below line is needed to convert `.pending...mp4` files to the final fname.
        #video_basename = new_video_files[0].split("-")[-1]
        #video_path = os.path.join(OPENCAMERA_SAVE_DIR, video_basename)

    start_screen_monitor(block=True) # This blocks until the screen monitor is closed.

    if directory_size_increasing(OPENCAMERA_SAVE_DIR):
        adb_tap_camera_button() # Presumably still recording; turn off the camera.
        while directory_size_increasing(OPENCAMERA_SAVE_DIR):
            print("Waiting for save directory to stop increasing in size...")
            sleep(1)

    # Get a final snapshot of save directory after recording is finished.
    after_ls = adb_ls(OPENCAMERA_SAVE_DIR, extension_whitelist=[VIDEO_FILE_EXTENSION])

    new_video_files = [f for f in after_ls if f not in before_ls]
    new_video_paths = [os.path.join(OPENCAMERA_SAVE_DIR, v) for v in new_video_files]
    return new_video_paths

def kill_pid(pid):
    """Issue a kill command to a PID on the local machine (not the Android device
    directly)."""
    os.system(f"kill {pid}")

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
            cmd = f"{VIDEO_PLAYER_CMD_JACK} {video_path}"
        else:
            print("\nDid not detect jack running via qjackctl.")
            cmd = f"{VIDEO_PLAYER_CMD} {video_path}"
        print(f"\nRunning: {cmd}")
        os.system(cmd)

    if QUERY_PREVIEW_VIDEO:
        preview = input("\nRun preview? ")
        if preview.strip() in YES_ANSWERS:
            run_preview(video_path)
    else:
        print("\nRunning preview...")
        run_preview(video_path)

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

def extract_audio_from_video(video_path):
    """Extract the audio from a video file, of the type with the given extension."""
    # Note screen recording doesn't have audio, only the "button" method.
    if not ((AUDIO_EXTRACT or QUERY_AUDIO_EXTRACT) and os.path.isfile(video_path)
                                               and RECORDING_METHOD == "button"):
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

    if QUERY_AUDIO_EXTRACT:
        extract_audio = input("\nExtract audio from video? ")
        if extract_audio.strip() in YES_ANSWERS:
            run_audio_extraction(video_path, extension=EXTRACTED_AUDIO_EXTENSION)
    else:
        run_audio_extraction(video_path, extension=EXTRACTED_AUDIO_EXTENSION)

def print_info_about_pulled_video(video_path):
    """Print out some information about the resolution, etc., of a video."""
    print("\nRunning ffprobe on saved video file:") # TODO, refine info and maybe print better.
    os.system(f"ffprobe -v error -show_entries stream=width,height -of default=noprint_wrappers=1 {video_path}")

def monitor_record_and_pull_videos():
    """Record a video on the Android device and pull the resulting file."""
    if RECORDING_METHOD == "screen":
        recorder_pid, video_path = start_screenrecording(args)
        start_screen_monitor(block=True)
        kill_pid(recorder_pid)
        video_path = pull_and_delete_file(video_path) # TODO: does this work with preview??? Haven't tested...
        return [video_path]

    elif RECORDING_METHOD == "button":
        video_paths = start_monitoring_and_button_push_recording()
        new_video_paths = []
        sleep(5) # Make sure video files have time to finish writing and close.
        numbering_offset = args.numbering_start[0]
        print("numbering offset", numbering_offset)
        for count, vid in enumerate(video_paths):
            pulled_vid = pull_and_delete_file(vid) # Note file always written to CWD for now.
            sleep(0.3)
            new_vid_name = f"{args.file_basename_or_prefix[0]}_{count+numbering_offset:02d}_{pulled_vid}"
            print("\n\n------------> new_vid_name:", new_vid_name)
            print(f"\nSaving (renaming) video file as\n   {new_vid_name}")
            os.rename(pulled_vid, new_vid_name)
            new_video_paths.append(new_vid_name)
        return new_video_paths

def parse_command_line():
    """Create and return the argparse object to read the command line."""

    parser = argparse.ArgumentParser(
                    description="Record a video on mobile via ADB and pull result.")

    parser.add_argument("file_basename_or_prefix", type=str, nargs=1, metavar="file_basename_or_prefix",
                        default=None, help="The basename or prefix of the pulled video file."
                        " Whether name or prefix depends on the method used to record.")
    parser.add_argument("--scrcpy-args", "-s", type=str, nargs=1, metavar="STRING-OF-ARGS",
                        default=[""], help="""An optional string of extra arguments to pass
                        directly to the `scrcpy` program.""")
    parser.add_argument("--numbering-start", "-n", type=int, nargs=1, metavar="INTEGER",
                        default=[1], help="""The number at which to start numbering videos.
                        The number is currently appended to the user-defined prefix and
                        defaults to 1.""")
    #parser.add_argument("--inplace", action="store_true", default=False,
    #                    help="""Modify the input code file inplace; code will be
    #                    replaced with the stripped code.  This is the same as
    #                    passing in the code file's name as the output file.""")
    #parser.add_argument("--to-empty", action="store_true", default=default_to_empty,
    #                    help="""Map removed code to empty strings rather than spaces.
    #                    This is easier to read, but does not preserve columns.
    #                    Default is false.""")
    #parser.add_argument("--strip-nl", action="store_true", default=default_strip_nl,
    #                    help="""Also strip non-logical newline tokens inside type
    #                    hints.  These occur, for example, when a type-hint
    #                    function like `List` in a function parameter list has
    #                    line breaks inside its own arguments list.  The default
    #                    is to keep the newline tokens in order to preserve line
    #                    numbers between the stripped and non-stripped files.
    #                    Selecting this option no longer guarantees a direct
    #                    correspondence.""")
    #parser.add_argument("--no-ast", action="store_true", default=default_no_ast,
    #                    help="""Do not parse the resulting code with the Python `ast`
    #                    module to check it.  Default is false.""")
    #parser.add_argument("--no-colon-move", action="store_true", default=default_no_colon_move,
    #                    help="""Do not move colons to fix line breaks that occur in the
    #                    hints for the function return type.  Default is false.""")
    #parser.add_argument("--no-equal-move", action="store_true", default=default_no_equal_move,
    #                    help="""Do not move the assignment with `=` when needed to
    #                    fix annotated assignments that include newlines in the
    #                    type hints.  When they are moved the total number of
    #                    lines is kept the same in order to preserve line number
    #                    correspondence between the stripped and non-stripped
    #                    files.  If this option is selected and such a situation
    #                    occurs an exception is raised.""")
    #parser.add_argument("--only-assigns-and-defs", action="store_true",
    #                    default=default_only_assigns_and_defs,
    #                    help="""Only strip annotated assignments and standalone type
    #                    definitions, keeping function signature annotations.
    #                    Python 3.5 and earlier do not implement these; they
    #                    first appeared in Python 3.6.  The default is false.""")
    #parser.add_argument("--only-test-for-changes", action="store_true",
    #                    default=default_only_test_for_changes, help="""
    #                    Only test if any changes would be made.  If any
    #                    stripping would be done then it prints `True` and
    #                    exits with code 0.  Otherwise it prints `False` and
    #                    exits with code 1.""")

    cmdline_args = parser.parse_args()
    return cmdline_args

def main():
    """Main script functionality."""
    print_startup_message()
    wakeup_device()
    unlock_screen()
    open_video_camera()

    video_paths = monitor_record_and_pull_videos()
    adb_toggle_power() # Turn device off after use.

    for vid in video_paths:
        print(f"\n{'='*12} {vid} {'='*30}")
        print_info_about_pulled_video(vid)
        preview_video(vid)
        extract_audio_from_video(vid)

if __name__ == "__main__":

    args = parse_command_line() # Put `args` in global scope so all funs can use it.
    main()

