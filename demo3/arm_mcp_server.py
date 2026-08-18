"""
arm_mcp_server.py - lets Claude Code or Codex drive the Braccio arm.

This is an MCP server. Claude Code and Codex start it automatically, keep it
running for the whole session, and call its tools when they decide to move
the arm. Students never run this file themselves.

WHY A SERVER AND NOT A SCRIPT
-----------------------------
Opening a serial port resets the Arduino, and the arm swings to its safety
position every time that happens. A server stays alive for the whole session
and holds the port open, so the reset happens once instead of once per command.

NO LIBRARIES REQUIRED
---------------------
MCP is JSON-RPC 2.0 sent as one JSON object per line over stdin and stdout.
That is implemented directly below, so this file depends on nothing except
pyserial, and only when a real arm is connected. Students can read the whole
protocol in one sitting.

CONFIGURATION (set in .mcp.json or the Codex config file)
---------------------------------------------------------
    WOZ_PORT     serial port name, or "sim" for the simulator. Default "sim".
    WOZ_SAFETY   "on" or "off". Default "on".
    WOZ_LOG      path to a log file. Default "logs/arm_calls.jsonl".

WHAT THE SAFETY SETTING CHANGES
-------------------------------
    on   an out-of-range command is REFUSED and the agent is told why.
         The agent then has to notice and correct itself.
    off  the command is sent anyway. The Braccio library still clamps the
         angle, so the hardware is safe, but nothing warns anybody that the
         agent asked for something impossible.
"""

import datetime
import json
import os
import sys
import time

SERVER_NAME = "braccio-arm"
SERVER_VERSION = "1.0.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"

JOINT_LIMITS = {
    "step_delay": (10, 30),
    "base": (0, 180),
    "shoulder": (15, 165),
    "elbow": (0, 180),
    "wrist_ver": (0, 180),
    "wrist_rot": (0, 180),
    "gripper": (10, 73),
}

JOINT_ORDER = [
    "step_delay", "base", "shoulder", "elbow",
    "wrist_ver", "wrist_rot", "gripper",
]

HOME_POSE = [20, 90, 90, 90, 90, 90, 40]
LARGE_JUMP_DEGREES = 90


# ----------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------

PORT = os.environ.get("WOZ_PORT", "sim")
SAFETY_ON = os.environ.get("WOZ_SAFETY", "on").strip().lower() != "off"
LOG_PATH = os.environ.get("WOZ_LOG", os.path.join("logs", "arm_calls.jsonl"))

# Settings for the code generation mode.
#
# arduino-cli is the command line version of the Arduino IDE. You almost
# certainly do NOT need to install it separately, because the Arduino IDE
# version 2 ships with a copy inside it. find_arduino_cli() looks for that copy
# before giving up.
#
# Using the IDE's own copy has a second advantage: it reads the same settings
# and library folders as the IDE, so any library already installed through the
# IDE Library Manager, such as Braccio, is found automatically.
ARDUINO_CLI_OVERRIDE = os.environ.get("WOZ_ARDUINO_CLI", "").strip()
# Board type for arduino-cli. The lab uses an Arduino Mega 2560.
#   Mega 2560   arduino:avr:mega
#   Uno         arduino:avr:uno
# Run the detect_board tool if you are not sure.
FQBN = os.environ.get("WOZ_FQBN", "arduino:avr:mega")
SKETCH_ROOT = os.environ.get("WOZ_SKETCH_DIR", "sketches")
LISTENER_SKETCH = os.path.join("firmware", "braccio_listener")

# Which firmware is currently on the board.
#   "listener"  the command interpreter is running, so move_arm works
#   "custom"    a sketch written by the agent is running, so move_arm does not
FIRMWARE_MODE = "listener"


