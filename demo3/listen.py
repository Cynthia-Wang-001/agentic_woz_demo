"""
listen.py - record your voice, transcribe it with Whisper, put the text on
the clipboard so you can paste it into Claude Code or Codex.

This is the speech half of the lab. It deliberately does NOT talk to the agent
itself. You paste the transcript into the agent's own interface, so that what
you see on screen is the real agent, not a wrapper around it.

Usage:
    python listen.py

    Press Enter to start recording.
    Press Enter again to stop.
    The transcript is printed and copied to the clipboard.
    Paste it into Claude Code or Codex and press Enter.

Whisper is used exactly as the course handout describes:
    ffmpeg -i recording.m4a -ac 1 -ar 16000 recording.wav
    whisper recording.wav --model turbo

Options:
    python listen.py --model small     use a smaller, faster Whisper model
    python listen.py --keep            keep the recordings instead of deleting
    python listen.py --file voice.m4a  transcribe an existing file, no recording
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import threading

SAMPLE_RATE = 16000
RECORDINGS_DIRECTORY = "recordings"


# ----------------------------------------------------------------------
# Recording
# ----------------------------------------------------------------------

def record_until_enter(wav_path):
    """
    Records from the default microphone until the user presses Enter.
    Returns True if audio was captured.
    """
    try:
        import sounddevice
        import numpy
    except ImportError:
        print("\nRecording needs two extra packages:")
        print("    pip install sounddevice numpy")
        print("\nAlternatively, record with any app on your computer and run:")
        print("    python listen.py --file yourrecording.m4a")
        return False

    import wave

    chunks = []
    stop = threading.Event()

    def callback(indata, frames, time_info, status):
        chunks.append(indata.copy())

    print("Recording. Press Enter to stop.")
    stream = sounddevice.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback
    )

    with stream:
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
    stop.set()

    if not chunks:
        print("No audio was captured. Check the microphone permissions.")
        return False

    audio = numpy.concatenate(chunks, axis=0)
    seconds = len(audio) / float(SAMPLE_RATE)

    with wave.open(wav_path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(audio.tobytes())

    print("Captured %.1f seconds." % seconds)
    return True


# ----------------------------------------------------------------------
# Whisper
# ----------------------------------------------------------------------

def convert_to_wav(source, destination):
    subprocess.run(
        ["ffmpeg", "-y", "-i", source, "-ac", "1", "-ar", str(SAMPLE_RATE), destination],
        check=True,
        capture_output=True,
    )


def transcribe(wav_path, model):
    if shutil.which("whisper") is None:
        return None, (
            "The 'whisper' command was not found. Follow the Whisper handout, "
            "and make sure the virtual environment is activated."
        )

    work_directory = tempfile.mkdtemp(prefix="woz_whisper_")
    command = [
        "whisper", wav_path,
        "--model", model,
        "--language", "en",
        "--output_format", "txt",
        "--output_dir", work_directory,
        "--fp16", "False",
    ]

    print("Running Whisper with the %s model. This can take a moment." % model)
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        return None, "Whisper failed:\n" + exc.stderr.decode("utf-8", errors="replace")[-800:]

    base = os.path.splitext(os.path.basename(wav_path))[0]
    transcript_path = os.path.join(work_directory, base + ".txt")
    if not os.path.exists(transcript_path):
        return None, "Whisper ran but produced no transcript file."

    with open(transcript_path, "r", encoding="utf-8") as handle:
        return handle.read().strip(), None


# ----------------------------------------------------------------------
# Clipboard
# ----------------------------------------------------------------------

def copy_to_clipboard(text):
    """Returns True if the text was copied."""
    if sys.platform == "darwin":
        candidates = [["pbcopy"]]
    elif sys.platform.startswith("win"):
        candidates = [["clip"]]
    else:
        candidates = [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]

    for command in candidates:
        if shutil.which(command[0]) is None:
            continue
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            process.communicate(text.encode("utf-8"))
            return process.returncode == 0
        except OSError:
            continue
    return False


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def handle_one(audio_source, model, keep):
    """audio_source is a path to an existing file, or None to record."""
    if shutil.which("ffmpeg") is None:
        print("The 'ffmpeg' command was not found.")
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt install ffmpeg")
        print("  Windows: winget install ffmpeg")
        return

    if keep:
        os.makedirs(RECORDINGS_DIRECTORY, exist_ok=True)
        work_directory = RECORDINGS_DIRECTORY
    else:
        work_directory = tempfile.mkdtemp(prefix="woz_audio_")

    index = 1
    while os.path.exists(os.path.join(work_directory, "take%02d.wav" % index)):
        index += 1
    wav_path = os.path.join(work_directory, "take%02d.wav" % index)

    if audio_source is None:
        if not record_until_enter(wav_path):
            return
    else:
        if not os.path.exists(audio_source):
            print("File not found: %s" % audio_source)
            return
        try:
            convert_to_wav(audio_source, wav_path)
        except subprocess.CalledProcessError as exc:
            print("ffmpeg failed:\n" + exc.stderr.decode("utf-8", errors="replace")[-500:])
            return

    transcript, error = transcribe(wav_path, model)

    print()
    print("=" * 60)
    if error:
        print(error)
        print("=" * 60)
        return

    if not transcript:
        print("Whisper returned an EMPTY transcript.")
        print()
        print("Nothing was said, or nothing was recognised. Write this down:")
        print("an empty result is a real outcome, not a failure of the lab.")
        print("=" * 60)
        return

    print("WHISPER HEARD:")
    print()
    print("  " + transcript)
    print()
    if copy_to_clipboard(transcript):
        print("Copied to the clipboard. Paste it into Claude Code or Codex.")
    else:
        print("Could not reach the clipboard. Copy the text above by hand.")
    print("=" * 60)

    if keep:
        print("Recording kept at %s" % wav_path)


def main():
    parser = argparse.ArgumentParser(description="Record, transcribe with Whisper, copy to clipboard.")
    parser.add_argument("--model", default="turbo",
                        help="Whisper model: turbo, small, base, tiny. Default turbo.")
    parser.add_argument("--keep", action="store_true",
                        help="Keep the recordings in the recordings folder.")
    parser.add_argument("--file", default=None,
                        help="Transcribe an existing audio file instead of recording.")
    args = parser.parse_args()

    if args.file:
        handle_one(args.file, args.model, args.keep)
        return

    print("Whisper model: %s" % args.model)
    print("Press Enter to start recording, or type q then Enter to quit.")

    while True:
        try:
            answer = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if answer in ("q", "quit", "exit"):
            break
        handle_one(None, args.model, args.keep)

    print("Done.")


if __name__ == "__main__":
    main()
