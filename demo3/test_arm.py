"""
test_arm.py - step 1 of setting up the lab.

Run this BEFORE touching any of the LLM code. It lets you drive the arm by
typing the seven numbers yourself. If this works, the hardware half of the
lab is finished and everything after it is pure software.

Usage:
    python test_arm.py                 pick a port automatically
    python test_arm.py /dev/ttyACM0    use a specific port
    python test_arm.py --sim           no hardware, simulator only
"""

import sys

import arm as arm_module


DEMO_POSES = {
    "home":  [20, 90, 90, 90, 90, 90, 40],
    "wave1": [20, 90, 120, 90, 60, 90, 30],
    "wave2": [20, 90, 120, 90, 120, 90, 30],
    "open":  [20, 90, 90, 90, 90, 90, 10],
    "close": [20, 90, 90, 90, 90, 90, 73],
}


def main():
    args = sys.argv[1:]

    if "--sim" in args:
        robot = arm_module.SimulatedArm()
    else:
        port = args[0] if args else arm_module.guess_port()
        if port is None:
            print("No serial port found. Ports visible on this computer:")
            for name in arm_module.available_ports():
                print("   ", name)
            print("\nPlug in the Arduino, or run with --sim to use the simulator.")
            return
        print("Connecting to %s ..." % port)
        robot = arm_module.SerialArm(port)
        print("Connected.")

    print("\nBackend: %s" % robot.backend_name)
    print("Type seven numbers, for example:  20 90 120 90 90 90 30")
    print("Shortcuts: %s" % ", ".join(DEMO_POSES))
    print("Type 'quit' to exit.\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue
        if line.lower() in ("quit", "exit"):
            break

        if line.lower() in DEMO_POSES:
            values = DEMO_POSES[line.lower()]
        else:
            parts = line.split()
            if len(parts) != 7:
                print("   Expected 7 numbers, got %d." % len(parts))
                continue
            try:
                values = [int(p) for p in parts]
            except ValueError:
                print("   All seven values must be whole numbers.")
                continue

        reply = robot.send(values)
        print("   arm: %s" % reply)

    robot.close()
    print("Closed.")


if __name__ == "__main__":
    main()
