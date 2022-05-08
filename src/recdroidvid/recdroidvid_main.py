#!/usr/bin/python3
"""

Usage: recdroidvid.py

Be sure to install scrcpy and set phone to allow for ADB communication over
USB.  See the video recording notes in ardour directory for details.

Currently requires these programs to be installed:
    scrcpy
    ffprobe, to print information about videos
    ffmpeg, for audio extraction when that option is selected
    mpv, for previewing when that option is selected

    sudo apt install scrcpy ffmpeg mpv

"""

# TODO maybe: Colorama colors on output text.

VERSION = "0.1.0"

import sys
import os
from time import sleep
import subprocess
import datetime
import threading

from .settings_and_options import (parse_command_line, args, DETECT_JACK_PROCESS_NAMES,
                USE_SCREENRECORD, RECORD_DETECTION_METHOD, SYNC_DAW_SLEEP_TIME,
                VIDEO_FILE_EXTENSION, QUERY_EXTRACT_AUDIO, QUERY_PREVIEW_VIDEO,
                EXTRACTED_AUDIO_EXTENSION, POSTPROCESS_VIDEOS,
                POSTPROCESSING_CMD, VIDEO_PLAYER_CMD, VIDEO_PLAYER_CMD_JACK)

#
# Simple utility functions.
#

def query_yes_no(query_string, empty_default=None):
    """Query the user for a yes or no response.  The `empty_default` value can
    be set to a string to replace an empty response.  A "quit" response is
    taken to be the same as "no"."""
    yes_answers = {"Y", "y", "yes", "YES", "Yes"}
    no_answers = {"N", "n", "no", "NO", "No"}
    quit_answers = {"q", "Q", "quit", "QUIT", "Quit"}

    while True:
        response = input(query_string)
        response = response.strip()
        if empty_default is not None and response == "":
            return empty_default
        if not (response in yes_answers or response in no_answers or response in quit_answers):
            continue
        if response in yes_answers:
            return True
        return False # Must be a "no" or "quit" answer.

def run_local_cmd_blocking(cmd, *, print_cmd=False, print_cmd_prefix="", macro_dict={},
                           fail_on_nonzero_exit=True, capture_output=True):
    """Run a local system command.  If a string is passed in as `cmd` then
    `shell=True` is assumed.  If `macro_dict` is passed in then any dict key
    strings found as substrings of `cmd` will be replaced by their corresponding
    values.

    If `fail_on_nonzero_exit` is false then the return code is the first
    returned argument.  Otherwise only stdout and stderr are returned, assuming
    `capture_output` is true.

    Note that when `capture_output` is false the process output goes to the
    terminal as it runs, otherwise it doesn't."""
    shell=False
    if isinstance(cmd, str):
        shell = True # Run as shell cmd if a string is passed in.
        for key, value in macro_dict.items():
            cmd = cmd.replace(key, value)
        cmd_string = cmd
    else:
        for key, value in macro_dict.items():
            cmd = [s.replace(key, value) for s in cmd]
        cmd_string = " ".join(cmd)

    if print_cmd:
        cmd_string = "\n" + print_cmd_prefix + cmd_string
        print(cmd_string)

    completed_process = subprocess.run(cmd, capture_output=capture_output, shell=shell,
                                       check=False, encoding="utf-8")

    if fail_on_nonzero_exit and completed_process.returncode != 0:
        print("\nError, nonzero exit running system command, exiting...", file=sys.stderr)
        sys.exit(1)

    if capture_output:
        if fail_on_nonzero_exit:
            return completed_process.stdout, completed_process.stderr
        else:
            return completed_process.returncode, completed_process.stdout, completed_process.stderr
    if not fail_on_nonzero_exit:
        return completed_process.returncode

def indent_lines(string, n=4):
    """Indent all the lines in a string by n spaces."""
    string_list = string.splitlines()
    string_list = [" "*n + i for i in string_list]
    return "\n".join(string_list)

#
# Android ADB commands.
#

def adb(cmd, *, print_cmd=True):
    """Run the ADB command, printing out diagnostics.  Setting `return_output`
    returns the stdout of the command, but the command must be redirectable to
    a temp file.  Returned string is a direct read, with no splitting."""
    returncode, stdout, stderr = run_local_cmd_blocking(cmd, print_cmd=print_cmd, print_cmd_prefix="ADB: ",
                                                        fail_on_nonzero_exit=False)
    if stderr.startswith("error: no devices"):
        print("\nERROR: No devices found, is the phone plugged in via USB?", file=sys.stderr)
        sys.exit(1)
    elif returncode != 0:
        print("\nERROR: ADB command returned nonzero exit status, exiting...", file=sys.stderr)
        sys.exit(1)
    return stdout, stderr

