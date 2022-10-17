"""

Commands calling the Android Debug Bridge (ADB) to the moblie device.

"""

import sys
from time import sleep
from .settings_and_options import args
from .utility_functions import run_local_cmd_blocking

def adb(cmd, *, print_cmd=True):
    """Run the ADB command, printing out diagnostics.  Setting `return_output`
    returns the stdout of the command, but the command must be redirectable to
    a temp file.  Returned string is a direct read, with no splitting."""
    returncode, stdout, stderr = run_local_cmd_blocking(cmd, print_cmd=print_cmd,
                                                        print_cmd_prefix="ADB: ",
                                                        fail_on_nonzero_exit=False)
    if stderr.startswith("error: no devices"):
        print("\nERROR: No devices found, is the phone plugged in via USB?", file=sys.stderr)
        sys.exit(1)
    elif returncode != 0:
        print(f"\nERROR: ADB command '{cmd}' returned nonzero exit status '{returncode}'."
                f"\nThe command's output follows:\n{stdout}\n{stderr}",
                file=sys.stderr)
        sys.exit(1)
    return stdout, stderr

def ls(path, also_hidden=False, extension_whitelist=None, print_cmd=True):
    """Run the ADB ls command and return the filenames time-sorted from oldest
    to newest.   If `all` is true the `-a` option to `ls` is used (which gets dotfiles
    too).  The `extension_whitelist` is an optional iterable of required file
    extensions such as `[".mp4"]`."""
    # NOTE NOTE: `adb shell ls` is DIFFERENT FROM `adb ls`, you need also hidden files with
    # `shell adb` to get `.pending....mp4` files, and there are still a few more in `shell ls`.
    if also_hidden:
        ls_list, ls_stderr = adb(f"adb shell ls -ctra {path}", print_cmd=print_cmd)
    else:
        ls_list, ls_stderr = adb(f"adb shell ls -ctr {path}", print_cmd=print_cmd)
    ls_list = ls_list.splitlines()

    if extension_whitelist:
        for e in extension_whitelist:
            ls_list = [f for f in ls_list if f.endswith(e)]
    return ls_list

def tap_screen(x, y):
    """Generate a screen tap at the given position."""
    #https://stackoverflow.com/questions/3437686/how-to-use-adb-to-send-touch-events-to-device-using-sendevent-command
    adb(f"adb shell input tap {x} {y}")

def force_stop_opencamera():
    """Issue a force-stop command to OpenCamera app.  Note this made the Google
    camera open by default afterward with camera button."""
    adb("adb shell am force-stop net.sourceforge.opencamera")

def tap_camera_button():
    """Tap the button in the camera to start it or stop it from recording."""
    adb(f"adb shell input keyevent 27")

def toggle_power():
    """Toggle the power.  See also the `device_wakeup` function."""
    adb("adb shell input keyevent KEYCODE_POWER")

def device_wakeup():
    """Issue an ADB wakeup command."""
    stdout, stderr = adb(f"adb shell input keyevent KEYCODE_WAKEUP")
    sleep(2)

def device_sleep():
    """Issue an ADB sleep command."""
    stdout, stderr = adb(f"adb shell input keyevent KEYCODE_SLEEP")
    sleep(2)

def unlock_screen():
    """Swipes screen up, assuming no passcode."""
    # Note 82 is the menu key.
    #adb(f"adb shell input keyevent 82 && adb shell input keyevent 66")
    adb(f"adb shell input keyevent 82")
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
    adb(f"adb shell am start -W -n {args().camera_package_name[0]}/.MainActivity --ei android.intent.extras.CAMERA_FACING 0")
    sleep(1)

def directory_size_increasing(dirname, wait_secs=1):
    """Return true if the save directory is growing in size (i.e., file is being
    recorded there)."""
    DEBUG = False # Print commands to screen when debugging.
    first_du, stderr = adb(f"adb shell du {dirname}", print_cmd=DEBUG)
    first_du = first_du.split("\t")[0]
    sleep(wait_secs)
    second_du, stderr = adb(f"adb shell du {dirname}", print_cmd=DEBUG)
    second_du = second_du.split("\t")[0]
    return int(second_du) > int(first_du)

def pending_video_file_exists(dirname):
    """Return true if a filename starting with `.pending` is found in the directory.
    This is an implementation detail of OpenCamera, but can detect recording video
    in one call (unlike `directory_size_increasing`."""
    files = ls(dirname, also_hidden=True, print_cmd=False)
    return any(f.startswith(".pending") for f in files)

