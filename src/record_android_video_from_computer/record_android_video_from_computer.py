#!/usr/bin/python3
"""

Usage: record-remote-and-pull-video.py

Be sure to set phone to allow for ADB communication over USB.  See the video
recording notes in ardour directory for details.

"""

# TODO: Keep monitor open, but detect when phone stops recording or starts.  Simultaneously,
# start or stop the recording on Ardour.  Can probably use space bar with xdotool, but need
# to find the window it is using.  Maybe start Ardour from a script that does some preliminary
# setup and data-gathering first?  Can that detect the GUI window, though?
#
# To detect recording, may need to look for new files or files that stop
# growing for some threshold period.
#
# https://linuxhint.com/xdotool_stimulate_mouse_clicks_and_keystrokes/

# NOTE: Look at the info from an OpenCamera video saved on the phone to find this path.
OPENCAMERA_SAVE_DIR = "/storage/emulated/0/DCIM/OpenCamera/" # Where OpenCamera writes video.

#RECORDING_METHOD = "screen" # Record with screenrecord; limited to screen resolution(?) and 3min, no sound.
# https://stackoverflow.com/questions/21938948/how-to-increase-time-limit-of-adb-screen-record-of-android-kitkat
RECORDING_METHOD = "button" # Record by emulating a button push and looking for new video file.

#VIDEO_PLAYER_CMD = "pl"
VIDEO_PLAYER_CMD = "mplayer -loop 0"
#VIDEO_PLAYER_CMD_JACK = "pl --jack"
VIDEO_PLAYER_CMD_JACK = "mplayer -ao jack -loop 0"
DETECT_JACK_PROCESS_NAMES = ["qjackctl"] # Search `ps -ef` for these to detect Jack running.

PREVIEW_VIDEO = True
QUERY_PREVIEW_VIDEO = False

AUDIO_EXTRACT = True # Whether to ever extract a AUDIO file from the video.
QUERY_AUDIO_EXTRACT = False # Ask before extracting AUDIO file.
EXTRACTED_AUDIO_EXTENSION = ".wav"

import sys
import os
from time import sleep
import subprocess
import argparse

def adb(cmd, print_cmd=True, return_output=False):
    """Run the ADB command, printing out diagnostics.  Setting `return_output`
    returns the stdout of the command, but the command must be redirectable to
    a temp file.  Returned string is a direct read, with no splitting or processing."""
    if print_cmd:
        print(f"\nCMD: {cmd}")

    if not return_output:
        os.system(cmd)
        return

    tmp_adb_cmd_output_file = "zzzz_tmp_adb_cmd_output_file"
    os.system(cmd + f" > {tmp_adb_cmd_output_file}")
    with open(tmp_adb_cmd_output_file, "r") as f:
        cmd_output = f.read()
        os.remove(tmp_adb_cmd_output_file)

        return cmd_output

def adb_ls(path, extension_whitelist=None):
    """Run the ADB ls command and return the filenames."""
    # TODO: could use the new adb option to return output...
    tmp_ls_path = "zzzz_tmp_adb_ls_path"
    adb(f"adb ls {path} > {tmp_ls_path}")

    with open(tmp_ls_path, "r") as f:
        ls_output = f.read()
    os.remove(tmp_ls_path)

    ls_list = ls_output.splitlines()
    if extension_whitelist:
        for e in extension_whitelist:
            ls_output = [f for f in ls_output if f.endswith(e)]
    return ls_list

def adb_tap_screen(x, y):
    """Generate a screen tap at the given position."""
    #https://stackoverflow.com/questions/3437686/how-to-use-adb-to-send-touch-events-to-device-using-sendevent-command
    adb(f"adb shell input tap {x} {y}")

def adb_tap_camera_button():
    """Tap the button in the camera to start it or stop it from recording."""
    adb(f"adb shell input keyevent 27")

def tap_camera_and_return_new_filenames_in_dir(dirpath, extension=".mp4"):
    """Issues a camera tap and looks for a new filename to appear in the ls listing."""
    before_ls = adb_ls(dirpath, extension_whitelist=extension)
    adb_tap_camera_button()
    sleep(0.5)
    after_ls = adb_ls(dirpath, extension_whitelist=extension)
    new_files = [f for f in after_ls if f not in before_ls]
    return new_files

def ls_diff(ls1, ls2):
    """Return the list of new files in ls2 that were not present in ls1."""

def wakeup_device():
    """Unlock the screen without password."""
    adb(f"adb shell input keyevent KEYCODE_WAKEUP")
    sleep(2)

def unlock_screen():
    """Swipes screen up, assuming no passcode."""
    adb(f"adb shell input keyevent 82 && adb shell input keyevent 66")
    sleep(1)

def open_video_camera():
    """Open the video camera, rear facing."""
    adb(f"adb shell am start -a android.media.action.VIDEO_CAMERA --ei android.intent.extras.CAMERA_FACING 0")
    sleep(1)

def print_startup_message():
    print("="*70)
    print("\n(Make sure that OpenCamera is set to the native SCREEN resolution, 1600x720.)\n")
    print("="*70)

def start_screenrecording(args):
    """Start screenrecording to the path passed in."""
    video_out_basename = args.file_basename_or_prefix[0]
    video_out_pathname =  os.path.join(OPENCAMERA_SAVE_DIR, f"{video_out_basename}.mp4")
    tmp_pid_path = f"zzzz_screenrecord_pid_tmp"
    adb_ls(os.path.dirname(video_out_pathname))

    adb(f"adb shell screenrecord {video_out_pathname} & echo $! > {tmp_pid_path}")
    #print("DEBUG: tmp_pid_path =", tmp_pid_path)

    sleep(1)
    with open(tmp_pid_path, "r") as f:
        pid = f.read()
    #print("DEBUG: pid =", pid)
    os.remove(tmp_pid_path)
    sleep(10)

    #adb shell screenrecord --size 720x1280 /storage/emulated/0/DCIM/OpenCamera/$1.mp4 & # TODO takes --size, but messes it up, density??
    # TODO: Consider using AutoInput to push the start button after below command... (someone online suggested)
    #adb shell am start -a android.media.action.VIDEO_CAPTURE & # FAILS for now...
    return pid, video_out_pathname

