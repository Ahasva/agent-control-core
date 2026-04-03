#include <Servo.h>

Servo machineServo;

// Pin mapping
const int PIN_LED_BLUE   = 2;
const int PIN_LED_GREEN  = 3;
const int PIN_LED_YELLOW = 4;
const int PIN_LED_RED    = 5;
const int PIN_BUZZER     = 6;
const int PIN_SERVO      = 9;
const int PIN_BTN_A      = 10; // approval
const int PIN_BTN_B      = 11; // reset / acknowledge
const int PIN_POT        = A0;

// Local machine state mirrored on Arduino
String machineState = "OFF";
bool machineEnabled = false;
bool faultActive = false;
bool lockActive = false;
int servoAngle = 90;

unsigned long lastStatusMs = 0;
unsigned long lastDebounceA = 0;
unsigned long lastDebounceB = 0;
int lastBtnAStable = HIGH;
int lastBtnBStable = HIGH;

void setAllStateLeds(bool blue, bool green, bool yellow, bool red) {
  digitalWrite(PIN_LED_BLUE, blue ? HIGH : LOW);
  digitalWrite(PIN_LED_GREEN, green ? HIGH : LOW);
  digitalWrite(PIN_LED_YELLOW, yellow ? HIGH : LOW);
  digitalWrite(PIN_LED_RED, red ? HIGH : LOW);
}

void updateStateIndicators() {
  if (faultActive) {
    setAllStateLeds(false, false, false, true);
    return;
  }

  if (lockActive) {
    setAllStateLeds(false, false, true, true);
    return;
  }

  if (machineState == "OFF") {
    setAllStateLeds(false, false, false, false);
    return;
  }

  if (machineState == "IDLE") {
    setAllStateLeds(true, false, false, false);
    return;
  }

  if (machineState == "READY") {
    setAllStateLeds(true, true, false, false);
    return;
  }

  if (machineState == "CALIBRATION") {
    setAllStateLeds(true, false, true, false);
    return;
  }

  if (machineState == "ACTIVE") {
    setAllStateLeds(true, true, true, false);
    return;
  }

  if (machineState == "FAULT") {
    setAllStateLeds(false, false, false, true);
    return;
  }

  if (machineState == "LOCKED") {
    setAllStateLeds(false, false, true, true);
    return;
  }
}

void beepShort(int durationMs = 80) {
  digitalWrite(PIN_BUZZER, HIGH);
  delay(durationMs);
  digitalWrite(PIN_BUZZER, LOW);
}

void beepAlert() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(100);
    digitalWrite(PIN_BUZZER, LOW);
    delay(80);
  }
}

void sendAck(const String& msg) {
  Serial.print("ACK ");
  Serial.println(msg);
}

void sendStatus() {
  int potRaw = analogRead(PIN_POT);
  int btnA = digitalRead(PIN_BTN_A) == LOW ? 1 : 0; // INPUT_PULLUP => pressed = LOW
  int btnB = digitalRead(PIN_BTN_B) == LOW ? 1 : 0;

  Serial.print("STATE=");
  Serial.print(machineState);
  Serial.print(" ENABLED=");
  Serial.print(machineEnabled ? 1 : 0);
  Serial.print(" FAULT=");
  Serial.print(faultActive ? 1 : 0);
  Serial.print(" LOCK=");
  Serial.print(lockActive ? 1 : 0);
  Serial.print(" SERVO=");
  Serial.print(servoAngle);
  Serial.print(" POT=");
  Serial.print(potRaw);
  Serial.print(" BTN_A=");
  Serial.print(btnA);
  Serial.print(" BTN_B=");
  Serial.println(btnB);
}

void handleEnableMachine() {
  machineEnabled = true;
  machineState = "IDLE";
  updateStateIndicators();
  sendAck("ENABLE_MACHINE");
}

void handleDisableMachine() {
  machineEnabled = false;
  machineState = "OFF";
  faultActive = false;
  lockActive = false;
  updateStateIndicators();
  sendAck("DISABLE_MACHINE");
}

