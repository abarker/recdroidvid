"""

Simple utility functions used in multiple modules.

"""

import sys
import subprocess
from colorama import init, Fore, Back, Style

USE_COLOR = True

args = None # Set globally from main() after command-line args are parsed.

# Available Colorama formatting constants are:
#
# Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
# Style: DIM, NORMAL, BRIGHT, RESET_ALL
#
# Style.RESET_ALL
# print(Fore.BLUE + 'some blue text')
# print(Fore.RED + 'some red text')
# print(Back.GREEN + 'and with a green background')
# print(Style.DIM + 'and in dim text')
# print(Style.RESET_ALL)
# print('back to normal now')

def init_color(parsed_args):
    """Initialize Colorama."""
    if not parsed_args.no_color:
        init(autoreset=False) # To avoid printing Style.RESET_ALL to clear.
    else:
        global USE_COLOR
        USE_COLOR = False

def print_color(color, *args, **kwargs):
    """Generic color printing."""
    if not USE_COLOR:
        print(*args, **kwargs)
    else:
        # For some reason this line below is needed or else BRIGHT text is not
        # turned off after printing, even though `autoreset=True` is set in init.
        #print(color, sep="", end="")
        #print(Style.RESET_ALL, sep="", end="") # This still fails to turn off sometimes...

        args = list(args)
        args[0] = Style.RESET_ALL + color + args[0]
        args[-1] = args[-1] + Style.RESET_ALL
        print(*args, **kwargs)

def print_info(*args, **kwargs):
    """Print out an ADB command with Colorama coloring."""
    print_color(Fore.GREEN, *args, **kwargs)

def input_query(arg):
    """Print out an ADB command with Colorama coloring."""
    if USE_COLOR:
        return input(Style.BRIGHT+Fore.CYAN + arg)
        #return input(Fore.GREEN + arg)
    else:
        return input(arg)

def print_cmd(*args, **kwargs):
    """Print out an ADB command with Colorama coloring."""
    print_color(Fore.BLUE, *args, **kwargs)

def print_error(*args, **kwargs):
    """Print out an ADB command with Colorama coloring."""
    print_color(Fore.RED, *args, **kwargs)

def print_warning(*args, **kwargs):
    """Print out an ADB command with Colorama coloring."""
    print_color(Fore.YELLOW, *args, **kwargs)

def query_yes_no(query_string, empty_default=None):
    """Query the user for a yes or no response.  The `empty_default` value can
    be set to a string to replace an empty response.  A "quit" response is
    taken to be the same as "no"."""
    yes_answers = {"Y", "y", "yes", "YES", "Yes"}
    no_answers = {"N", "n", "no", "NO", "No"}
    quit_answers = {"q", "Q", "quit", "QUIT", "Quit"}

    while True:
        response = input_query(query_string)
        response = response.strip()
        if empty_default is not None and response == "":
            return empty_default
        if not (response in yes_answers or response in no_answers or response in quit_answers):
            continue
        if response in yes_answers:
            return True
        return False # Must be a "no" or "quit" answer.

def run_local_cmd_blocking(cmd, *, print_cmd_str=False, print_cmd_prefix="", macro_dict={},
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
    shell = False
    if isinstance(cmd, str):
        shell = True # Run as shell cmd if a string is passed in.
        for key, value in macro_dict.items():
            cmd = cmd.replace(key, value)
        cmd_string = cmd
    else:
        for key, value in macro_dict.items():
            cmd = [s.replace(key, value) for s in cmd]
        cmd_string = " ".join(cmd)

    if print_cmd_str:
        cmd_string = "\n" + print_cmd_prefix + cmd_string
        print_cmd(cmd_string)

    completed_process = subprocess.run(cmd, capture_output=capture_output, shell=shell,
                                       check=False, encoding="utf-8")

    if fail_on_nonzero_exit and completed_process.returncode != 0:
        print_error("\nError, nonzero exit running system command, exiting...", file=sys.stderr)
        sys.exit(1)

    if capture_output:
        if fail_on_nonzero_exit:
            return completed_process.stdout, completed_process.stderr
        return completed_process.returncode, completed_process.stdout, completed_process.stderr
    if not fail_on_nonzero_exit:
        return completed_process.returncode

def indent_lines(string, n=4):
    """Indent all the lines in a string by n spaces."""
    string_list = string.splitlines()
    string_list = [" "*n + i for i in string_list]
    return "\n".join(string_list)

