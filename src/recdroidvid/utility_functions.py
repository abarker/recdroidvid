"""

Simple utility functions used in multiple modules.

"""

import sys
import subprocess

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
        return completed_process.returncode, completed_process.stdout, completed_process.stderr
    if not fail_on_nonzero_exit:
        return completed_process.returncode

def indent_lines(string, n=4):
    """Indent all the lines in a string by n spaces."""
    string_list = string.splitlines()
    string_list = [" "*n + i for i in string_list]
    return "\n".join(string_list)