def start_button_push_recording():
    """Emulate a button push to start and stop recording."""
    new_video_files = tap_camera_and_return_new_filenames_in_dir(OPENCAMERA_SAVE_DIR)
    #print("\nDEBUG: new video files:", new_video_files)
    if len(new_video_files) > 1:
        print("\nWARNING: Found multiple new files in OPENCAMERA_SAVE_DIR.", file=sys.stderr)
    if not(new_video_files):
        print("\nERROR: No new video files found.  Is phone connected via USB?\n", file=sys.stderr)

    video_basename = new_video_files[0].split("-")[-1]
    video_path = os.path.join(OPENCAMERA_SAVE_DIR, video_basename)
    #print("DEBUG: new video path:", video_path)
    start_screen_monitor()
    adb_tap_camera_button() # Turn off the camera.
    adb_tap_screen(403, 740) # Maybe center tap helps?  Sometimes zoom slider stays.
    return video_path, video_basename

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

    os.system("scrcpy --rotation=0 --lock-video-orientation=initial --stay-awake --disable-screensaver --display-buffer=50 # --crop 720:1600:0:0")

def kill_pid(pid):
    os.system(f"kill {pid}")

def pull_and_delete_file(pathname):
    """Pull the file at the pathname and delete the remote file.  Returns the
    path of the extracted video."""

    # Pull.
    sleep(10) # Make sure files have time to finish writing and close.
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
            cmd = f"{VIDEO_PLAYER_CMD} {video_path}"
        else:
            print("\nDid not detect jack running via qjackctl.")
            cmd = f"{VIDEO_PLAYER_CMD_JACK} {video_path}"
        print(f"\nRunning: {cmd}")
        os.system(cmd)

    if QUERY_PREVIEW_VIDEO:
        preview = input("\nRun preview? ")
        if preview.strip() in {"Y", "y", "yes", "YES", "Yes"}:
            run_preview(video_path)
    else:
        print("\nRunning preview...")
        run_preview(video_path)

def detect_if_jack_running():
    """Determine if the Jack audio system is currently running."""
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
        print("\nExtracting audio to file: '{output_audio_path}'")
        # https://superuser.com/questions/609740/extracting-wav-from-mp4-while-preserving-the-highest-possible-quality
        cmd = f"ffmpeg -i {video_path} -map 0:a {output_audio_path}"
        print("  ", cmd)
        os.system(cmd)
        return output_audio_path

    if QUERY_AUDIO_EXTRACT:
        extract_audio = input("\nExtract audio from video? ")
        if extract_audio.strip() in {"Y", "y", "yes", "YES", "Yes"}:
            print(f"\nExtracting audio from the video file:\n   {video_path}")
            run_audio_extraction(video_path, extension=EXTRACTED_AUDIO_EXTENSION)
            print("\nAudio extracted.")
    else:
        print(f"\nExtracting audio file with extension '{EXTRACTED_AUDIO_EXTENSION}' from video...")
        run_audio_extraction(video_path, extension=EXTRACTED_AUDIO_EXTENSION)
        print("\nAudio extracted.")

def print_info_about_pulled_video(video_path):
    """Print out some information about the resolution, etc., of a video."""
    print("\nRunning ffprobe on saved video file:") # TODO, refine info and maybe print better.
    os.system(f"ffprobe -v error -show_entries stream=width,height -of default=noprint_wrappers=1 {video_path}")

def record_and_pull_video():
    """Record a video on the Android device and pull the resulting file."""
    if RECORDING_METHOD == "screen":
        recorder_pid, video_path = start_screenrecording(args)
        start_screen_monitor(block=True)
        kill_pid(recorder_pid)
        video_path = pull_and_delete_file(video_path) # TODO: does this work with preview??? Haven't tested...

    elif RECORDING_METHOD == "button":
        video_path, video_basename = start_button_push_recording()
        pulled_video_path = pull_and_delete_file(video_path) # Note file always written to CWD for now.
        sleep(0.3)
        video_path = args.file_basename_or_prefix[0] + "_" + pulled_video_path
        print(f"\nSaving (renaming) video file as\n   {video_path}")
        os.rename(pulled_video_path, video_path)

    return video_path

def parse_command_line():
    """Create and return the argparse object to read the command line."""

    parser = argparse.ArgumentParser(
                    description="Record a video on mobile via ADB and pull result.")

    parser.add_argument("file_basename_or_prefix", type=str, nargs=1, metavar="file_basename_or_prefix",
                        default=None, help="The basename or prefix of the pulled video file."
                        " Whether name or prefix depends on the method used to record.")
    #parser.add_argument("--outfile", "-o", type=str, nargs=1, metavar="OUTPUTFILE",
    #                    default=None,
    #                    help="""Write the output to a file with the pathname passed in.
    #                    Files will be silently overwritten if they already
    #                    exist.  If this argument is omitted the output is
    #                    written to stdout.""")
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

    video_path = record_and_pull_video()
    print_info_about_pulled_video(video_path)
    preview_video(video_path)
    extract_audio_from_video(video_path)

if __name__ == "__main__":

    args = parse_command_line() # Put `args` in global scope so all funs can use it.
    main()

