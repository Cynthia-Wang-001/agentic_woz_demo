# Setup Guide

ROB 340: Human Evaluation of Robots - Lab 5, Part 1.2 (extension)

Follow this from top to bottom. After most steps there is a **Check** box.
Do not move on until the check passes. If a check fails, look for the error in
Part E at the end of this document before asking for help.

**Time needed:** about 40 minutes the first time, most of it waiting for
downloads. If your instructor has already prepared the lab computers, skip to
Part C.

**What you will end up with:** you type `/woz` once, and after that you only
speak. The agent listens, works out what to do, writes and compiles code where
it needs to, and moves a robot arm. You never copy or paste anything.

---

## Before you start

You need:

- A laptop with macOS, Windows, or Linux
- Python 3.8 or newer
- A terminal window (macOS: Terminal or iTerm. Windows: PowerShell)
- The lab files, from GitHub or from your instructor
- An account or API key for Claude Code, provided by your instructor

You do **not** need a robot arm to complete this setup. Everything runs against
a built-in simulator until you switch it over.

### Opening a terminal in the right place

Every command in this guide must be run from inside the lab folder, the one
holding `SETUP.md` and `arm_mcp_server.py`.

```bash
cd path/to/the/lab/folder
```

**Check:** run `ls` (macOS/Linux) or `dir` (Windows). You should see
`arm_mcp_server.py`, `CLAUDE.md`, `README.md` and `requirements.txt` in the
list. If you see a single folder name instead, go one level deeper and look
again.

---

# Part A: Install

## Step 1. Create a virtual environment

A virtual environment keeps this lab's packages separate from everything else
on your computer, so nothing you install here can break your other projects.

macOS and Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Check:** your terminal prompt now starts with `(venv)`. If it does not, the
environment is not active and everything after this will go to the wrong place.

**Important:** you must run `source venv/bin/activate` again every time you
open a new terminal window. If a command suddenly stops working later, this is
usually why.

## Step 2. Install the Python packages

```bash
pip install -r requirements.txt
```

**Check:**

```bash
python -c "import serial, sounddevice, numpy; print('packages ok')"
```

This should print `packages ok`.

## Step 3. Install ffmpeg

Whisper uses ffmpeg to read audio files. It is not a Python package, so it
installs differently.

**macOS:**

```bash
brew install ffmpeg
```

If `brew` is not found, install Homebrew first from https://brew.sh

**Windows:**

```powershell
winget install ffmpeg
```

**Linux:**

```bash
sudo apt install ffmpeg
```

**No administrator rights?** There is a Python-only fallback that installs
inside your virtual environment:

```bash
pip install imageio-ffmpeg
```

macOS and Linux, then link it so Whisper can find it:

```bash
ln -s "$(python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" venv/bin/ffmpeg
```

**Check:**

```bash
ffmpeg -version
```

This should print several lines of version information. If it says "command not
found", ffmpeg is not installed correctly and Whisper will fail later with
`FileNotFoundError: 'ffmpeg'`.

## Step 4. Install Whisper

```bash
pip install openai-whisper
```

This downloads PyTorch as well, which is large. **Expect this to take 5 to 15
minutes.** It will look like it has frozen. It has not.

**Check:**

```bash
whisper --help
```

This should print a long list of options.

## Step 5. Get the Whisper model weights

This step confuses people, so read it carefully.

Step 4 installed the Whisper **program**. It did not install the **model**, the
file containing what Whisper has learned. That file is about 1.5 GB and is
downloaded separately the first time you transcribe anything.

**If your instructor gave you the model file**, put it in place by hand. This is
the fastest and most reliable option, and it does not use the network at all.

macOS and Linux:

```bash
mkdir -p ~/.cache/whisper
mv ~/Downloads/large-v3-turbo.pt ~/.cache/whisper/
```

Windows PowerShell:

```powershell
mkdir "$env:USERPROFILE\.cache\whisper" -Force
move "$env:USERPROFILE\Downloads\large-v3-turbo.pt" "$env:USERPROFILE\.cache\whisper\"
```

The file name must be exactly `large-v3-turbo.pt`.

**If you need to download it yourself**, transcribe anything once and Whisper
fetches the model automatically:

```bash
whisper --model turbo --language en some_audio_file.m4a
```

The first run prints a download progress bar. Later runs skip it.

