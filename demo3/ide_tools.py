"""
ide_tools.py - opens the Arduino IDE so students can watch the code arrive.

This does one small thing. It opens a sketch file in the Arduino IDE.

Because the IDE has that file open, it reloads it whenever the file changes on
disk. So when the agent rewrites the sketch, the new code appears in the editor
window in front of the students, in the same program they used in Lab 1.

That is all. No keystrokes are sent, no screenshots are taken, and no special
macOS permissions are needed. Compiling and uploading are done by
arm_mcp_server.py through arduino-cli, which gives clean text output.
"""

import os
import subprocess
import sys

IDE_APP_NAME = "Arduino IDE"


def available():
    """True if we know how to ask this computer to open a file in the IDE."""
    return sys.platform in ("darwin", "win32") or sys.platform.startswith("linux")


def open_in_ide(sketch_path):
    """
    Asks the operating system to open a sketch in the Arduino IDE.
    Returns (ok, message).
    """
    path = os.path.abspath(sketch_path)

    if sys.platform == "darwin":
        command = ["open", "-a", IDE_APP_NAME, path]
    elif sys.platform.startswith("win"):
        command = ["cmd", "/c", "start", "", path]
    else:
        command = ["xdg-open", path]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return False, (
            "Could not find a way to open files on this computer. "
            "Open the sketch in the Arduino IDE by hand:\n  %s" % path
        )
    except Exception as exc:
        return False, "Could not open the Arduino IDE: %s" % exc

    if result.returncode != 0:
        return False, (
            ((result.stderr or "").strip() or "Could not open the Arduino IDE.")
            + "\n\nOpen this file by hand instead:\n  %s" % path
        )

    return True, "Opened the sketch in the Arduino IDE."
