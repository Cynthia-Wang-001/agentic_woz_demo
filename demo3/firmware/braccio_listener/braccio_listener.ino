/*
 * braccio_listener.ino
 * ROB340 - Agentic Wizard of Oz Lab
 *
 * Upload this sketch to the Arduino ONCE. After that you never need to
 * open the Arduino IDE again for the rest of the lab.
 *
 * The sketch waits for a line of text on the serial port and executes it.
 *
 * COMMAND FORMAT
 * --------------
 * Seven integers separated by spaces, ending with a newline:
 *
 *     <stepDelay> <base> <shoulder> <elbow> <wrist_ver> <wrist_rot> <gripper>
 *
 * Example:
 *
 *     20 90 120 90 90 90 30
 *
 * These are exactly the seven arguments of Braccio.ServoMovement() used in
 * LLM_wk2.ino, in the same order. Nothing new to learn.
 *
 * The sketch replies with one of:
 *     READY               sent once at startup
 *     OK <the command>    command was parsed and executed
 *     ERR <reason>        command could not be parsed
 *
 * NOTE ON JOINT LIMITS
 * --------------------
 * The Braccio library clamps out-of-range angles internally, so a bad angle
 * cannot damage the arm. This is the "hard" safety layer. It is always on and
 * students cannot switch it off. The "software safety check" that students can
 * toggle lives in the Python program, not here.
 *
 * You can test this sketch on its own with the Arduino Serial Monitor:
 * set the line ending to "Newline", the baud rate to 9600, then type
 * a command such as "20 90 120 90 90 90 30" and press Enter.
 */

#include <Servo.h>
#include <Braccio.h>

Servo base;
Servo shoulder;
Servo elbow;
Servo wrist_ver;
Servo wrist_rot;
Servo gripper;

// Home / safe pose used at startup and by the "home" command.
const int HOME[7] = {20, 90, 90, 90, 90, 90, 40};

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(200);

  // Braccio.begin() powers the servos and moves the arm to its safety
  // position. Keep hands clear of the arm when the board resets.
  Braccio.begin();

  Serial.println("READY");
}

void loop() {
  if (Serial.available() <= 0) {
    return;
  }

  String line = Serial.readStringUntil('\n');
  line.trim();

  if (line.length() == 0) {
    return;
  }

  // "home" is a convenience command so the arm can always be reset by hand.
  if (line.equalsIgnoreCase("home")) {
    Braccio.ServoMovement(HOME[0], HOME[1], HOME[2], HOME[3],
                          HOME[4], HOME[5], HOME[6]);
    Serial.println("OK home");
    return;
  }

  int values[7];
  int count = parseSevenInts(line, values);

  if (count != 7) {
    Serial.print("ERR expected 7 integers, got ");
    Serial.println(count);
    return;
  }

  Braccio.ServoMovement(values[0], values[1], values[2], values[3],
                        values[4], values[5], values[6]);

  Serial.print("OK ");
  Serial.println(line);
}

/*
 * Splits a whitespace separated line into at most 7 integers.
 * Returns how many integers were found.
 */
int parseSevenInts(const String &line, int *out) {
  int count = 0;
  int i = 0;
  int len = line.length();

  while (i < len && count < 7) {
    // Skip any whitespace before the next number.
    while (i < len && line.charAt(i) == ' ') {
      i++;
    }
    if (i >= len) {
      break;
    }

    int start = i;
    if (line.charAt(i) == '-') {
      i++;
    }
    while (i < len && isDigit(line.charAt(i))) {
      i++;
    }

    // If we did not consume at least one digit, the line is malformed.
    if (i == start || (i == start + 1 && line.charAt(start) == '-')) {
      return -1;
    }

    out[count] = line.substring(start, i).toInt();
    count++;
  }

  return count;
}