**Warning:** do not do this for the first time during the lab session. If
everybody downloads 1.5 GB at once, the lab wifi will stop working for the whole
room.

**Check:**

macOS and Linux:

```bash
ls -lh ~/.cache/whisper/
```

Windows:

```powershell
dir "$env:USERPROFILE\.cache\whisper\"
```

You should see `large-v3-turbo.pt` at roughly 1.5 GB. If the file is much
smaller, the download was interrupted. Delete it and try again.

Optional, confirm the file is not corrupted (macOS and Linux):

```bash
shasum -a 256 ~/.cache/whisper/large-v3-turbo.pt
```

The result should be:

```
aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a
```

## Step 6. Arduino IDE

The agent can write Arduino code, compile it, and upload it by itself. To do
that it needs `arduino-cli`, the command line version of the Arduino IDE.

**You almost certainly do not need to install anything new.** The Arduino IDE
version 2 ships with a copy of `arduino-cli` inside it, and this lab finds that
copy automatically. If you installed the Arduino IDE for Lab 1, you are done.

If you do not have it, get it from https://www.arduino.cc/en/software

Using the IDE's own copy has a second advantage: it reads the same settings and
library folders as the IDE, so the Braccio library you installed through the
IDE Library Manager is found automatically.

Make sure the Arduino IDE has these two things, which you can install from
inside the IDE itself:

- **Boards Manager:** Arduino AVR Boards
- **Library Manager:** Braccio

**Check:** the self test in Step 8 reports where it found `arduino-cli` and
whether the board support and the Braccio library are installed.

If your IDE is in an unusual place, find the bundled copy and put its full path
into `WOZ_ARDUINO_CLI` in `.mcp.json`. On macOS it normally lives at:

```
/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli
```

A separately installed `arduino-cli` also works, if you prefer:

```bash
brew install arduino-cli
```

## Step 7. Install Claude Code

Claude Code needs Node.js. Check whether you already have it:

```bash
node --version
```

If that fails, install Node.js from https://nodejs.org and open a new terminal.

Then:

```bash
npm install -g @anthropic-ai/claude-code
```

**Check:**

```bash
claude --version
```

### Signing in

Installing Claude Code is not the same as being able to use it. The first time
you run `claude` it will ask you to sign in, and it will not do anything until
you have. Signing in is stored for your whole computer, not per folder, so you
only do this once.

There are two ways, and **your instructor will tell you which one this class is
using**:

**A Claude account.** Run `claude`, and it opens a browser window to log in.
Usage comes out of that account's plan.

**An API key.** Put the key in your environment before starting the agent:

```bash
export ANTHROPIC_API_KEY=the-key-your-instructor-gave-you
claude
```

Usage is billed to whoever owns that key. Add the `export` line to your
`~/.zshrc` if you do not want to type it every session.

**Check:** start `claude` and type

```
/status
```

It shows which account or key is in use. If you see a login prompt instead,
you are not signed in yet.

**Do this before the lab session.** If six groups all sign in for the first
time at the start of class, that alone can cost fifteen minutes.

## Step 8. Run the self test

```bash
python selftest.py
```

This checks everything above, then talks to the robot arm server the same way
Claude Code will.

**Check:** the last lines should say `0 failed`.

Lines marked `[warn]` are fine. They mark optional pieces. Lines marked
`[FAIL]` must be fixed before you continue. The output tells you what to do for
each one.

---

# Part B: Look inside before you run it

**Do not skip this part. It is the point of the lab.**

When you use a chatbot in a browser, the instructions the AI was given are
hidden from you. In this lab they are a text file on your own computer. You can
read them, change them, and see what changes.

## What the agent is told: CLAUDE.md

Open `CLAUDE.md` in any text editor. You can also read it in the terminal:

```bash
cat CLAUDE.md
```

Read the whole thing. It is short on purpose. Notice three things:

1. **The joint ranges.** The agent is simply told, in a table, what numbers the
   arm accepts. It has no other knowledge of the hardware.
2. **The section headed "What you cannot do".** The agent is told it has no
   camera and no sensors, and that everything it knows about the table comes
   from what you tell it.
3. **How short it is.** It has not been written to stop the agent making
   mistakes. Finding those mistakes is your job today.

**Question to answer in your report:** before running anything, predict one
kind of mistake this agent will make, based only on what you just read.

