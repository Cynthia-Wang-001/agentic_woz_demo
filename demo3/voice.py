"""
voice.py - the arm server's half of the recording arrangement.

The student presses Enter to stop recording. That sounds trivial, and it is the
reason this file exists in the shape it does.

The arm server cannot read the keyboard. Its standard input is the channel it
uses to talk to Claude Code, and the terminal itself belongs to the Claude Code
interface. So the recording happens somewhere that does have a keyboard: a
second terminal window, running record_window.py, which stays open for the whole
session and shows the student what is going on.

This file opens that window when it is needed, asks it to record, and waits for
the answer. The two halves pass messages through small files in logs/voice.

    server                            window
      |  writes request.json  ------>   |  shows RECORDING, records
      |                                 |  student presses Enter
      |                                 |  runs Whisper
      |  <------ writes result.json     |  shows what it heard
"""

import json
import os
import shutil
import subprocess
import sys
import time

VOICE_DIRECTORY = os.path.join("logs", "voice")
HEARTBEAT_PATH = os.path.join(VOICE_DIRECTORY, "heartbeat")
REQUEST_PATH = os.path.join(VOICE_DIRECTORY, "request.json")
RESULT_PATH = os.path.join(VOICE_DIRECTORY, "result.json")

# The window updates its heartbeat every second. Anything older than this means
# the window has been closed.
HEARTBEAT_STALE_SECONDS = 6.0

TURN_COUNTER = {"n": 0}


def dependencies_missing():
    """Returns a message explaining what is missing, or None if all is well."""
    try:
        import numpy  # noqa: F401
    except ImportError:
        return (
            "Recording needs numpy, which is not installed:\n"
            "    pip install numpy"
        )

    try:
        import sounddevice  # noqa: F401
    except ImportError:
        return (
            "Recording needs the sounddevice package, which is not installed:\n"
            "    pip install sounddevice"
        )
    except Exception as exc:
        # sounddevice imports fine but cannot load the system audio library.
        # This raises OSError rather than ImportError, so it needs its own case.
        return (
            "The sounddevice package is installed but could not reach the "
            "system audio library: %s\n\n"
            "    macOS    brew install portaudio\n"
            "    Ubuntu   sudo apt install libportaudio2\n\n"
            "If audio cannot be made to work at all, the student can type "
            "instructions to you instead of speaking." % exc
        )

    if shutil.which("ffmpeg") is None:
        return (
            "ffmpeg is not installed, and Whisper needs it to read audio.\n"
            "    macOS    brew install ffmpeg\n"
            "    Ubuntu   sudo apt install ffmpeg\n"
            "    Windows  winget install ffmpeg"
        )

    if shutil.which("whisper") is None:
        return (
            "The whisper command was not found. Follow the Whisper handout, "
            "and make sure the virtual environment was active in the terminal "
            "that started the agent."
        )

    return None


# ----------------------------------------------------------------------
# Opening the recording window
# ----------------------------------------------------------------------

def window_is_open():
    try:
        age = time.time() - os.path.getmtime(HEARTBEAT_PATH)
    except OSError:
        return False
    return age < HEARTBEAT_STALE_SECONDS


def _launcher_script(project_directory):
    """
    Writes a small shell script for the new window to run.

    It carries this process's PATH across, so that whisper and ffmpeg are found
    in the new window even though it starts a fresh shell that has not activated
    the virtual environment.
    """
    os.makedirs(VOICE_DIRECTORY, exist_ok=True)
    path = os.path.join(VOICE_DIRECTORY, "start_recorder.command")

    lines = [
        "#!/bin/bash",
        "# Written automatically. Opens the recording window for the lab.",
        'export PATH=%s' % _quote(os.environ.get("PATH", "")),
        'cd %s' % _quote(project_directory),
        'exec %s %s %s' % (
            _quote(sys.executable),
            _quote(os.path.join(project_directory, "record_window.py")),
            _quote(project_directory),
        ),
        "",
    ]

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    os.chmod(path, 0o755)
    return path


def _quote(text):
    return "'" + str(text).replace("'", "'\\''") + "'"


def open_window():
    """
    Opens the recording window. Returns (ok, message).
    """
    project_directory = os.path.abspath(os.getcwd())

    if sys.platform == "darwin":
        script = _launcher_script(project_directory)
        command = ["open", "-a", "Terminal", script]
    elif sys.platform.startswith("win"):
        command = [
            "cmd", "/c", "start", "Recording",
            sys.executable,
            os.path.join(project_directory, "record_window.py"),
            project_directory,
        ]
    else:
        script = _launcher_script(project_directory)
        for terminal in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
            if shutil.which(terminal):
                command = [terminal, "-e", script]
                break
        else:
            return False, (
                "Could not find a terminal program to open the recording "
                "window. Open one yourself and run:\n"
                "    python record_window.py"
            )

    try:
        subprocess.run(command, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        return False, "Could not open the recording window: %s" % exc

    # Give it a moment to start and write its first heartbeat.
    for _ in range(40):
        if window_is_open():
            return True, "Opened the recording window."
        time.sleep(0.25)

    return False, (
        "The recording window did not start. Open a second terminal yourself, "
        "activate the virtual environment, and run:\n"
        "    python record_window.py"
    )


def ensure_window(auto_open=True):
    if window_is_open():
        return True, None
    if not auto_open:
        return False, (
            "The recording window is not open. Open a second terminal, "
            "activate the virtual environment, and run:\n"
            "    python record_window.py"
        )
    ok, message = open_window()
    return ok, (None if ok else message)


# ----------------------------------------------------------------------
# Asking for one recording
# ----------------------------------------------------------------------

def _clear_stale_files():
    for path in (REQUEST_PATH, RESULT_PATH):
        try:
            os.remove(path)
        except OSError:
            pass


def request_recording(model="turbo", timeout=600):
    """
    Asks the window to record one instruction and waits for the transcript.

    Returns a dictionary:
        {"ok": True,  "transcript": str, "seconds": float, "audio": str}
        {"ok": False, "message": str}
    """
    os.makedirs(VOICE_DIRECTORY, exist_ok=True)
    _clear_stale_files()

    TURN_COUNTER["n"] += 1
    turn = TURN_COUNTER["n"]

    temporary = REQUEST_PATH + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump({"id": turn, "model": model}, handle)
    os.replace(temporary, REQUEST_PATH)

    deadline = time.time() + timeout

    while time.time() < deadline:
        if os.path.exists(RESULT_PATH):
            try:
                with open(RESULT_PATH, "r", encoding="utf-8") as handle:
                    result = json.load(handle)
            except (OSError, json.JSONDecodeError):
                time.sleep(0.1)
                continue

            if result.get("id") == turn:
                try:
                    os.remove(RESULT_PATH)
                except OSError:
                    pass
                return result

        if not window_is_open():
            _clear_stale_files()
            return {
                "ok": False,
                "message": (
                    "The recording window was closed before anything was "
                    "recorded. It will be reopened on the next attempt."
                ),
            }

        time.sleep(0.15)

    _clear_stale_files()
    return {
        "ok": False,
        "message": (
            "Waited %d seconds and the student never finished the recording. "
            "Nothing was sent." % timeout
        ),
    }
