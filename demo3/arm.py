"""
arm.py - talks to the Braccio arm over the serial port.

Two interchangeable backends:

    SerialArm     sends commands to a real Braccio arm
    SimulatedArm  pretends to be an arm, so groups can work without hardware

Both expose the same two methods: send(command) and describe_pose().

A command is a list of 7 integers:
    [step_delay, base, shoulder, elbow, wrist_ver, wrist_rot, gripper]
"""

import time

try:
    import serial
    from serial.tools import list_ports
    PYSERIAL_AVAILABLE = True
except ImportError:  # pragma: no cover - only hit when pyserial is missing
    PYSERIAL_AVAILABLE = False


# Joint ranges accepted by the Braccio library. The library clamps anything
# outside these ranges, so these numbers are informational for the agent and
# for the software safety check.
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
    "step_delay",
    "base",
    "shoulder",
    "elbow",
    "wrist_ver",
    "wrist_rot",
    "gripper",
]

HOME_POSE = [20, 90, 90, 90, 90, 90, 40]


def format_command(values):
    """Turns [20, 90, 120, 90, 90, 90, 30] into the string '20 90 120 90 90 90 30'."""
    return " ".join(str(int(v)) for v in values)


def available_ports():
    """Returns a list of serial port names that might be the Arduino."""
    if not PYSERIAL_AVAILABLE:
        return []
    return [p.device for p in list_ports.comports()]


def guess_port():
    """Best guess at which serial port the Arduino is on. None if unsure."""
    for name in available_ports():
        lowered = name.lower()
        if "usbmodem" in lowered or "usbserial" in lowered:
            return name
        if "ttyacm" in lowered or "ttyusb" in lowered:
            return name
        if lowered.startswith("com"):
            return name
    return None


class SimulatedArm:
    """
    A stand-in for the real arm.

    Use this when no hardware is plugged in, or when several groups need to
    work on the agent at the same time and only one physical arm is free.
    Everything else in the program behaves identically.
    """

    backend_name = "Simulator"

    def __init__(self):
        self.pose = list(HOME_POSE)
        self.connected = True

    def send(self, values):
        self.pose = [int(v) for v in values]
        # Pretend the motion takes a moment, so the pacing feels realistic.
        time.sleep(0.3)
        return "OK " + format_command(self.pose) + "  (simulated)"

    def describe_pose(self):
        return dict(zip(JOINT_ORDER, self.pose))

    def close(self):
        self.connected = False


class SerialArm:
    """Sends commands to a real Braccio arm running braccio_listener.ino."""

    backend_name = "Serial"

    def __init__(self, port, baudrate=9600, timeout=5.0):
        if not PYSERIAL_AVAILABLE:
            raise RuntimeError("pyserial is not installed. Run: pip install pyserial")

        self.port = port
        self.pose = list(HOME_POSE)
        self.link = serial.Serial(port, baudrate, timeout=timeout)

        # Opening the serial port resets the Arduino board. Wait for it to
        # finish booting, otherwise the first few commands are silently lost.
        time.sleep(2.0)
        self.link.reset_input_buffer()

        self.connected = True

    def send(self, values):
        command = format_command(values)
        self.link.write((command + "\n").encode("ascii"))
        self.link.flush()

        # The arm replies once the movement has finished.
        reply = self.link.readline().decode("ascii", errors="replace").strip()
        if reply.startswith("OK"):
            self.pose = [int(v) for v in values]
        if not reply:
            reply = "(no reply from arm - check the cable and the baud rate)"
        return reply

    def describe_pose(self):
        return dict(zip(JOINT_ORDER, self.pose))

    def close(self):
        try:
            self.link.close()
        finally:
            self.connected = False


def connect(port=None):
    """
    Returns a SerialArm if a port is given and can be opened,
    otherwise falls back to the SimulatedArm.
    """
    if port and port != "Simulator":
        return SerialArm(port)
    return SimulatedArm()