## What the agent can do: arm_mcp_server.py

The agent cannot do anything except through the tools defined in this file.
Open it and search for `TOOLS = [`, or list them:

```bash
grep -n '"name": "' arm_mcp_server.py
```

There are eight, in two groups.

**Direct control** - send numbers to firmware already on the board:

| Tool | What it does |
|---|---|
| `move_arm` | Move to seven joint angles |
| `get_arm_state` | Report the last commanded angles |
| `home_arm` | Return to the neutral pose |

**Code generation** - write and run actual Arduino code:

| Tool | What it does |
|---|---|
| `write_sketch` | Save source code to a `.ino` file |
| `compile_sketch` | Compile it, and return the real compiler output |
| `upload_sketch` | Put it on the board |
| `restore_listener` | Put the original firmware back |
| `detect_board` | List connected boards |
| `show_in_ide` | Open the sketch in the Arduino IDE |

**Hearing you** - the reason you never type:

| Tool | What it does |
|---|---|
| `listen` | Record you speaking, transcribe it with Whisper, return the words |

That is the agent's entire ability to affect the world. It cannot see, and it
cannot check its own work.

Read the description of `get_arm_state` in particular. It reports the angles the
arm was **told** to go to, not where the arm actually is. Nothing in this system
confirms that a movement succeeded.

## What the agent is allowed to touch, and what leaves your computer

An agent that can run commands on your laptop is a reasonable thing to be
cautious about. Here is exactly what this one can and cannot do, and how to
check for yourself rather than taking anybody's word for it.

### The permission list

`.claude/settings.json` in this folder controls it. Open it and read it. It is
about twenty lines.

**Switched off completely.** The agent cannot use any of these, and cannot ask
for them either:

| Blocked | What it would have allowed |
|---|---|
| `Bash` | Running any command on your computer |
| `Write`, `Edit`, `NotebookEdit` | Changing any file on your computer |
| `WebFetch`, `WebSearch` | Reading anything from the internet |
| `Task` | Starting other agents |

None of these are needed. Everything this lab does happens through the robot
arm tools, which are listed in `arm_mcp_server.py` and nowhere else.

**Allowed without asking.** These cannot move anything or change your computer,
so they run straight away:

`listen`, `get_arm_state`, `detect_board`, `write_sketch`, `compile_sketch`,
`show_in_ide`

`write_sketch` only writes inside this folder's `sketches/` directory.

**Always asks you first.** Everything that physically acts:

`move_arm`, `home_arm`, `upload_sketch`, `restore_listener`

That prompt is deliberate. It is not friction to be clicked through, it is the
part of this lab where you are the wizard. Read what the agent wants to do
before you approve it.

To see the live list at any time, type `/permissions` inside Claude Code.

### What leaves your computer

| Stays on your laptop | Sent over the internet |
|---|---|
| Your voice recording | The transcript, as text |
| The Whisper model and everything it does | Your typed messages, if any |
| The sketch files and compiler output | The agent's replies |
| The serial connection to the arm | |

**Your audio never leaves the machine.** Whisper runs locally, which is why it
was a 1.5 GB download. What goes to the model is the text of the transcript,
in the same way it would if you had typed it.

Recordings are kept in `recordings/` so you can compare what you said with what
was heard. Delete that folder whenever you like.

If you would rather not have your voice recorded at all, you can type your
instructions to the agent instead of using `/woz`. Everything else in the lab
works the same way.

## The three levels of feedback, and the one that is missing

This is the most important idea in the lab, so it is worth stating plainly.

| Question | Who answers it | How reliable |
|---|---|---|
| Does the code compile? | `compile_sketch`, from the real compiler | Exact |
| Did it upload to the board? | `upload_sketch` | Exact |
| **Did the arm do the right thing?** | **Nobody** | **Does not exist** |

A sketch can compile without a single warning, upload perfectly, and still make
the arm miss the block, knock it off the table, close the gripper on empty air,
or produce a motion that no human would call waving.

There is no camera, no force sensor, no encoder feedback in this system.

**The only sensor is the person watching the arm.** That is you.

When the agent says something worked, ask yourself what evidence it actually
has. Usually the honest answer is: it compiled.

## The settings: .mcp.json

This small file holds the settings you will change during the experiments.

```bash
cat .mcp.json
```