def adb_ls(path, all=False, extension_whitelist=None, print_cmd=True):
    """Run the ADB ls command and return the filenames time-sorted from oldest
    to newest.   If `all` is true the `-a` option to `ls` is used (which gets dotfiles
    too).  The `extension_whitelist` is an optional iterable of required file
    extensions such as `[".mp4"]`."""
    tmp_ls_path = "zzzz_tmp_adb_ls_path"
    # NOTE NOTE: `adb shell ls` is DIFFERENT FROM `adb ls`, you need also hidden files with
    # `shell adb` to get `.pending....mp4` files, and there are still a few more in `shell ls`.
    if all:
        ls_list, ls_stderr = adb(f"adb shell ls -ctra {path}", print_cmd=print_cmd)
    else:
        ls_list, ls_stderr = adb(f"adb shell ls -ctr {path}", print_cmd=print_cmd)
    ls_list = ls_list.splitlines()

    if extension_whitelist:
        for e in extension_whitelist:
            ls_list = [f for f in ls_list if f.endswith(e)]
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
    stdout, stderr = adb(f"adb shell input keyevent KEYCODE_WAKEUP")
    sleep(2)

def adb_device_sleep():
    """Issue an ADB sleep command."""
    stdout, stderr = adb(f"adb shell input keyevent KEYCODE_SLEEP")
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
    adb(f"adb shell am start -W -n {args().camera_package_name[0]}/.MainActivity --ei android.intent.extras.CAMERA_FACING 0")
    sleep(1)

def adb_directory_size_increasing(dirname, wait_secs=1):
    """Return true if the save directory is growing in size (i.e., file is being
    recorded there)."""
    DEBUG = False # Print commands to screen when debugging.
    first_du, stderr = adb(f"adb shell du {dirname}", print_cmd=DEBUG)
    first_du = first_du.split("\t")[0]
    sleep(wait_secs)
    second_du, stderr = adb(f"adb shell du {dirname}", print_cmd=DEBUG)
    second_du = second_du.split("\t")[0]
    return int(second_du) > int(first_du)

def adb_pending_video_file_exists(dirname):
    """Return true if a filename starting with `.pending` is found in the directory.
    This is an implementation detail of OpenCamera, but can detect recording video
    in one call (unlike `adb_directory_size_increasing`."""
    files = adb_ls(dirname, all=True, print_cmd=False)
    return any(f.startswith(".pending") for f in files)

#
# Local machine startup functions.
#

def print_startup_message():
    """Print out the initial greeting message."""
    print(f"{'='*78}")
    print(f"\nrecdroidvid, version {VERSION}")
    print(f"\n{'='*78}")

def detect_if_jack_running():
    """Determine if the Jack audio system is currently running; return true if it is."""
    #ps_output_old = subprocess.check_output(["ps", "-ef"]) # DEBUG, Works, but delete when below known to work... TODO
    ps_output, stderr = run_local_cmd_blocking(["ps", "-ef"])
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

def raise_daw_in_window_stack():
    """Run the command to raise the DAW in the window stack."""
    print("\nRaising DAW to top of Window stack:", args().raise_daw_to_top_cmd[0])
    # Allow the command to fail, but issue a warning.
    returncode, stdout, stderr = run_local_cmd_blocking(args().raise_daw_to_top_cmd[0],
                                                        fail_on_nonzero_exit=False)
    if returncode != 0:
        print("\nWARNING: Nonzero exit status running the raise-DAW command.", file=sys.stderr)

def toggle_daw_transport():
    """Toggle the transport state of the DAW.  Used to sync with recording."""
    print("\nToggling DAW transport:", args().toggle_daw_transport_cmd[0])
    run_local_cmd_blocking(args().toggle_daw_transport_cmd[0])
    if args().raise_daw_on_transport_toggle:
        raise_daw_in_window_stack()

sync_daw_stop_flag = False # Flag to signal the DAW sync thread to stop.

def video_is_recording_on_device():
    """Function to detect when video is recording on the Android device, returns
    true or false."""
    if RECORD_DETECTION_METHOD == "directory size increasing":
        return adb_directory_size_increasing(args().camera_save_dir[0],
                                             wait_secs=1)
    if RECORD_DETECTION_METHOD == ".pending filename prefix":
        return adb_pending_video_file_exists(args().camera_save_dir[0])

    print(f"Error in recdroidvid setting: Unrecognized RECORD_DETECTION_METHOD:"
          f"\n   '{RECORD_DETECTION_METHOD}'", file=sys.stderr)
    sys.exit(1)