void handleSetState(const String& stateName) {
  machineState = stateName;

  if (stateName == "FAULT") {
    faultActive = true;
  } else if (stateName == "LOCKED") {
    lockActive = true;
  }

  updateStateIndicators();
  sendAck("SET_STATE " + stateName);
}

void handleMoveServo(int angle) {
  angle = constrain(angle, 0, 180);
  machineServo.write(angle);
  servoAngle = angle;
  sendAck("MOVE_SERVO " + String(angle));
}

void handleClearFault() {
  faultActive = false;
  if (machineEnabled) {
    machineState = "IDLE";
  } else {
    machineState = "OFF";
  }
  updateStateIndicators();
  sendAck("CLEAR_FAULT");
}

void handleUnlockMachine() {
  lockActive = false;
  if (machineEnabled) {
    machineState = "IDLE";
  } else {
    machineState = "OFF";
  }
  updateStateIndicators();
  sendAck("UNLOCK_MACHINE");
}

void handleAcknowledge() {
  beepShort(50);
  sendAck("ACKNOWLEDGE");
}

void processCommand(String command) {
  command.trim();

  if (command.length() == 0) {
    return;
  }

  if (command == "ENABLE_MACHINE") {
    handleEnableMachine();
    return;
  }

  if (command == "DISABLE_MACHINE") {
    handleDisableMachine();
    return;
  }

  if (command.startsWith("SET_STATE ")) {
    String stateName = command.substring(String("SET_STATE ").length());
    handleSetState(stateName);
    return;
  }

  if (command.startsWith("MOVE_SERVO ")) {
    String angleStr = command.substring(String("MOVE_SERVO ").length());
    int angle = angleStr.toInt();
    handleMoveServo(angle);
    return;
  }

  if (command == "CLEAR_FAULT") {
    handleClearFault();
    return;
  }

  if (command == "UNLOCK_MACHINE") {
    handleUnlockMachine();
    return;
  }

  if (command == "BUZZER ALERT") {
    beepAlert();
    sendAck("BUZZER ALERT");
    return;
  }

  if (command == "ACKNOWLEDGE") {
    handleAcknowledge();
    return;
  }

  if (command == "READ_STATUS") {
    sendStatus();
    return;
  }

  Serial.print("ERR UNKNOWN_COMMAND ");
  Serial.println(command);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_LED_BLUE, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  pinMode(PIN_BTN_A, INPUT_PULLUP);
  pinMode(PIN_BTN_B, INPUT_PULLUP);

  machineServo.attach(PIN_SERVO);
  machineServo.write(servoAngle);

  updateStateIndicators();
  beepShort(60);
  Serial.println("READY GUARDED_MACHINE_CELL");
}

void loop() {
  // Handle incoming serial commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    processCommand(cmd);
  }

  // Optional periodic status every 2s
  if (millis() - lastStatusMs >= 2000) {
    lastStatusMs = millis();
    sendStatus();
  }

  // Button A = approval indicator (local beep only)
  int btnA = digitalRead(PIN_BTN_A);
  if (btnA != lastBtnAStable && millis() - lastDebounceA > 50) {
    lastDebounceA = millis();
    lastBtnAStable = btnA;
    if (btnA == LOW) {
      beepShort(40);
      Serial.println("EVENT BUTTON_A_PRESSED");
    }
  }

  // Button B = reset / acknowledge indicator
  int btnB = digitalRead(PIN_BTN_B);
  if (btnB != lastBtnBStable && millis() - lastDebounceB > 50) {
    lastDebounceB = millis();
    lastBtnBStable = btnB;
    if (btnB == LOW) {
      beepShort(80);

      faultActive = false;
      lockActive = false;
      machineEnabled = false;
      machineState = "OFF";
      servoAngle = 90;
      machineServo.write(servoAngle);
      updateStateIndicators();

      Serial.println("EVENT BUTTON_B_PRESSED");
      sendAck("LOCAL_RESET");
    }
  }
}