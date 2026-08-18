"""
selftest.py - checks that everything this lab needs is working.

Run this first, and run it again on every lab computer before the session:

    python selftest.py

It checks the environment, then actually drives the MCP server the same way
Claude Code does, so a pass here means the agent will be able to move the arm.

Nothing here touches the network or costs money.

Options:
    python selftest.py --port /dev/ttyACM0    also test a real arm on that port
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"

results = []


def record(status, label, detail=""):
    results.append((status, label, detail))
    marker = {PASS: "[ ok ]", FAIL: "[FAIL]", WARN: "[warn]"}[status]
    print("%s %s" % (marker, label))
    if detail:
        for line in detail.splitlines():
            print("        " + line)


def section(title):
    print()
    print(title)
    print("-" * len(title))


# ----------------------------------------------------------------------
# Environment
# ----------------------------------------------------------------------

def check_python():
    version = sys.version_info
    text = "%d.%d.%d" % (version.major, version.minor, version.micro)
    if version >= (3, 8):
        record(PASS, "Python %s" % text)
    else:
        record(FAIL, "Python %s is too old, 3.8 or newer is needed" % text)


def check_module(name, label, required, hint):
    try:
        __import__(name)
        record(PASS, label)
    except ImportError:
        record(FAIL if required else WARN, "%s not installed" % label, hint)


def check_command(name, label, required, hint):
    path = shutil.which(name)
    if path:
        record(PASS, "%s found" % label, path)
    else:
        record(FAIL if required else WARN, "%s not found" % label, hint)


def check_permissions():
    """
    Reports what the agent is allowed to do, so that it can be checked rather
    than taken on trust.
    """
    path = os.path.join(".claude", "settings.json")
    if not os.path.exists(path):
        record(WARN, "No permission list found",
               "Without .claude/settings.json the agent arrives with its full\n"
               "default toolset and students will be asked to approve all of it.")
        return

    try:
        with open(path, "r", encoding="utf-8") as handle:
            settings = json.load(handle)
    except json.JSONDecodeError as exc:
        record(FAIL, ".claude/settings.json is not valid JSON", str(exc))
        return

    permissions = settings.get("permissions", {})
    allowed = permissions.get("allow", [])
    denied = permissions.get("deny", [])

    record(PASS, "Permission list found",
           "Allowed without asking: %d\nDenied outright:         %d"
           % (len(allowed), len(denied)))

    dangerous = ["Bash", "Write", "Edit", "WebFetch"]
    missing = [name for name in dangerous if name not in denied]
    if missing:
        record(WARN, "Some powerful tools are not denied",
               "Not in the deny list: %s\n"
               "The lab does not need any of them." % ", ".join(missing))
    else:
        record(PASS, "Shell, file editing and network access are all denied")

    acts_physically = ["move_arm", "upload_sketch", "home_arm", "restore_listener"]
    auto = [name for name in acts_physically
            if "mcp__braccio__" + name in allowed]
    if auto:
        record(WARN, "Some physical actions run without asking",
               "Auto-approved: %s\n"
               "The approval prompt is the human wizard in this lab. Remove\n"
               "these from the allow list unless you are deliberately running\n"
               "the no-oversight condition." % ", ".join(auto))
    else:
        record(PASS, "Every physical action still asks a human first")


def check_arduino_cli():
    """
    arduino-cli is only needed for the code generation mode, so a missing one
    is a warning rather than a failure.

    It is usually not a separate download: the Arduino IDE version 2 ships with
    a copy inside it. The same search that arm_mcp_server.py performs is used
    here, so both report the same thing.
    """
    # Reuse the server's own search so the two never disagree.
    sys.path.insert(0, os.getcwd())
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_woz_server_probe", "arm_mcp_server.py")
        module = importlib.util.module_from_spec(spec)
        # Importing the server opens the arm, so keep it on the simulator.
        os.environ.setdefault("WOZ_PORT", "sim")
        spec.loader.exec_module(module)
        path = module.ARDUINO_CLI
    except Exception:
        path = shutil.which("arduino-cli")

    if path is None:
        record(WARN, "arduino-cli not found",
               "Only needed for the code generation mode.\n"
               "It normally comes with the Arduino IDE version 2. Installing\n"
               "the IDE from https://www.arduino.cc/en/software is enough.\n"
               "A standalone copy also works: brew install arduino-cli")
        return

    if "Arduino IDE" in path or "arduino-ide" in path or "arduinoIDE" in path:
        record(PASS, "arduino-cli found, bundled with the Arduino IDE", path)
    else:
        record(PASS, "arduino-cli found", path)

    def ask(arguments):
        return subprocess.run([path] + arguments, capture_output=True,
                              text=True, timeout=90).stdout

    try:
        if "arduino:avr" in ask(["core", "list"]):
            record(PASS, "Arduino AVR core installed")
        else:
            record(WARN, "Arduino AVR core not installed",
                   "Install the board support in the Arduino IDE Boards Manager,\n"
                   'or run: "%s" core install arduino:avr' % path)
    except Exception as exc:
        record(WARN, "Could not list Arduino cores", str(exc))

    try:
        if "Braccio" in ask(["lib", "list"]):
            record(PASS, "Braccio library installed")
        else:
            record(WARN, "Braccio library not installed",
                   "Install Braccio in the Arduino IDE Library Manager,\n"
                   'or run: "%s" lib install Braccio' % path)
    except Exception as exc:
        record(WARN, "Could not list Arduino libraries", str(exc))


def check_files():
    needed = [
        "arm_mcp_server.py",
        "voice.py",
        "record_window.py",
        "ide_tools.py",
        "listen.py",
        "test_arm.py",
        "arm.py",
        "CLAUDE.md",
        ".mcp.json",
        os.path.join(".claude", "commands", "woz.md"),
        os.path.join(".claude", "settings.json"),
    ]
    missing = [name for name in needed if not os.path.exists(name)]
    if missing:
        record(FAIL, "Some files are missing",
               "Missing: %s\nAre you running this from inside the lab folder?"
               % ", ".join(missing))
    else:
        record(PASS, "All expected files are present")

    if not os.path.exists("AGENTS.md"):
        record(WARN, "AGENTS.md is missing",
               "Codex reads AGENTS.md. Create it with: cp CLAUDE.md AGENTS.md")


def check_mcp_json():
    if not os.path.exists(".mcp.json"):
        record(FAIL, ".mcp.json is missing")
        return None

    try:
        with open(".mcp.json", "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as exc:
        record(FAIL, ".mcp.json is not valid JSON", str(exc))
        return None

    try:
        server = config["mcpServers"]["braccio"]
        environment = server.get("env", {})
    except (KeyError, TypeError):
        record(FAIL, ".mcp.json does not define the 'braccio' server")
        return None

    port = environment.get("WOZ_PORT", "sim")
    safety = environment.get("WOZ_SAFETY", "on")
    record(PASS, ".mcp.json is valid",
           "WOZ_PORT   = %s\nWOZ_SAFETY = %s" % (port, safety))
    return environment


# ----------------------------------------------------------------------
# The MCP server, driven exactly the way Claude Code drives it
# ----------------------------------------------------------------------

def talk_to_server(messages, environment):
    env = dict(os.environ)
    env.update(environment)
    process = subprocess.Popen(
        [sys.executable, "arm_mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    payload = "".join(json.dumps(m) + "\n" for m in messages)
    out, err = process.communicate(payload, timeout=90)
    replies = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" in message:
            replies[message["id"]] = message
    return replies, err


def check_server(port, safety):
    environment = {"WOZ_PORT": port, "WOZ_SAFETY": safety, "WOZ_LOG": "logs/selftest.jsonl"}

    good = {"step_delay": 20, "base": 45, "shoulder": 120,
            "elbow": 90, "wrist_ver": 90, "wrist_rot": 90, "gripper": 10}
    bad = dict(good)
    bad["shoulder"] = 200

    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "selftest", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "get_arm_state", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "move_arm", "arguments": good}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "move_arm", "arguments": bad}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "home_arm", "arguments": {}}},
    ]

    try:
        replies, stderr = talk_to_server(messages, environment)
    except subprocess.TimeoutExpired:
        record(FAIL, "The MCP server did not respond in time")
        return
    except Exception as exc:
        record(FAIL, "Could not start the MCP server", str(exc))
        return

    if 1 not in replies or "result" not in replies[1]:
        record(FAIL, "The server did not complete the handshake",
               "stderr:\n" + stderr.strip())
        return
    record(PASS, "Handshake completed",
           "server: %s" % replies[1]["result"]["serverInfo"]["name"])

    tools = [t["name"] for t in replies.get(2, {}).get("result", {}).get("tools", [])]
    expected = [
        "move_arm", "get_arm_state", "home_arm",
        "write_sketch", "compile_sketch", "upload_sketch",
        "restore_listener", "detect_board", "show_in_ide", "listen",
    ]
    missing = [name for name in expected if name not in tools]
    if missing:
        record(FAIL, "Some tools are missing", "Missing: %s" % ", ".join(missing))
    else:
        record(PASS, "All %d tools offered" % len(tools))

    state = replies.get(3, {}).get("result", {})
    if state and not state.get("isError"):
        record(PASS, "get_arm_state works")
    else:
        record(FAIL, "get_arm_state failed", json.dumps(state))

    move = replies.get(4, {}).get("result", {})
    if move and not move.get("isError"):
        record(PASS, "A valid move was accepted",
               move["content"][0]["text"].splitlines()[0])
    else:
        record(FAIL, "A valid move was rejected", json.dumps(move))

    bad_move = replies.get(5, {}).get("result", {})
    bad_text = bad_move.get("content", [{}])[0].get("text", "")
    if safety == "on":
        if bad_move.get("isError"):
            record(PASS, "Safety check ON refused an out-of-range move",
                   bad_text.splitlines()[0])
        else:
            record(FAIL, "Safety check ON did NOT refuse an out-of-range move", bad_text)
    else:
        if not bad_move.get("isError") and "NOT blocked" in bad_text:
            record(PASS, "Safety check OFF let the move through and said so")
        else:
            record(FAIL, "Safety check OFF behaved unexpectedly", bad_text)

    home = replies.get(6, {}).get("result", {})
    if home and not home.get("isError"):
        record(PASS, "home_arm works")
    else:
        record(FAIL, "home_arm failed", json.dumps(home))

    backend = "serial" if "connected to the arm" in stderr else "simulator"
    if port not in ("sim", "simulator", ""):
        if backend == "serial":
            record(PASS, "Connected to the real arm on %s" % port)
        else:
            record(FAIL, "Could not open %s, fell back to the simulator" % port,
                   stderr.strip())


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Check that the lab setup works.")
    parser.add_argument("--port", default=None,
                        help="Also test a real arm on this serial port.")
    args = parser.parse_args()

    print("Agentic Wizard of Oz - self test")
    print("Working directory: %s" % os.getcwd())

    section("1. Python and files")
    check_python()
    check_files()
    environment = check_mcp_json()

    section("2. What the agent is allowed to do")
    check_permissions()

    section("3. Packages")
    check_module("serial", "pyserial", False,
                 "Only needed for a real arm. Install with: pip install pyserial")
    check_module("sounddevice", "sounddevice", False,
                 "Only needed to record. Install with: pip install sounddevice numpy")
    check_module("numpy", "numpy", False,
                 "Only needed to record. Install with: pip install numpy")

    section("4. External tools")
    check_command("ffmpeg", "ffmpeg", False,
                  "Needed for Whisper.\n"
                  "  macOS   brew install ffmpeg\n"
                  "  Ubuntu  sudo apt install ffmpeg\n"
                  "  Windows winget install ffmpeg")
    check_command("whisper", "whisper", False,
                  "Needed for Layer 4.\n"
                  "  python3 -m pip install git+https://github.com/openai/whisper.git")
    check_command("node", "Node.js", False,
                  "Needed by Claude Code and Codex. https://nodejs.org")

    found_agent = False
    for command, label in (("claude", "Claude Code"), ("codex", "Codex")):
        if shutil.which(command):
            record(PASS, "%s found" % label, shutil.which(command))
            found_agent = True
    if not found_agent:
        record(WARN, "No agent CLI found",
               "npm install -g @anthropic-ai/claude-code\n"
               "npm install -g @openai/codex")

    check_arduino_cli()

    section("5. MCP server with the simulator, safety ON")
    check_server("sim", "on")

    section("6. MCP server with the simulator, safety OFF")
    check_server("sim", "off")

    if args.port:
        section("7. MCP server with the real arm on %s" % args.port)
        print("The arm will move. Keep the area clear.")
        check_server(args.port, "on")

    section("Summary")
    failures = [r for r in results if r[0] == FAIL]
    warnings = [r for r in results if r[0] == WARN]
    print("%d checks, %d failed, %d warnings."
          % (len(results), len(failures), len(warnings)))

    if failures:
        print()
        print("These must be fixed:")
        for _, label, _ in failures:
            print("  - " + label)
    if warnings:
        print()
        print("These are optional, depending on what you are testing today:")
        for _, label, _ in warnings:
            print("  - " + label)
    if not failures:
        print()
        print("Ready. Start the agent with:  claude")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