def sync_daw_transport_bg_process(stop_flag_fun):
    """Start the DAW transport when video recording is detected on the Android
    device.  Meant to be run as a thread or via multiprocessing to execute at the
    same time as the scrcpy monitor."""
    daw_transport_rolling = False
    while True:
        vid_recording = video_is_recording_on_device()
        if not daw_transport_rolling and vid_recording:
            toggle_daw_transport() # Later could be a "start transport" cmd.
            daw_transport_rolling = True
        if daw_transport_rolling and not vid_recording:
            toggle_daw_transport() # Later could be a "stop transport" cmd.
            daw_transport_rolling = False
        if stop_flag_fun():
            break
        sleep(SYNC_DAW_SLEEP_TIME)

def sync_daw_transport_with_video_recording():
    """Start up the background process to sync the DAW transport when recording
    starts or stops are detected on the mobile device."""
    # To use threading instead, set a stop flag as in one of the answers here:
    # https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread
    proc = threading.Thread(target=sync_daw_transport_bg_process,
                                   args=(lambda: sync_daw_stop_flag,))
    proc.daemon = True # This is so the thread always dies when the main program exits.
    proc.start()
    return proc

def sync_daw_process_kill(proc):
    """Kill the DAW syncing process and reclaim resources."""
    global sync_daw_stop_flag
    sync_daw_stop_flag = True
    proc.join()
    sync_daw_stop_flag = False # Reset for next time.

#
# Recording and monitoring functions.
#

def start_screenrecording():
    """Start screenrecording via the ADB `screenrecord` command.  This process is run
    in the background.  The PID is returned along with the video pathname."""
    # CODE DEPRECATED AND NOW UNTESTED!!!!
    video_out_basename = args().video_file_prefix[0]
    video_out_pathname =  os.path.join(args().camera_save_dir[0], f"{video_out_basename}.mp4")
    tmp_pid_path = f"zzzz_screenrecord_pid_tmp"
    adb_ls(os.path.dirname(video_out_pathname)) # DOESNT DO ANYTHING?? DEBUG??

    adb(f"adb shell screenrecord {video_out_pathname} & echo $! > {tmp_pid_path}")

    sleep(1)
    with open(tmp_pid_path, "r", encoding="utf-8") as f:
        pid = f.read()
    os.remove(tmp_pid_path)
    sleep(10)

    # NOTE, below takes --size, but messes it up, density??
    #adb shell screenrecord --size 720x1280 /storage/emulated/0/DCIM/OpenCamera/$1.mp4 &
    return pid, video_out_pathname

def start_screen_monitor():
    """Run the scrcpy program as a screen monitor, blocking until it is shut down."""
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

    scrcpy_cmd = args().scrcpy_cmd[0]

    window_title_str = f"'video file prefix: {args().video_file_prefix}'"
    run_local_cmd_blocking(scrcpy_cmd, print_cmd=True, print_cmd_prefix="SYSTEM: ",
                           macro_dict={"RDB%SCRCPY-TITLE": window_title_str},
                           capture_output=False)

def start_monitoring_and_button_push_recording():
    """Emulate a button push to start and stop recording."""
    # Get a snapshot of save directory before recording starts.
    before_ls = adb_ls(args().camera_save_dir[0], extension_whitelist=[VIDEO_FILE_EXTENSION])

    if args().autorecord:
        adb_tap_camera_button()

    if args().sync_daw_transport_with_video_recording:
        proc = sync_daw_transport_with_video_recording()

    start_screen_monitor() # This blocks until the screen monitor is closed.

    # If the user just shut down scrcpy while recording video, stop the recording.
    if adb_directory_size_increasing(args().camera_save_dir[0]):
        adb_tap_camera_button() # Presumably still recording; turn off the camera.
        #if args().sync_daw_transport_with_video_recording: # Now BG thread is still running to stop DAW transport.
        #    toggle_daw_transport() # Presumably the DAW transport is still rolling.
        while adb_directory_size_increasing(args().camera_save_dir[0]):
            print("Waiting for save directory to stop increasing in size...")
            sleep(1)

    if args().sync_daw_transport_with_video_recording:
        sync_daw_process_kill(proc)

    # Get a final snapshot of save directory after recording is finished.
    after_ls = adb_ls(args().camera_save_dir[0], extension_whitelist=[VIDEO_FILE_EXTENSION])

    new_video_files = [f for f in after_ls if f not in before_ls]
    new_video_paths = [os.path.join(args().camera_save_dir[0], v) for v in new_video_files]
    return new_video_paths

def generate_video_name(video_number, pulled_vid_name):
    """Generate the name to rename a pulled video to."""
    if args().date_and_time_in_video_name:
        date_time_string = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S_')
    else:
        date_time_string = ""
    new_vid_name = f"{args().video_file_prefix}_{video_number:02d}_{date_time_string}{pulled_vid_name}"
    return new_vid_name