def log_line(record):
    """Records every tool call for the instructor. Never interrupts the lab."""
    try:
        directory = os.path.dirname(LOG_PATH)
        if directory:
            os.makedirs(directory, exist_ok=True)
        record["time"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except OSError:
        pass


def note(message):
    """
    Prints to stderr. Claude Code and Codex show stderr from MCP servers in
    their logs, and it never corrupts the JSON-RPC stream on stdout.
    """
    sys.stderr.write("[braccio] %s\n" % message)
    sys.stderr.flush()


# ----------------------------------------------------------------------
# The arm
# ----------------------------------------------------------------------

def clamp_like_braccio(values):
    """
    Mimics what the Braccio library does inside the Arduino: any angle outside
    the accepted range is silently pulled back to the nearest legal value.
    The simulator has to do this too, otherwise it would behave differently
    from the real hardware in exactly the situation the lab cares about.
    """
    clamped = []
    for name, value in zip(JOINT_ORDER, values):
        low, high = JOINT_LIMITS[name]
        clamped.append(min(max(value, low), high))
    return clamped


class SimulatedArm:
    backend = "simulator"

    def __init__(self):
        self.pose = list(HOME_POSE)

    def send(self, values):
        actual = clamp_like_braccio(values)
        self.pose = list(actual)
        time.sleep(0.3)
        text = "OK " + " ".join(str(v) for v in actual) + "  (simulated)"
        if actual != list(values):
            text += "\nNote: the arm clamped some values. Requested %s, performed %s." % (
                " ".join(str(v) for v in values),
                " ".join(str(v) for v in actual),
            )
        return text

    def close(self):
        pass


class SerialArm:
    backend = "serial"

    def __init__(self, port):
        import serial  # imported here so the simulator needs no dependencies

        self.pose = list(HOME_POSE)
        self.link = serial.Serial(port, 9600, timeout=15)
        # Opening the port resets the board. Give it time to boot.
        time.sleep(2.0)
        self.link.reset_input_buffer()

    def send(self, values):
        line = " ".join(str(v) for v in values)
        self.link.write((line + "\n").encode("ascii"))
        self.link.flush()
        reply = self.link.readline().decode("ascii", errors="replace").strip()
        if reply.startswith("OK"):
            self.pose = list(values)
        return reply or "(no reply from the arm)"

    def close(self):
        try:
            self.link.close()
        except Exception:
            pass


def open_arm():
    if PORT.strip().lower() in ("sim", "simulator", ""):
        note("using the simulator (set WOZ_PORT to a serial port for real hardware)")
        return SimulatedArm()
    try:
        arm = SerialArm(PORT)
        note("connected to the arm on %s" % PORT)
        return arm
    except Exception as exc:
        note("could not open %s (%s). Falling back to the simulator." % (PORT, exc))
        return SimulatedArm()


ARM = open_arm()
note("software safety check is %s" % ("ON" if SAFETY_ON else "OFF"))


def using_real_hardware():
    return PORT.strip().lower() not in ("sim", "simulator", "")


def release_serial_port():
    """
    Closes the serial connection so that arduino-cli can use the port.
    Only one program can hold a serial port at a time.
    """
    global ARM
    if ARM is not None:
        ARM.close()
        ARM = None
        time.sleep(0.5)


def reopen_serial_port():
    global ARM
    if ARM is None:
        ARM = open_arm()


# ----------------------------------------------------------------------
# Safety check
# ----------------------------------------------------------------------

def safety_problems(values, previous):
    problems = []

    for name, value in zip(JOINT_ORDER, values):
        low, high = JOINT_LIMITS[name]
        if value < low or value > high:
            problems.append(
                "%s = %d is outside the valid range %d to %d."
                % (name, value, low, high)
            )

    if previous:
        for i in range(1, 7):
            change = abs(values[i] - previous[i])
            if change > LARGE_JUMP_DEGREES:
                problems.append(
                    "%s would swing %d degrees in one move, from %d to %d."
                    % (JOINT_ORDER[i], change, previous[i], values[i])
                )

    return problems


# ----------------------------------------------------------------------
# Code generation mode: writing, compiling and uploading Arduino sketches
#
# The direct control tools above send seven numbers to firmware that is already
# on the board. These tools do something different: the agent writes actual
# Arduino source code, compiles it, and uploads it.
#
# The compiler output is passed back to the agent unchanged. That is the point.
# The agent gets to see real error messages and fix its own code.
#
# What the compiler CANNOT tell anybody is whether the arm did the right thing.
# Code that compiles and uploads perfectly can still make the arm miss the
# block, knock it over, or wave in a way no human would call waving. There is
# no sensor for that. The only sensor is a person watching.
# ----------------------------------------------------------------------

import re
import shutil
import subprocess


def arduino_ide_candidates():
    """
    Places the Arduino IDE version 2 keeps its bundled copy of arduino-cli.
    """
    home = os.path.expanduser("~")
    candidates = []

    if sys.platform == "darwin":
        candidates += [
            "/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli",
            os.path.join(home, "Applications/Arduino IDE.app/Contents/Resources/"
                               "app/lib/backend/resources/arduino-cli"),
        ]
    elif sys.platform.startswith("win"):
        for base in (
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("PROGRAMFILES", ""),
            os.environ.get("PROGRAMFILES(X86)", ""),
        ):
            if base:
                candidates.append(os.path.join(
                    base, "Programs", "Arduino IDE", "resources", "app",
                    "lib", "backend", "resources", "arduino-cli.exe"))
                candidates.append(os.path.join(
                    base, "Arduino IDE", "resources", "app",
                    "lib", "backend", "resources", "arduino-cli.exe"))
    else:
        candidates += [
            "/opt/arduino-ide/resources/app/lib/backend/resources/arduino-cli",
            "/usr/local/arduino-ide/resources/app/lib/backend/resources/arduino-cli",
            os.path.join(home, ".arduinoIDE/arduino-cli"),
        ]

    return candidates


def find_arduino_cli():
    """
    Returns the path to a usable arduino-cli, or None.

    Order of preference:
      1. WOZ_ARDUINO_CLI, if the student set it
      2. arduino-cli on the PATH, if it was installed separately
      3. the copy bundled inside the Arduino IDE
    """
    if ARDUINO_CLI_OVERRIDE:
        return ARDUINO_CLI_OVERRIDE

    on_path = shutil.which("arduino-cli")
    if on_path:
        return on_path

    for candidate in arduino_ide_candidates():
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


ARDUINO_CLI = find_arduino_cli()
if ARDUINO_CLI:
    note("arduino-cli: %s" % ARDUINO_CLI)
else:
    note("arduino-cli not found. The code generation tools will explain how to "
         "fix that if they are used.")


def safe_sketch_name(name):
    """Sketch names become folder names, so keep them boring."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", (name or "").strip())
    return cleaned or "agent_sketch"


def sketch_paths(name):
    """arduino-cli requires the folder name to match the .ino file name."""
    safe = safe_sketch_name(name)
    folder = os.path.join(SKETCH_ROOT, safe)
    return safe, folder, os.path.join(folder, safe + ".ino")


def run_arduino_cli(arguments, timeout=180):
    """
    Runs arduino-cli and returns (ok, combined_output).
    The output is returned unchanged so the agent sees real compiler messages.
    """
    if ARDUINO_CLI is None:
        return False, (
            "Cannot compile or upload, because arduino-cli was not found.\n\n"
            "It is normally not a separate download. The Arduino IDE version 2 "
            "includes a copy, and this server looks for it automatically. So "
            "the usual fix is simply to install the Arduino IDE from "
            "https://www.arduino.cc/en/software\n\n"
            "If the IDE is installed somewhere unusual, find the bundled copy "
            "and put its path in WOZ_ARDUINO_CLI in .mcp.json. On macOS it is "
            "normally at:\n"
            "  /Applications/Arduino IDE.app/Contents/Resources/app/lib/"
            "backend/resources/arduino-cli\n\n"
            "A standalone arduino-cli also works: brew install arduino-cli"
        )

    try:
        result = subprocess.run(
            [ARDUINO_CLI] + arguments,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return False, (
            "arduino-cli was found at %s but could not be run." % ARDUINO_CLI
        )
    except subprocess.TimeoutExpired:
        return False, "arduino-cli did not finish within %d seconds." % timeout

    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or "(no output)"

    # Keep the end of the output, because that is where errors appear.
    if len(output) > 6000:
        output = "...(earlier output trimmed)...\n" + output[-6000:]

    return result.returncode == 0, output


def tool_write_sketch(arguments):
    code = arguments.get("code")
    if not code:
        return "Refused: no code was provided.", True

    name, folder, path = sketch_paths(arguments.get("name", "agent_sketch"))

    try:
        os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(code)
    except OSError as exc:
        return "Could not write the sketch: %s" % exc, True

    line_count = len(code.splitlines())
    log_line({"tool": "write_sketch", "sketch": name, "lines": line_count})

    return (
        "Wrote %d lines to %s\n\n"
        "The file exists now, but nothing has been checked. "
        "Call compile_sketch next to find out whether it is valid code."
        % (line_count, path)
    ), False


def tool_compile_sketch(arguments):
    name, folder, path = sketch_paths(arguments.get("name", "agent_sketch"))

    if not os.path.exists(path):
        return (
            "There is no sketch called '%s'. Call write_sketch first." % name
        ), True

    if ARDUINO_CLI is None:
        # The code was never looked at, so do not tell the agent to fix it.
        _, message = run_arduino_cli(["compile"])
        return message, True

    ok, output = run_arduino_cli(["compile", "--fqbn", FQBN, folder])
    log_line({"tool": "compile_sketch", "sketch": name, "ok": ok})

    if ok:
        return (
            "Compiled successfully for board %s.\n\n%s\n\n"
            "Note: compiling only proves the code is valid C++ that fits on the "
            "board. It says nothing about whether the arm will do what you "
            "intended." % (FQBN, output)
        ), False

    return (
        "Compilation FAILED for board %s.\n\n%s\n\n"
        "Read the errors above, fix the code, write it again and recompile."
        % (FQBN, output)
    ), True


def tool_upload_sketch(arguments):
    global FIRMWARE_MODE

    name, folder, path = sketch_paths(arguments.get("name", "agent_sketch"))

    if not os.path.exists(path):
        return "There is no sketch called '%s'. Call write_sketch first." % name, True

    if not using_real_hardware():
        return (
            "Nothing was uploaded, because this session is running against the "
            "simulator (WOZ_PORT is set to 'sim'). Writing and compiling both "
            "work without hardware, but uploading needs a real board.\n\n"
            "To use a real board, set WOZ_PORT in .mcp.json to the serial port "
            "and restart the agent."
        ), True

    release_serial_port()

    ok, output = run_arduino_cli(
        ["upload", "-p", PORT, "--fqbn", FQBN, folder], timeout=240
    )
    log_line({"tool": "upload_sketch", "sketch": name, "ok": ok})

    if not ok:
        reopen_serial_port()
        return (
            "Upload FAILED.\n\n%s\n\n"
            "The board still has whatever was on it before." % output
        ), True

    FIRMWARE_MODE = "custom"

    return (
        "Uploaded '%s' to the board.\n\n%s\n\n"
        "IMPORTANT: the board is now running your sketch instead of the command "
        "interpreter, so move_arm, get_arm_state and home_arm will not work "
        "until you call restore_listener.\n\n"
        "Uploading also resets the board, so the arm has moved to its startup "
        "position. Ask the student what the arm actually did. Nothing in this "
        "system can tell you whether the movement was correct."
        % (name, output)
    ), False


def tool_restore_listener(arguments):
    global FIRMWARE_MODE

    if not using_real_hardware():
        FIRMWARE_MODE = "listener"
        reopen_serial_port()
        return "Running against the simulator, so direct control is available again.", False

    if not os.path.exists(os.path.join(LISTENER_SKETCH, "braccio_listener.ino")):
        return (
            "Could not find the listener firmware at %s" % LISTENER_SKETCH
        ), True

    release_serial_port()
    ok, output = run_arduino_cli(
        ["upload", "-p", PORT, "--fqbn", FQBN, LISTENER_SKETCH], timeout=240
    )
    log_line({"tool": "restore_listener", "ok": ok})

    if not ok:
        return "Could not restore the listener firmware.\n\n%s" % output, True

    FIRMWARE_MODE = "listener"
    reopen_serial_port()
    return (
        "The command interpreter is back on the board. "
        "move_arm, get_arm_state and home_arm work again."
    ), False


# ----------------------------------------------------------------------
# Showing the work in the Arduino IDE
#
# This does not drive the IDE. It opens a sketch in it.
#
# Because the IDE has the file open, it reloads it whenever the file changes.
# So when the agent rewrites the sketch, students watch the new code appear in
# the editor window of the program they already know. Compiling still happens
# through arduino-cli, which gives clean text the agent can actually read.
# ----------------------------------------------------------------------

import ide_tools

IDE_SKETCH_NAME = "agent_ide_sketch"


# ----------------------------------------------------------------------
# Listening to the student
#
# This is what removes the copying and pasting. The agent calls listen, the
# student talks, the recording stops by itself, Whisper transcribes it, and the
# words arrive here as the tool result.
#
# The transcript is passed on exactly as Whisper produced it. It is not tidied
# up and not corrected. If Whisper mishears something, the agent acts on the
# mistake, which is the whole point of Layer 4.
# ----------------------------------------------------------------------

import voice

WHISPER_MODEL = os.environ.get("WOZ_WHISPER_MODEL", "turbo")


def tool_listen(arguments):
    missing = voice.dependencies_missing()
    if missing:
        return missing, True

    was_already_open = voice.window_is_open()

    ok, problem = voice.ensure_window()
    if not ok:
        log_line({"tool": "listen", "ok": False, "message": problem})
        return problem, True

    opening_note = ""
    if not was_already_open:
        opening_note = (
            "A second window called RECORDING has just opened. Tell the "
            "student to put it where they can see it, because it shows when "
            "the microphone is on.\n\n"
        )

    result = voice.request_recording(model=WHISPER_MODEL)

    if not result.get("ok"):
        message = result.get("message", "The recording failed.")
        log_line({"tool": "listen", "ok": False, "message": message})
        return opening_note + message, True

    transcript = result.get("transcript", "")
    log_line({
        "tool": "listen",
        "seconds": result.get("seconds"),
        "audio": result.get("audio"),
        "transcript": transcript,
        "model": WHISPER_MODEL,
    })

    if not transcript:
        return (
            opening_note
            + "The student spoke for %s seconds, and Whisper returned an "
              "EMPTY transcript. Nothing was recognised.\n\n"
              "This is a real result, not a malfunction. Tell them nothing was "
              "heard, and do not guess at what they might have said. Then "
              "listen again." % result.get("seconds")
        ), False

    return (
        opening_note
        + "Recorded %s seconds. Whisper heard:\n\n"
          "    %s\n\n"
          "That is the raw output of the speech recogniser. Nobody has checked "
          "it. If a word looks wrong for a robot arm, it may have been "
          "misheard, and you should ask rather than assume."
          % (result.get("seconds"), transcript)
    ), False


def tool_show_in_ide(arguments):
    name = arguments.get("name", IDE_SKETCH_NAME)
    safe, folder, path = sketch_paths(name)

    code = arguments.get("code")
    os.makedirs(folder, exist_ok=True)

    if code:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(code)
    elif not os.path.exists(path):
        return (
            "There is no sketch called '%s' yet. Provide code, or call "
            "write_sketch first." % safe
        ), True

    ok, message = ide_tools.open_in_ide(path)
    log_line({"tool": "show_in_ide", "sketch": safe, "ok": ok})

    if not ok:
        return message, True

    return (
        "%s\n\nThe students can now see this code in the Arduino IDE:\n  %s\n\n"
        "The IDE reloads the file on its own, so calling write_sketch again "
        "updates what they see. Compile it with compile_sketch."
        % (message, path)
    ), False


def tool_detect_board(arguments):
    ok, output = run_arduino_cli(["board", "list"], timeout=60)
    log_line({"tool": "detect_board", "ok": ok})

    if not ok:
        return output, True

    return (
        "Boards connected to this computer:\n\n%s\n\n"
        "The server is currently configured for FQBN '%s' on port '%s'.\n"
        "If the board listed above has a different FQBN, change WOZ_FQBN in "
        ".mcp.json and restart the agent." % (output, FQBN, PORT)
    ), False


# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------

TOOLS = [
    {
        "name": "move_arm",
        "description": (
            "Move the Braccio robot arm to a set of absolute joint angles. "
            "All seven values are required. This is not a relative movement: "
            "the arm goes to exactly the angles given."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "step_delay": {"type": "integer", "description": "Movement speed, 10 to 30. Lower is faster."},
                "base": {"type": "integer", "description": "Base rotation, 0 to 180."},
                "shoulder": {"type": "integer", "description": "Shoulder angle, 15 to 165."},
                "elbow": {"type": "integer", "description": "Elbow angle, 0 to 180."},
                "wrist_ver": {"type": "integer", "description": "Wrist vertical angle, 0 to 180."},
                "wrist_rot": {"type": "integer", "description": "Wrist rotation, 0 to 180."},
                "gripper": {"type": "integer", "description": "Gripper. 10 is fully open, 73 is fully closed."},
            },
            "required": [
                "step_delay", "base", "shoulder", "elbow",
                "wrist_ver", "wrist_rot", "gripper",
            ],
        },
    },
    {
        "name": "get_arm_state",
        "description": (
            "Report the joint angles the arm was last commanded to. "
            "This is the only sense the arm has. It cannot see the table, "
            "the blocks, or whether a previous movement actually succeeded."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "home_arm",
        "description": "Return the arm to a neutral upright position with the gripper half open.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "write_sketch",
        "description": (
            "Write Arduino source code to a .ino file. This does not check the "
            "code and does not run it. Use compile_sketch afterwards."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The complete contents of the .ino file."},
                "name": {"type": "string", "description": "Short name for the sketch, letters and numbers only."},
            },
            "required": ["code"],
        },
    },
    {
        "name": "compile_sketch",
        "description": (
            "Compile a sketch with arduino-cli and return the compiler output "
            "unchanged. Works without a board connected. Compiling proves the "
            "code is valid, not that the movement is correct."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Which sketch to compile."},
            },
        },
    },
    {
        "name": "upload_sketch",
        "description": (
            "Upload a compiled sketch to the board. This REPLACES the command "
            "interpreter firmware, so move_arm stops working until "
            "restore_listener is called. Requires a real board."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Which sketch to upload."},
            },
        },
    },
    {
        "name": "restore_listener",
        "description": (
            "Put the command interpreter firmware back on the board so that "
            "move_arm, get_arm_state and home_arm work again."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "detect_board",
        "description": "List the Arduino boards connected to this computer and their board types.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "listen",
        "description": (
            "Record the student speaking and return what Whisper heard. A "
            "separate window shows RECORDING while the microphone is on, and "
            "the student presses Enter there when they have finished talking. "
            "This tool waits for them, so it may take a while to return. The "
            "transcript is raw speech recognition output and may contain "
            "mistakes."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "show_in_ide",
        "description": (
            "Open a sketch in the Arduino IDE so the students can see the code "
            "in the program they already know. The IDE reloads the file by "
            "itself, so writing the sketch again updates what they see. This "
            "does not compile or upload anything."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Optional code to write before opening."},
                "name": {"type": "string", "description": "Which sketch to show."},
            },
        },
    },
]


def wrong_firmware_message(tool_name):
    return (
        "%s cannot run right now. The board is running a sketch you uploaded, "
        "not the command interpreter, so it is not listening on the serial "
        "port for movement commands.\n\n"
        "Call restore_listener to put the command interpreter back."
        % tool_name
    )


def tool_move_arm(arguments):
    if FIRMWARE_MODE != "listener":
        return wrong_firmware_message("move_arm"), True

    values = []
    for name in JOINT_ORDER:
        if name not in arguments:
            return "Refused: the value for '%s' is missing. All seven values are required." % name, True
        try:
            values.append(int(arguments[name]))
        except (TypeError, ValueError):
            return "Refused: '%s' was not a whole number." % name, True

    previous = list(ARM.pose)
    problems = safety_problems(values, previous)

    record = {
        "tool": "move_arm",
        "requested": values,
        "previous": previous,
        "safety_on": SAFETY_ON,
        "problems": problems,
    }

    if problems and SAFETY_ON:
        record["result"] = "refused by safety check"
        log_line(record)
        return (
            "Refused by the software safety check. Nothing was sent to the arm.\n"
            + "\n".join("- " + p for p in problems)
            + "\n\nAdjust the values and try again."
        ), True

    reply = ARM.send(values)

    if problems:
        record["result"] = "sent with safety off"
        log_line(record)
        return (
            "Sent with the software safety check switched OFF. "
            "These problems were NOT blocked:\n"
            + "\n".join("- " + p for p in problems)
            + "\n\nArm replied: " + reply
        ), False

    record["result"] = "sent"
    log_line(record)
    return "Arm replied: " + reply, False


def tool_get_arm_state(arguments):
    if FIRMWARE_MODE != "listener" or ARM is None:
        return wrong_firmware_message("get_arm_state"), True

    parts = ["%s = %d" % (name, value) for name, value in zip(JOINT_ORDER, ARM.pose)]
    log_line({"tool": "get_arm_state", "pose": list(ARM.pose)})
    return (
        "Last commanded position:\n"
        + "\n".join("- " + p for p in parts)
        + "\n\nBackend: %s. Software safety check: %s.\n"
          "Remember that this is only what the arm was TOLD to do. "
          "There is no sensor confirming that it worked, and no camera."
          % (ARM.backend, "on" if SAFETY_ON else "off")
    ), False


def tool_home_arm(arguments):
    if FIRMWARE_MODE != "listener" or ARM is None:
        return wrong_firmware_message("home_arm"), True

    reply = ARM.send(list(HOME_POSE))
    log_line({"tool": "home_arm", "result": reply})
    return "Arm replied: " + reply, False


HANDLERS = {
    # Direct control: send numbers to firmware already on the board.
    "move_arm": tool_move_arm,
    "get_arm_state": tool_get_arm_state,
    "home_arm": tool_home_arm,
    # Code generation: write, compile and upload Arduino source code.
    "write_sketch": tool_write_sketch,
    "compile_sketch": tool_compile_sketch,
    "upload_sketch": tool_upload_sketch,
    "restore_listener": tool_restore_listener,
    "detect_board": tool_detect_board,
    # Showing the code in the Arduino IDE so students can watch.
    "show_in_ide": tool_show_in_ide,
    # Hearing the student, so nothing has to be copied or pasted.
    "listen": tool_listen,
}


# ----------------------------------------------------------------------
# JSON-RPC over stdin and stdout
#
# One JSON object per line. A message with an "id" is a request and needs a
# reply. A message without an "id" is a notification and must not be replied to.
# ----------------------------------------------------------------------

def send_message(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def reply_result(request_id, result):
    send_message({"jsonrpc": "2.0", "id": request_id, "result": result})


def reply_error(request_id, code, message):
    send_message({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    })


def handle_initialize(params):
    # Agree on whatever protocol version the client asked for.
    version = params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def handle_tools_call(params):
    name = params.get("name")
    arguments = params.get("arguments") or {}

    handler = HANDLERS.get(name)
    if handler is None:
        return {
            "content": [{"type": "text", "text": "Unknown tool: %s" % name}],
            "isError": True,
        }

    try:
        text, is_error = handler(arguments)
    except Exception as exc:
        text, is_error = "The tool failed: %s: %s" % (type(exc).__name__, exc), True

    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def main():
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            message = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        # Notifications carry no id and expect no reply.
        if request_id is None:
            continue

        if method == "initialize":
            reply_result(request_id, handle_initialize(params))
        elif method == "ping":
            reply_result(request_id, {})
        elif method == "tools/list":
            reply_result(request_id, {"tools": TOOLS})
        elif method == "tools/call":
            reply_result(request_id, handle_tools_call(params))
        elif method in ("resources/list", "prompts/list"):
            # This server offers neither, but some clients ask anyway.
            key = "resources" if method.startswith("resources") else "prompts"
            reply_result(request_id, {key: []})
        else:
            reply_error(request_id, -32601, "Method not found: %s" % method)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        ARM.close()