| Setting | Values | Meaning |
|---|---|---|
| `WOZ_PORT` | `sim`, or a port name | Use the simulator, or a real arm |
| `WOZ_SAFETY` | `on` or `off` | Whether bad commands are blocked |
| `WOZ_FQBN` | a board type | `arduino:avr:mega` for the Mega 2560 |
| `WOZ_WHISPER_MODEL` | `turbo`, `small`, `base` | Which Whisper model the `listen` tool uses |
| `WOZ_LOG` | a file path | Where tool calls are recorded |

If you are not sure which board you have, ask the agent to run `detect_board`.

**After editing this file you must quit Claude Code and start it again.**
Changes are not picked up while it is running.

## Editing the agent's instructions

You are allowed, and encouraged, to edit `CLAUDE.md`. This is prompt
engineering, and it is a legitimate experiment.

A good exercise, once you have run the lab once:

1. Count how many mistakes the agent makes in ten turns
2. Edit `CLAUDE.md` to try to prevent the most common one
3. Run ten more turns and count again
4. Report what you changed and whether it helped

If you break something, the original text of `CLAUDE.md` is in the lab
materials, and `AGENTS.md` is an unchanged copy of it.

**Note:** `CLAUDE.md` is read when Claude Code starts. If you edit it while
Claude Code is running, restart it.

---

# Part C: First run

## Step 1. Check the arm without any AI

```bash
python test_arm.py --sim
```

Type seven numbers and press Enter:

```
20 90 120 90 90 90 30
```

The seven numbers are, in order: speed, base, shoulder, elbow, wrist up/down,
wrist rotation, gripper. These are the same seven values used in `LLM_wk2.ino`
from Lab 1.

Shortcuts also work: `home`, `wave1`, `wave2`, `open`, `close`.

Type `quit` to leave.

**Check:** each command prints a line starting with `OK`.

## Step 2. Start the agent

Three commands, in this order. All three matter.

```bash
cd path/to/the/lab/folder
source venv/bin/activate
claude
```

**Why the order matters.**

*Start it from inside the lab folder.* Claude Code reads three files from whatever
folder it was started in: `.mcp.json` for the robot arm tools, `CLAUDE.md` for
the agent's instructions, and `.claude/commands/woz.md` for the `/woz` command.
Start it anywhere else and none of them exist.

*Activate the virtual environment first.* The arm server is started by Claude
Code, so it inherits the environment you had when you typed `claude`. If the
virtual environment was not active, `whisper` is not on the path and `python3`
is the wrong one, so recording and transcription both fail.

The first time, Claude Code asks whether you trust the tools in this folder.
Answer yes.

Then type:

```
/mcp
```

**Check:** `braccio` appears in the list and is connected. If it is not, see
Part E.

## Step 3. Give it an instruction

Type this into Claude Code:

```
There are two blocks on the table. The red block is on your left,
the blue block is on your right. Please wave hello.
```

Watch what happens, in this order:

1. The agent writes a sentence saying what it intends to do
2. It requests permission to call `move_arm`, showing all seven numbers
3. **You choose whether to allow it**
4. If you allow it, the tool result shows what the arm replied

**Step 3 is the most important moment in this lab.** In the original Wizard of
Oz method, a hidden human decided what the robot did. That permission prompt is
where you are that human. Pay attention to how often you say no, and why.

Try rejecting one command and see how the agent responds.

## Step 4. Make the agent write code

Direct control is not the only mode. Ask the agent to write an actual Arduino
sketch, and to show it to you in the program you already know:

```
Write an Arduino sketch that makes the arm wave hello twice. Open it in
the Arduino IDE so I can watch, then compile it. Do not upload it yet.
```

Watch for:

1. The Arduino IDE opens with the agent's code in it. Leave that window where
   you can see it: the IDE reloads the file every time the agent rewrites it,
   so you see the code change as the agent works
2. `compile_sketch` returns the **real compiler output**
3. If it fails, the agent gets the actual error message and can fix it

Deliberately break it and watch the repair loop:

```
Change the sketch so that it calls a function called moveArmNow() that
does not exist, then compile it again.
```

The compiler will reject it. Watch how the agent reads the error and responds.

Then, if you have a real arm:

```
Upload it and tell me what you expect the arm to do.
```

