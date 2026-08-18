"""
record_window.py - the recording window the student actually looks at.

This runs in its own terminal window, next to the agent. It stays open for the
whole session and always shows what is happening:

    WAITING     the agent is thinking, or the arm is moving
    RECORDING   the microphone is open, speak, press Enter when finished
    WORKING     Whisper is turning the recording into text

The student never types anything here except Enter.

WHY THIS IS A SEPARATE WINDOW
-----------------------------
The arm server talks to Claude Code over its own standard input, so it has no
keyboard of its own and cannot notice you pressing Enter. This window has a
keyboard. The two halves pass messages through small files in logs/voice, which
is unglamorous and completely reliable.

Students do not run this by hand. The agent opens it the first time it needs to
listen.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import wave

SAMPLE_RATE = 16000
BLOCK_FRAMES = 1024
HEARTBEAT_SECONDS = 1.0

BANNER_WIDTH = 62


def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def banner(title, lines, colour):
    """colour: 32 green, 31 red, 33 yellow, 36 cyan."""
    clear()
    bar = "=" * BANNER_WIDTH
    print("\033[%dm%s" % (colour, bar))
    print(title.center(BANNER_WIDTH))
    print(bar + "\033[0m")
    print()
    for line in lines:
        print("  " + line)
    print()
    sys.stdout.flush()


class Paths:
    def __init__(self, project_directory):
        self.root = os.path.join(project_directory, "logs", "voice")
        os.makedirs(self.root, exist_ok=True)
        self.heartbeat = os.path.join(self.root, "heartbeat")
        self.request = os.path.join(self.root, "request.json")
        self.result = os.path.join(self.root, "result.json")
        self.recordings = os.path.join(project_directory, "recordings")
        os.makedirs(self.recordings, exist_ok=True)


def start_heartbeat(paths, stop_event):
    """Lets the arm server know this window is still open."""
    def beat():
        while not stop_event.is_set():
            try:
                with open(paths.heartbeat, "w") as handle:
                    handle.write(str(time.time()))
            except OSError:
                pass
            stop_event.wait(HEARTBEAT_SECONDS)

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    return thread


def record_until_enter(wav_path):
    """
    Records until the student presses Enter.
    Returns (ok, message, seconds).
    """
    import numpy
    import sounddevice

    chunks = []

    def callback(indata, frames, time_info, status):
        chunks.append(indata.copy())

    try:
        stream = sounddevice.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16",
            blocksize=BLOCK_FRAMES, callback=callback,
        )
    except Exception as exc:
        return False, (
            "Could not open the microphone: %s\n"
            "On macOS: System Settings, Privacy and Security, Microphone." % exc
        ), 0.0

    with stream:
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass

    if not chunks:
        return False, "No audio was captured.", 0.0

    audio = numpy.concatenate(chunks, axis=0)
    seconds = len(audio) / float(SAMPLE_RATE)

    with wave.open(wav_path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(audio.tobytes())

    return True, "Recorded %.1f seconds." % seconds, seconds


def transcribe(wav_path, model):
    """Runs the Whisper command line tool, as the course handout does."""
    work = tempfile.mkdtemp(prefix="woz_win_")
    command = [
        "whisper", wav_path,
        "--model", model,
        "--language", "en",
        "--output_format", "txt",
        "--output_dir", work,
        "--fp16", "False",
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=600)
    except FileNotFoundError:
        return False, (
            "The whisper command was not found in this window. The agent was "
            "started without the virtual environment active."
        )
    except subprocess.CalledProcessError as exc:
        return False, "Whisper failed:\n" + exc.stderr.decode("utf-8", errors="replace")[-600:]
    except subprocess.TimeoutExpired:
        return False, "Whisper took too long."

    base = os.path.splitext(os.path.basename(wav_path))[0]
    path = os.path.join(work, base + ".txt")
    if not os.path.exists(path):
        return False, "Whisper produced no transcript file."

    with open(path, "r", encoding="utf-8") as handle:
        return True, handle.read().strip()


def write_result(paths, payload):
    temporary = paths.result + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    os.replace(temporary, paths.result)


def handle_request(paths, request):
    turn = request.get("id", 0)
    model = request.get("model", "turbo")

    banner("RECORDING", [
        "Speak your instruction now.",
        "",
        "\033[1mPress Enter when you have finished.\033[0m",
    ], 31)

    wav_path = os.path.join(paths.recordings, "turn%03d.wav" % turn)
    ok, message, seconds = record_until_enter(wav_path)

    if not ok:
        banner("PROBLEM", [message], 31)
        write_result(paths, {"id": turn, "ok": False, "message": message})
        time.sleep(2)
        return

    banner("WORKING", [
        message,
        "",
        "Whisper is turning it into text. This takes a moment.",
    ], 33)

    ok, result = transcribe(wav_path, model)

    if not ok:
        banner("PROBLEM", [result], 31)
        write_result(paths, {"id": turn, "ok": False, "message": result})
        time.sleep(3)
        return

    write_result(paths, {
        "id": turn,
        "ok": True,
        "transcript": result,
        "seconds": round(seconds, 1),
        "audio": wav_path,
        "message": message,
    })

    banner("HEARD", [
        result if result else "(nothing was recognised)",
        "",
        "Sent to the agent.",
    ], 36)
    time.sleep(1.5)


def main():
    project_directory = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    paths = Paths(project_directory)

    stop_event = threading.Event()
    start_heartbeat(paths, stop_event)

    try:
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        banner("CANNOT RECORD", [
            "sounddevice and numpy are not installed in this environment.",
            "",
            "    pip install sounddevice numpy",
            "",
            "Close this window, fix that, and start the agent again.",
        ], 31)
        input()
        return

    last_id = None

    while True:
        banner("WAITING", [
            "Nothing to do yet.",
            "",
            "When the agent is ready to listen, this window turns red",
            "and you speak.",
            "",
            "Leave this window open. Close it to end the session.",
        ], 32)

        # Wait for the agent to ask for a recording.
        while True:
            if os.path.exists(paths.request):
                try:
                    with open(paths.request, "r", encoding="utf-8") as handle:
                        request = json.load(handle)
                except (OSError, json.JSONDecodeError):
                    time.sleep(0.15)
                    continue

                if request.get("id") != last_id:
                    last_id = request.get("id")
                    try:
                        os.remove(paths.request)
                    except OSError:
                        pass
                    break
            time.sleep(0.15)

        handle_request(paths, request)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        print("Recording window closed.")
