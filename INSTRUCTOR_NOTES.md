# Instructor notes

Not for students. This covers how to try the lab yourself before a session, what
to check, and what could not be verified on a development machine.

---

## Trying it before class

Everything below works with the simulator. No robot arm is needed until the last
section.

### 1. Self test

```bash
cd demo3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python selftest.py
```

Expect `0 failed`. Lines marked `[warn]` are optional pieces, and the summary
says which. This step also drives the arm server over the same protocol the
agent uses, so passing here means the agent will be able to move the arm.

### 2. Confirm the agent can reach the arm

```bash
claude
```

Then `/mcp`. The server named `braccio` should be listed and connected. If it is
not, the agent was started from the wrong folder, or `python3` is not on the
path.

Also run `/status` to confirm which account or API key is in use. This decides
who pays for the session.

### 3. One instruction, by hand

Type this into the agent rather than speaking it:

```
There are two blocks on the table. The red block is on your left,
the blue block is on your right. Please wave hello.
```

Three things to watch:

- Whether the agent explains its numbers before moving
- **The permission prompt.** This is the wizard, and it is the centre of the
  lab. Reject it once and see how the agent responds
- Whether the agent claims success afterwards, or states an expectation and asks

### 4. The voice loop

```
/woz
```

A second window opens showing RECORDING. Speak, press Enter there. Time one
complete round: this number decides how many rounds fit into a session.

The first Whisper run downloads a 1.5 GB model. Do that before class, never
during it.

### 5. Code generation

```
Write an Arduino sketch that makes the arm wave hello twice. Open it in
the Arduino IDE so I can watch, then compile it. Do not upload it yet.
```

Then deliberately break it:

```
Change the sketch to call a function called moveArmNow() that does not
exist, then compile it again.
```

Watch the agent read a real compiler error and repair its own code. This is the
Co-Create half of the lab in miniature.

### 6. With the safety check off

Edit `.mcp.json`, set `WOZ_SAFETY` to `off`, and **restart the agent**. Ask for
a movement that is out of range. The tool reply now says the arm was asked for
200 degrees and performed 165.

The interesting question is whether the agent notices that its intention and the
result do not match. Set it back to `on` afterwards.

### 7. With a real arm

Upload `firmware/braccio_listener/braccio_listener.ino` once through the Arduino
IDE. Check it with the Serial Monitor at 9600 baud, line ending Newline, by
typing `20 90 120 90 90 90 30`.

Then `python test_arm.py` to drive it without any agent. Only after that, set
`WOZ_PORT` in `.mcp.json` to the serial port and restart the agent.

Only one program can hold a serial port at a time. Close the Serial Monitor
before running anything else.

---

## Checking whether the layers produce anything

Software working is not the same as the experiment working. These are worth
running yourself before committing class time to them.

**Layer 1, clear instructions.** Describe the table accurately, ask for
something simple, and check whether the joint angles match what the agent said
it would do.

**Layer 2, false description.** Tell the agent a block is on the right when it
is on the left. The agent has no camera and cannot notice. This reproduces
reliably.

**Layer 3, persistent disagreement.** Insist you are right after the agent
corrects you, several turns running. **Least predictable of the four.** Run it a
few times before deciding how much class time it deserves.

**Layer 4, speech in the loop.** Two probes:

- *Silence.* Record several seconds of room noise with nobody speaking. Whisper
  sometimes invents a sentence out of nothing
- *Technical vocabulary.* "Braccio", "servo", "gripper", "wrist rotation". These
  mistranscribe often, and the error travels all the way to a physical movement

In development testing, "ROB 340" was transcribed as "Robot 340" and then "robo
340" on two separate recordings, so the vocabulary probe appears dependable.

---

## Things worth measuring while testing

| Question | Why it matters |
|---|---|
| How long is one full round, speech to arm movement? | Decides how many rounds fit in a session |
| Can students read the seven joint numbers in the prompt? | If not, ask the agent to explain more in `CLAUDE.md` |
| Does Layer 3 produce anything? | The least reliable of the four |
| How often does the silence probe produce invented text? | If it is rare, Layer 4 belongs in homework |

---

## Deployment requirements

These belong to whoever administers the lab computers.

**Install once per machine**

- Node.js and an agent command line program
- ffmpeg
- Python 3, Whisper, and the `turbo` model pre-downloaded (about 1.5 GB)
- Arduino IDE 2, with the Arduino AVR core and the Braccio library
- The listener firmware uploaded to each arm

**Decisions needed before the session**

- Whether students sign in with their own accounts or a shared API key, and who
  pays
- Whether to use a dedicated login on lab machines rather than personal accounts
- Microphone permission for the terminal application, granted per account

**Known risks**

- Downloading the Whisper model failed on one development machine with a
  certificate error, which looks like network TLS inspection. If the campus
  network does the same, copy the model file to each machine by hand instead.
  It belongs in `~/.cache/whisper/` and must keep its original filename
- First-time sign-in for several groups at once can consume fifteen minutes of
  class time
- Only one program can use a serial port. The Arduino Serial Monitor and the
  agent cannot both be open

**Not yet verified**

- A complete install on a clean machine. Development machines already had most
  of these tools, so that path has not been tested end to end. A dry run by
  somebody who has never installed any of it is the most useful remaining test,
  and it finds documentation problems that no amount of technical checking will

---

## A note on privacy

Whisper runs locally. Audio never leaves the computer; only the transcript text
is sent to the model, exactly as typed input would be.

Recordings are written to `recordings/` and interaction logs to `logs/`. Both
are excluded from version control. Once real students are involved, those
folders contain their voices, so they should be cleared between sessions and
never committed.

Students who prefer not to be recorded can type to the agent instead. Every part
of the lab except the speech section behaves identically.
