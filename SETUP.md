# Installation and Setup

Follow these steps in order. Each one ends with a command that tells you whether
it worked.

Commands are given for macOS and for Windows PowerShell. Use the ones that match
your computer.

## 1. Check the basics

- Python 3.8 or newer
- Node.js 18 or newer
- A microphone
- About 40 minutes, most of it downloads

Check Python and Node:

```bash
python3 --version
node --version
```

Windows PowerShell:

```powershell
python --version
node --version
```

If Node is missing, install it from <https://nodejs.org>.

## 2. Get the files

```bash
git clone <repository link>
cd <folder it created>
```

If `git` is not installed, download the ZIP from the repository page instead:
click the green **Code** button, choose **Download ZIP**, unzip it, and open a
terminal in the folder.

Check you are in the right place:

```bash
ls
```

Windows PowerShell:

```powershell
dir
```

You should see `SETUP.md`, `arm_mcp_server.py` and `requirements.txt`.
**Every command below is run from this folder.**

## 3. Create a virtual environment

macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Your prompt now starts with `(venv)`. Run the activate command again in every
new terminal window.

## 4. Install the Python packages

```bash
pip install -r requirements.txt
```

Check:

```bash
python -c "import serial, sounddevice, numpy; print('ok')"
```

## 5. Install ffmpeg

macOS:

```bash
brew install ffmpeg
```

If `brew` is missing, install Homebrew from <https://brew.sh> first.

Windows PowerShell:

```powershell
winget install ffmpeg
```

Close and reopen the terminal, then check:

```bash
ffmpeg -version
```

## 6. Install Whisper

```bash
pip install openai-whisper
```

This pulls in PyTorch and takes 5 to 15 minutes. Check:

```bash
whisper --help
```

## 7. Download the Whisper model

The previous step installed the program, not the model. The model is a separate
1.5 GB file, downloaded the first time you transcribe anything.

If your instructor gave you the file, put it in place by hand.

macOS:

```bash
mkdir -p ~/.cache/whisper
mv ~/Downloads/large-v3-turbo.pt ~/.cache/whisper/
```

Windows PowerShell:

```powershell
mkdir "$env:USERPROFILE\.cache\whisper" -Force
move "$env:USERPROFILE\Downloads\large-v3-turbo.pt" "$env:USERPROFILE\.cache\whisper\"
```

Otherwise let Whisper fetch it:

```bash
whisper --model turbo --language en any_audio_file.m4a
```

Check the file is there.

macOS:

```bash
ls -lh ~/.cache/whisper/
```

Windows PowerShell:

```powershell
dir "$env:USERPROFILE\.cache\whisper\"
```

`large-v3-turbo.pt` should be about 1.5 GB. If it is much smaller, delete it and
download again.

## 8. Install the Arduino IDE

Download it from <https://www.arduino.cc/en/software>.

Inside the IDE, install:

- **Boards Manager:** Arduino AVR Boards
- **Library Manager:** Braccio

Nothing else is needed. The lab uses the copy of `arduino-cli` that comes inside
the IDE, and finds it automatically.

## 9. Install and sign in to Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Check:

```bash
claude --version
```

Installing is not the same as signing in. Start it once:

```bash
claude
```

The first run asks you to sign in. Your instructor will tell you whether to use
a Claude account or an API key. Inside Claude Code, check with:

```
/status
```

Type `/exit` to leave.

## 10. Upload the firmware to the arm

Skip this if your instructor has already done it, or if you are working without
hardware.

1. Open `firmware/braccio_listener/braccio_listener.ino` in the Arduino IDE
2. Under **Tools**, select the board and the port
3. Click **Upload**

Check it with **Tools > Serial Monitor**, set to 9600 baud with the line ending
set to **Newline**. Type:

```
20 90 120 90 90 90 30
```

The arm moves and replies `OK 20 90 120 90 90 90 30`.

Close the Serial Monitor afterwards. Only one program can use the port at a
time.

## 11. Run the self test

```bash
python selftest.py
```

The last lines should say `0 failed`. Lines marked `[warn]` are optional.

## 12. Test the arm without the agent

```bash
python test_arm.py
```

Type seven numbers and press Enter:

```
20 90 120 90 90 90 30
```

Type `quit` to exit.

No arm? Use the simulator:

```bash
python test_arm.py --sim
```

## 13. Connect to a real arm

Skip this to stay on the simulator.

Find the port name:

```bash
python test_arm.py
```

It lists the ports it can see. They look like `/dev/tty.usbmodem14201` on macOS
and `COM3` on Windows.

Open `.mcp.json` and change `"WOZ_PORT": "sim"` to your port name. Restart
Claude Code after editing this file.

## 14. Start the lab

```bash
claude
```

Check the arm tools are connected:

```
/mcp
```

`braccio` should be listed. Then start the session:

```
/woz
```

That is the last thing you type. A second window opens and shows what the
microphone is doing:

| The window shows | What to do |
|---|---|
| **WAITING**, green | Nothing |
| **RECORDING**, red | Speak, then press Enter in that window |
| **WORKING**, yellow | Wait |
| **HEARD**, blue | Read what it understood |

Approve or reject each movement in the Claude Code window. Say "stop" to finish.

## Troubleshooting

**A command worked yesterday and not today**

The virtual environment is not active. Run `source venv/bin/activate` on macOS,
or `venv\Scripts\Activate.ps1` on Windows.

**`FileNotFoundError: 'ffmpeg'`**

ffmpeg is not installed. Go back to step 5.

**`CERTIFICATE_VERIFY_FAILED` while downloading the Whisper model**

macOS:

```bash
open "/Applications/Python 3.11/Install Certificates.command"
```

Or download the model with `curl`, which uses the system certificates:

```bash
mkdir -p ~/.cache/whisper
cd ~/.cache/whisper
curl -L -O https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt
```

Or ask your instructor for the file and follow step 7.

**`/woz` is not a command, or `braccio` is missing from `/mcp`**

You started `claude` from the wrong folder. Quit, `cd` into the lab folder, and
start it again.

**The `listen` tool cannot find whisper**

You started `claude` without activating the virtual environment first. Quit,
activate it, then start `claude` again.

**The RECORDING window did not open**

Open a second terminal, activate the virtual environment, and run:

```bash
python record_window.py
```

**Recording captures nothing**

Give the terminal permission to use the microphone. macOS: System Settings,
Privacy and Security, Microphone. Quit and reopen the terminal afterwards.

**Uploading to the arm fails with a port error**

Something else is using the serial port. Close the Arduino Serial Monitor and
any other terminal running `test_arm.py`.

**Compiling fails with `Braccio.h: No such file or directory`**

Install the Braccio library in the Arduino IDE Library Manager.

## Command reference

Every session starts with these, in the lab folder:

```bash
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
claude
```

| Command | What it does |
|---|---|
| `python selftest.py` | Check the setup |
| `python test_arm.py` | Drive the arm by hand |
| `python test_arm.py --sim` | Same, with the simulator |
| `claude` | Start the agent |
| `/woz` | Start the voice session |
| `/mcp` | Check the arm tools are connected |
| `/status` | Check which account is in use |
| `python listen.py` | Record and transcribe by hand |
| `python record_window.py` | Open the recording window by hand |
