# Agentic Wizard of Oz Experiment demo

**ROB 340: Human Evaluation of Robots** 

-The hidden human is replaced by an LLM agent.


## Setup

**[Installation and Setup](SETUP.md)** - follow it from top to bottom.


## Running it

In the lab folder:

```bash
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
claude
```

Then, inside Claude Code:

```
/woz
```
**A second window will open and show what the microphone is doing:

| The window shows | What to do |
|---|---|
| **WAITING**, green | Nothing |
| **RECORDING**, red | Speak, then press Enter in that window |
| **WORKING**, yellow | Wait |
| **HEARD**, blue | Read what it understood |

Approve or reject each movement in the Claude Code window. Say "stop" to finish.

## Files

| File | What it does |
|---|---|
| `SETUP.md` | Installation and setup. Start here |
| `CLAUDE.md` / `AGENTS.md` | The agent's instructions |
| `.mcp.json` | Settings: simulator or real arm, safety check on or off |
| `.claude/settings.json` | What the agent is allowed to do |
| `.claude/commands/woz.md` | The `/woz` command |
| `arm_mcp_server.py` | The tools the agent can use |
| `record_window.py` | The recording window |
| `voice.py` | Connects the agent to the recording window |
| `ide_tools.py` | Opens a sketch in the Arduino IDE |
| `selftest.py` | Checks the setup |
| `test_arm.py` | Drive the arm by typing numbers, with no agent |
| `arm.py` | Serial connection and simulator |
| `listen.py` | Record and transcribe by hand |
| `firmware/braccio_listener/` | Uploaded to the Arduino once during setup |

## Hardware

- Arduino Braccio robot arm
- Arduino Mega 2560 with the Braccio shield
- A laptop with a microphone
