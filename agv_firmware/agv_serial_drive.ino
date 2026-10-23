/*
 * AGV skid-steer serial drive — ESP32-WROOM
 * Arduino IDE: Board = "ESP32 Dev Module"
 *
 * Pin map matches agv_pcb schematic (2x L298N, 4 DC motors).
 *   L298N A (front axle): M1=FL, M2=FR
 *   L298N B (rear axle):  M3=RL, M4=RR
 *
 * Skid-steer mapping:
 *   left_pwm  -> M1 (FL) + M3 (RL)
 *   right_pwm -> M2 (FR) + M4 (RR)
 *
 * Serial protocol (115200 8N1, newline-terminated):
 *   V <left_pwm> <right_pwm>   signed ints -255..255
 *   S                          stop all motors
 *
 * Stops automatically if no command for COMMAND_TIMEOUT_MS.
 * If a motor runs backward, swap that motor's two wires on the L298N.
 */

// ----- L298N A → M1 (OUT1/OUT2), M2 (OUT3/OUT4) -----
static const int ENA_A = 25;
static const int IN1_A = 26;
static const int IN2_A = 27;
static const int IN3_A = 14;
static const int IN4_A = 12;  // strapping pin — fine after boot
static const int ENB_A = 13;

// ----- L298N B → M3 (OUT1/OUT2), M4 (OUT3/OUT4) -----
static const int ENA_B = 33;
static const int IN1_B = 32;
static const int IN2_B = 23;
static const int IN3_B = 22;
static const int IN4_B = 21;
static const int ENB_B = 19;

static const unsigned long COMMAND_TIMEOUT_MS = 300;
static const size_t LINE_BUF_SIZE = 64;

String lineBuf;
unsigned long lastCmdMs = 0;
bool motorsActive = false;

void setupMotorPins() {
  const int pins[] = {
    ENA_A, IN1_A, IN2_A, IN3_A, IN4_A, ENB_A,
    ENA_B, IN1_B, IN2_B, IN3_B, IN4_B, ENB_B
  };
  for (int p : pins) {
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
  }
}

void setMotor(int in1, int in2, int en, int pwm) {
  int mag = abs(pwm);
  if (mag > 255) mag = 255;
  if (mag == 0) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
    analogWrite(en, 0);
    return;
  }
  if (pwm > 0) {
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
  } else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
  }
  analogWrite(en, mag);
}

void allStop() {
  analogWrite(ENA_A, 0);
  analogWrite(ENB_A, 0);
  analogWrite(ENA_B, 0);
  analogWrite(ENB_B, 0);
  digitalWrite(IN1_A, LOW);
  digitalWrite(IN2_A, LOW);
  digitalWrite(IN3_A, LOW);
  digitalWrite(IN4_A, LOW);
  digitalWrite(IN1_B, LOW);
  digitalWrite(IN2_B, LOW);
  digitalWrite(IN3_B, LOW);
  digitalWrite(IN4_B, LOW);
  motorsActive = false;
}

void setSkidSteer(int leftPwm, int rightPwm) {
  // Left side: FL (M1) + RL (M3)
  setMotor(IN1_A, IN2_A, ENA_A, leftPwm);   // M1 FL
  setMotor(IN1_B, IN2_B, ENA_B, leftPwm);   // M3 RL
  // Right side: FR (M2) + RR (M4)
  setMotor(IN3_A, IN4_A, ENB_A, rightPwm);  // M2 FR
  setMotor(IN3_B, IN4_B, ENB_B, rightPwm);  // M4 RR
  motorsActive = (leftPwm != 0 || rightPwm != 0);
  lastCmdMs = millis();
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line.charAt(0) == 'S' || line.charAt(0) == 's') {
    allStop();
    lastCmdMs = millis();
    Serial.println("OK STOP");
    return;
  }

  if (line.charAt(0) == 'V' || line.charAt(0) == 'v') {
    int leftPwm = 0;
    int rightPwm = 0;
    // Skip leading 'V' and whitespace
    int n = sscanf(line.c_str() + 1, "%d %d", &leftPwm, &rightPwm);
    if (n == 2) {
      if (leftPwm > 255) leftPwm = 255;
      if (leftPwm < -255) leftPwm = -255;
      if (rightPwm > 255) rightPwm = 255;
      if (rightPwm < -255) rightPwm = -255;
      setSkidSteer(leftPwm, rightPwm);
      Serial.print("OK V ");
      Serial.print(leftPwm);
      Serial.print(' ');
      Serial.println(rightPwm);
    } else {
      Serial.println("ERR V usage: V <left> <right>");
    }
    return;
  }

  Serial.println("ERR unknown cmd");
}

void setup() {
  Serial.begin(115200);
  delay(200);
  setupMotorPins();
  allStop();
  lastCmdMs = millis();
  Serial.println("AGV serial drive ready (V left right | S)");
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (lineBuf.length() > 0) {
        handleLine(lineBuf);
        lineBuf = "";
      }
    } else {
      if (lineBuf.length() < LINE_BUF_SIZE - 1) {
        lineBuf += c;
      }
    }
  }

  if (motorsActive && (millis() - lastCmdMs > COMMAND_TIMEOUT_MS)) {
    allStop();
    Serial.println("OK TIMEOUT STOP");
  }
}