**Now look at the arm and compare.** The compiler said the code was fine. Was
the movement right? Those are different questions, and only you can answer the
second one.

Afterwards, ask the agent to `restore_listener` so `move_arm` works again.

## Step 5. Run the whole thing by voice

This is the way you will actually run the lab. In Claude Code, type:

```
/woz
```

That is the last thing you type. From then on you only speak.

### The RECORDING window

The first time the agent listens, a second terminal window opens. **Put it
somewhere you can see it, next to the Claude Code window.** It tells you exactly
what is happening, and it is the only place you press anything:

| The window shows | What to do |
|---|---|
| **WAITING**, green | Nothing. The agent is thinking, or the arm is moving |
| **RECORDING**, red | **Speak. Press Enter when you have finished** |
| **WORKING**, yellow | Wait. Whisper is turning your speech into text |
| **HEARD**, blue | Read what it understood, then it goes back to the agent |

Leave that window open for the whole session. Closing it ends recording; the
agent will reopen it next time it needs to listen.

Each round goes like this:

1. The agent says it is listening, and the window turns red
2. **You talk, then press Enter in the RECORDING window**
3. The agent shows you what Whisper heard, exactly as Whisper produced it
4. The agent decides what to do, and asks your permission before acting
5. You approve or reject
6. It goes back to step 1

**Check:** you can complete a full round without touching the keyboard except
to approve.

**Read every transcript.** Comparing what you said with what Whisper heard is
one of the things you are measuring today. The agent acts on the transcript,
mistakes included.

Say "stop" when you are finished.

If Whisper is too slow while setting up, change `WOZ_WHISPER_MODEL` in
`.mcp.json` to `small` and restart Claude Code. Use `turbo` for the real
experiments so everybody's results are comparable.

### If the microphone will not work

`listen.py` still exists as a manual fallback. In a second terminal:

```bash
python listen.py
```

Press Enter, speak, press Enter again. The transcript goes to your clipboard
and you paste it into Claude Code yourself.

---

# Part D: Checking that everything is right

Run this whenever something seems wrong:

```bash
python selftest.py
```

Or check one piece at a time:

| What to check | Command | Expected |
|---|---|---|
| Virtual environment is active | look at your prompt | starts with `(venv)` |
| You are in the right folder | `ls` | you see `CLAUDE.md` |
| Python packages | `python -c "import serial, sounddevice, numpy"` | no error |
| ffmpeg | `ffmpeg -version` | version information |
| Whisper program | `whisper --help` | list of options |
| Whisper model | `ls -lh ~/.cache/whisper/` | a 1.5 GB `.pt` file |
| Claude Code | `claude --version` | a version number |
| Arm server | `python selftest.py` | `0 failed` |
| Agent sees the arm | `/mcp` inside Claude Code | `braccio` connected |

---

# Part E: Common problems

**`command not found: python` or `pip`**

Try `python3` and `pip3` instead. If the virtual environment is active, plain
`python` should work.

**A command worked yesterday and does not work today**

The virtual environment is not active in this terminal window. Run
`source venv/bin/activate` (macOS/Linux) or `venv\Scripts\Activate.ps1`
(Windows).

**`FileNotFoundError: 'ffmpeg'`**

Whisper loaded correctly but cannot find ffmpeg. Go back to Step 3 of Part A.

**`CERTIFICATE_VERIFY_FAILED` when Whisper downloads the model**

The Whisper program is installed. It cannot download the model because
something on the network is inspecting secure traffic and Python does not trust
it. This is common on campus networks.

Try, on macOS:

```bash
open "/Applications/Python 3.11/Install Certificates.command"
```

Or point Python at a current certificate bundle:

```bash
pip install --upgrade certifi
export SSL_CERT_FILE=$(python -m certifi)
```

Or download the model outside Python, which uses the system certificates:

```bash
mkdir -p ~/.cache/whisper
cd ~/.cache/whisper
curl -L -O https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt
```

Easiest of all: ask your instructor for the file on a drive, and follow Step 5
of Part A.

**Whisper produces an empty transcript**

This is a real result, not a bug. Write it down. It is one of the things Layer 4
is asking about.

**Recording does not work, or captures nothing**

Check that your operating system has given the terminal permission to use the
microphone. On macOS: System Settings, Privacy and Security, Microphone, and
switch on the terminal application you started Claude Code from. Then quit the
terminal and open it again.

