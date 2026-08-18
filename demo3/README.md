# Agentic Wizard of Oz

**ROB 340: Human Evaluation of Robots** - Lab 5, Part 1.2 (extension)

In the classic Wizard of Oz method, a hidden human operates the robot while the
participant believes it is acting on its own. In this lab that hidden human is
replaced by an LLM agent, and every part of the substitution is put where you
can see it.

**You speak. The agent listens, decides what the robot arm should do, writes and
compiles Arduino code when the task needs it, asks your permission, and moves
the arm.** You watch all of it and decide whether it was right.

---

## Getting the files

### If you were given a folder or a zip file

Put it wherever you keep coursework and skip to **Setting up** below.

### If you were given a repository link

You need `git`. On macOS it arrives with the Xcode command line tools; if
`git --version` fails, run `xcode-select --install` first.

```bash
cd ~/Documents
git clone <the repository link your instructor gave you>
cd <the folder it created>
```

### If you would rather not use git

On the repository page, click the green **Code** button, choose **Download
ZIP**, and unzip it. Everything is in the folder that appears.

### Check you are in the right place

```bash
ls
```

You should see `SETUP.md`, `CLAUDE.md`, `arm_mcp_server.py` and
`requirements.txt`. **Every command in this lab is run from this folder.** If
you see a folder name instead of those files, go one level deeper.

---

## Setting up

**Read [`SETUP.md`](SETUP.md) and follow it from top to bottom.** It has a check
after each step, so you always know whether to continue or fix something first.

The short version of what you are installing:

| What | Why |
|---|---|
| Python packages | Talking to the arm, recording your voice |
| ffmpeg | Whisper needs it to read audio |
| Whisper and its model | Turning your speech into text, entirely on your laptop |
| Node.js and Claude Code | The agent itself |
| Arduino IDE | Compiling and uploading code to the arm |

**Budget about 40 minutes the first time**, most of it waiting for downloads. If
your instructor has already prepared the computer you are using, you can skip
most of it.

Two things catch people out, so they are worth saying twice:

- Installing the agent is **not** the same as signing in. The first time you run
  it, it asks you to log in
- Installing Whisper is **not** the same as downloading the Whisper model. The
  model is a separate 1.5 GB file

Both are covered in `SETUP.md`.

---

## Running it

Two commands and one more, in a terminal opened in this folder:

```bash
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
claude
```

Then, inside the agent:

```
/woz
```

**That is the last thing you type.** After that you only speak.

A second window opens and shows what the microphone is doing:

| The window shows | What to do |
|---|---|
| **WAITING**, green | Nothing. The agent is thinking, or the arm is moving |
| **RECORDING**, red | **Speak, then press Enter in that window** |
| **WORKING**, yellow | Wait. Whisper is turning your speech into text |
| **HEARD**, blue | Read what it understood before it reaches the agent |

Say "stop" when you are finished.

You do not need a robot arm to try this. Everything runs against a built-in
simulator until somebody changes one setting.

---

## What to look at while you work

**Open `CLAUDE.md` and read it.** That file *is* the agent's instructions. In a
normal chat application those instructions are hidden from you; here they are a
short text file you can read, argue with, and edit. Everything the agent
believes about this robot comes from that file and from what you tell it.

**Watch the permission prompt.** When the agent wants to move the arm, it stops
and asks you. In the original Wizard of Oz method a hidden human decided what
the robot did. That prompt is where you are that human. Notice how often you say
no, and why.

**Do not trust "it compiled".** The compiler tells you the code is valid. It
cannot tell you the arm did the right thing, because there is no camera and no
force sensor anywhere in this system. Code can compile cleanly, upload
perfectly, and still miss the block completely. **You are the only sensor.**

---

## What the agent is allowed to do

`.claude/settings.json` is short, and you should open it.

| | Tools |
|---|---|
| **Denied outright** | Running shell commands, editing files, reading the internet |
| **Allowed silently** | Listening, reading the arm's last position, writing and compiling a sketch |
| **Always asks you first** | Every action that physically moves the arm |

The agent cannot run a command on your computer, cannot touch a file outside
this folder's `sketches/` directory, and cannot reach the network. It is not
being trusted not to; it is not able to.

**Your voice stays on your laptop.** Whisper runs locally, which is why the
model is a 1.5 GB download. What travels over the network is the transcript
text, exactly as it would if you had typed it. If you would rather not be
recorded at all, you can type to the agent instead and every part of the lab
except the speech section works the same way.

---

## If something goes wrong

`SETUP.md` ends with a troubleshooting section covering the problems people
actually hit: certificate errors when downloading the Whisper model, missing
ffmpeg, the agent not finding the arm, and microphone permissions.

Before asking for help, run:

```bash
python selftest.py
```

It checks every part of the setup and prints exactly what is missing and how to
fix it.

---

## Files

| File | What it does |
|---|---|
| `SETUP.md` | The step by step setup guide. Start here |
| `CLAUDE.md` / `AGENTS.md` | The agent's instructions. Read these |
| `.claude/settings.json` | What the agent may and may not do |
| `.claude/commands/woz.md` | The `/woz` command |
| `.mcp.json` | Settings: simulator or real arm, safety check on or off |
| `arm_mcp_server.py` | The tools the agent can use. Readable, and worth reading |
| `record_window.py` | The RECORDING window |
| `voice.py` | Connects the agent to that window |
| `ide_tools.py` | Opens a sketch in the Arduino IDE |
| `selftest.py` | Checks your setup |
| `test_arm.py` | Drive the arm by typing numbers, with no agent involved |
| `arm.py` | Serial connection and the simulator |
| `listen.py` | Record and transcribe by hand, if the automatic version fails |
| `firmware/braccio_listener/` | Uploaded to the Arduino once during setup |

---

## Hardware

- Arduino Braccio robot arm
- Arduino Mega 2560 with the Braccio shield
- A laptop with a microphone

The simulator covers everything except the arm actually moving, so you can do
the whole setup and most of the experiment before you touch hardware.
