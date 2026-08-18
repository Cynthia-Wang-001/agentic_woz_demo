# Agentic Wizard of Oz

**ROB 340: Human Evaluation of Robots** - an extension to the Wizard of Oz lab
(Lab 5, Part 1.2).

In the classic Wizard of Oz method, a hidden human operates the robot while the
participant believes it is acting on its own. This project replaces that hidden
human with an LLM agent, and then makes every part of the substitution visible
and testable.

A student speaks. The agent hears them, decides what the robot arm should do,
writes and compiles Arduino code when the task needs it, asks permission, and
moves the arm. The student watches all of it happen and decides whether it was
right.

---

## What to download

**[`demo3/`](demo3/) is the version to use.** It is self contained: clone the
repository, open `demo3/README.md`, and follow it.

```bash
git clone <this repository>
cd demo3
```

| Folder | What it is |
|---|---|
| **`demo3/`** | **The release version. Start here.** |
| `demo1/` | Simpler variant: the student pastes the transcript in by hand |
| `demo2/` | Working copy of the release version |
| `archive/` | The first prototype, kept for reference. Not used |

`demo1` exists as a fallback. If a computer will not give the microphone to the
agent, or the extra window causes trouble, `demo1` runs the same experiment with
the student copying the transcript across manually.

---

## How it works

Setup happens once per computer: the Arduino gets a small piece of firmware that
listens on the serial port, and the laptop gets Whisper and an agent command
line program. After that a session looks like this.

```
Student types /woz once, then only speaks
   |
   +-- 1. The agent calls listen
   |        A second window turns red and shows RECORDING
   |        The student speaks and presses Enter
   |        Whisper transcribes it locally and hands back the raw text
   |
   +-- 2. The agent decides what the instruction needs
   |
   |      Single movement:
   |        move_arm  ->  [permission prompt]  ->  serial port  ->  the arm moves
   |
   |      A sequence that runs on the board:
   |        write_sketch   ->  saves an .ino file
   |        show_in_ide    ->  the code appears in the Arduino IDE
   |        compile_sketch ->  real compiler output comes back
   |            failed?    ->  the agent reads the errors and fixes its own code
   |        upload_sketch  ->  [permission prompt]  ->  the board runs it
   |
   +-- 3. The agent says what it expected to happen. It does not claim success
   |
   +-- 4. Back to step 1
```

The agent never runs shell commands. It calls tools, and a small local server
runs the compiler on its behalf and hands back the output unchanged.

---

## Three design decisions worth knowing about

**The agent works in its own interface.** There is no custom app. The agent's
instructions are `CLAUDE.md`, a short text file students are told to open, read
and edit. The tools it can use are listed in one readable Python file. Students
see the real thing rather than a summary of it.

**The permission prompt is the wizard.** When the agent wants to move the arm,
the agent program stops and asks a human to approve it. That prompt is where the
student occupies the role the hidden operator used to occupy, and it can be
switched off to see what changes. Everything the agent does not need is denied
outright: it cannot run shell commands, edit files outside its own sketch
folder, or reach the network.

**Compiling is not succeeding.** The compiler reports whether the code is valid.
Nothing in the system reports whether the arm did the right thing, because there
is no camera and no force feedback. A sketch can compile cleanly, upload
perfectly, and still miss the block entirely. The only sensor is the student
watching, and the lab is built to make that gap obvious.

---

## Hardware

- Arduino Braccio robot arm
- Arduino Mega 2560 with the Braccio shield
- A laptop with a microphone

Every part of the software runs against a built-in simulator as well, so groups
waiting for the arm can still write, compile and test everything else.