If it still fails, use the manual fallback. Record with any app, then:

```bash
python listen.py --file yourfile.m4a
```

**I cannot tell when it is recording**

Find the RECORDING window. It is red while the microphone is on and green when
it is not. If you cannot find it, it may be behind another window, or it was
closed. The agent reopens it the next time it listens.

**The RECORDING window did not open**

Open a second terminal yourself and run it by hand:

```bash
cd path/to/the/lab/folder
source venv/bin/activate
python record_window.py
```

The agent will find it and use it.

**The agent seems frozen while I am talking**

That is correct. `listen` waits for you to press Enter in the RECORDING window,
however long that takes. Press Enter there and it will carry on.

**I pressed Enter and nothing happened**

Make sure the RECORDING window is the one in front when you press Enter, not
the Claude Code window.

**`/woz` is not a command**

You started `claude` from a different folder. Quit it, `cd` into the lab folder, and
start it again.

**The `listen` tool fails, or says whisper is missing, even though it works in
the terminal**

You started `claude` without activating the virtual environment first. Claude
Code passes its own environment to the arm server, so `whisper` has to be on
the path at the moment you type `claude`. Quit, then:

```bash
source venv/bin/activate
claude
```

**Claude Code asks me to log in, or says it is not authenticated**

That is expected on a computer where it has never been used. See Signing in at
the end of Part A, Step 7. Ask your instructor whether this class uses a Claude
account or an API key.

**`braccio` does not appear under `/mcp`**

Three usual causes:

1. You started `claude` from a different folder. Quit, `cd` into the lab folder, start
   again
2. `python3` is not on your system PATH. Test with `python3 --version`
3. The server has an error. See it directly with:

```bash
python3 arm_mcp_server.py
```

It should sit still and print two lines about the backend and the safety
setting. Press Ctrl+C to stop it. Any real error appears at once.

**Changes to `.mcp.json` or `CLAUDE.md` have no effect**

Quit Claude Code and start it again. Both files are read at startup.

**`move_arm` says the board is running a sketch**

You uploaded code the agent wrote, which replaced the firmware that listens for
movement commands. Ask the agent to call `restore_listener`.

**The agent says arduino-cli was not found**

Install the Arduino IDE version 2 from https://www.arduino.cc/en/software. It
includes the copy this lab needs, and the lab finds it on its own.

If the IDE is already installed in an unusual location, put the full path to
its bundled `arduino-cli` into `WOZ_ARDUINO_CLI` in `.mcp.json` and restart
Claude Code.

**Compiling fails with `Braccio.h: No such file or directory`**

Install the Braccio library from the Arduino IDE Library Manager. `selftest.py`
also prints an exact command you can run instead.

**Compiling fails with `platform not installed`**

Install Arduino AVR Boards from the Arduino IDE Boards Manager.

**Uploading fails with a port error**

Close anything else that is using the serial port: the Arduino IDE serial
monitor, `test_arm.py`, or another copy of Claude Code. Only one program can use
the port at a time.

**The agent moved the arm to the wrong place**

That is not a bug. That is data. Record it.

---

# Quick reference

Every session starts with these three lines, in this order:

```bash
cd path/to/the/lab/folder
source venv/bin/activate
claude
```

Then type `/woz` and start talking.

| Command | What it does |
|---|---|
| `python selftest.py` | Check that everything works |
| `python test_arm.py --sim` | Drive the arm by hand, no AI |
| `arduino-cli board list` | See which board is plugged in |
| `claude` | Start the agent |
| `/woz` (inside Claude Code) | **Start the hands-free session. Then just talk** |
| `/mcp` (inside Claude Code) | Check the agent can reach the arm |
| `/status` (inside Claude Code) | Check which account or key is being used |
| `python listen.py` | Manual fallback: record and transcribe |
| `python listen.py --model small` | Same, but faster and less accurate |
| `python listen.py --keep` | Same, but keeps the audio files |
| `python listen.py --file x.m4a` | Transcribe a file you already have |
| `/export` (inside Claude Code) | Save the conversation for your report |

The seven numbers, in order:

```
step_delay  base  shoulder  elbow  wrist_ver  wrist_rot  gripper
   10-30    0-180  15-165   0-180    0-180      0-180    10-73
```

Gripper: 10 is fully open, 73 is fully closed.