def monitor_record_and_pull_videos(video_start_number):
    """Record a video on the Android device and pull the resulting file."""
    if USE_SCREENRECORD: # NOTE: This method is no longer tested, may be removed.
        recorder_pid, video_path = start_screenrecording()
        start_screen_monitor()
        run_local_cmd_blocking(f"kill {recorder_pid}")
        video_path = pull_and_delete_file(video_path)
        return [video_path]

    # Use the method requiring a button push on phone, emulated or actual.
    video_paths = start_monitoring_and_button_push_recording()
    new_video_paths = []
    sleep(5) # Make sure video files have time to finish writing and close.
    for count, vid in enumerate(video_paths):
        pulled_vid = pull_and_delete_file(vid) # Note file always written to CWD for now.
        sleep(0.3)
        new_vid_name = generate_video_name(count+video_start_number, pulled_vid)
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
    if not (args().preview_video or QUERY_PREVIEW_VIDEO):
        return
    if QUERY_PREVIEW_VIDEO and not query_yes_no("\nRun preview? "):
        return

    print("\nRunning preview...")
    if detect_if_jack_running():
        print("\nDetected jack running via qjackctl.")
        preview_cmd = VIDEO_PLAYER_CMD_JACK + [f"{video_path}"]
    else:
        print("\nDid not detect jack running via qjackctl.")
        preview_cmd = VIDEO_PLAYER_CMD + [f"{video_path}"]

    run_local_cmd_blocking(preview_cmd, print_cmd=True, capture_output=False,
                       macro_dict={"RDV%FILENAME": os.path.basename(video_path)})

def extract_audio_from_video(video_path):
    """Extract the audio from a video file, of the type with the given extension."""
    if not ((args().audio_extract or QUERY_EXTRACT_AUDIO) and os.path.isfile(video_path)
                                                   and not USE_SCREENRECORD):
        return
    if QUERY_EXTRACT_AUDIO and not query_yes_no("\nExtract audio from video? "):
        return

    dirname, basename = os.path.split(video_path)
    root_name, video_extension = os.path.splitext(basename)
    output_audio_path = os.path.join(dirname, root_name + EXTRACTED_AUDIO_EXTENSION)
    print(f"\nExtracting audio to file: '{output_audio_path}'")
    # https://superuser.com/questions/609740/extracting-wav-from-mp4-while-preserving-the-highest-possible-quality
    cmd = f"ffmpeg -i {video_path} -map 0:a {output_audio_path} -loglevel quiet"
    run_local_cmd_blocking(cmd, print_cmd=True, print_cmd_prefix="SYSTEM: ",
                           capture_output=False)
    print("\nAudio extracted.")

def postprocess_video_file(video_path):
    """Run a postprocessing algorithm on the video file at `video_path`."""
    if not POSTPROCESS_VIDEOS or not os.path.isfile(video_path):
        return
    postprocess_cmd = POSTPROCESSING_CMD + [f"{video_path}"]
    run_local_cmd_blocking(postprocess_cmd, print_cmd=True, print_cmd_prefix="SYSTEM: ",
                           capture_output=False)

def print_info_about_pulled_video(video_path):
    """Print out some information about the resolution, etc., of a video."""
    # To get JSON: ffprobe -v quiet -print_format json -show_format -show_streams "lolwut.mp4" > "lolwut.mp4.json"
    # In Python search for examples or use library: https://docs.python.org/3/library/json.html
    cmd = (f"ffprobe -pretty -show_format -v error -show_entries"
           f" stream=codec_name,width,height,duration,size,bit_rate"
           f" -of default=noprint_wrappers=1 {video_path} | grep -v 'TAG:'")
    print("\nRunning ffprobe on saved video file:")
    stdout, stderr = run_local_cmd_blocking(cmd)
    print(indent_lines(stdout, 4))
    if stderr:
        print(indent_lines(stderr, 4))

#
# High-level functions.
#


def startup_device_and_run(video_start_number):
    """Main script functionality."""
    adb_device_sleep() # Get a consistent starting state for repeatability.
    adb_device_wakeup()
    adb_unlock_screen()
    adb_open_video_camera()
    if args().raise_daw_on_camera_app_open:
        raise_daw_in_window_stack()

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
    """Outer loop over invocations of the scrcpy screen monitor."""
    parse_command_line()

    video_start_number = args().numbering_start[0]
    print_startup_message()

    count = 0
    while True:
        count += 1
        video_end_number = startup_device_and_run(video_start_number)
        video_start_number = video_end_number + 1
        if not args().loop:
            break
        cont = query_yes_no(f"\nFinished recdroidvid loop {count}, continue?"
                            f" [ynq enter=y]: ", empty_default="y")
        if not cont:
            break

    print("\nExiting recdroidvid.")

if __name__ == "__main__":

    main()

