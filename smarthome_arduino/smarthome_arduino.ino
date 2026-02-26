#define TEST_MODE 0
 
const int PIN_SERVO    = 9;
const int PIN_RGB_RED  = 6;
const int PIN_RGB_GRN  = 7;
const int PIN_BUZZER   = 8;
 
const unsigned long FLASH_MS = 400;
const int ANGLE_LOCKED = 90;
const int ANGLE_UNLOCKED = 0;
const unsigned long UNLOCK_HOLD_MS = 5000;
const unsigned long TEST_CYCLE_MS = 8000;
 
int servoPulseUs = 1500;
unsigned long lastServoPulse = 0;
 
unsigned long unlockStartTime = 0;
unsigned long lastTestTime = 0;
bool isUnlocked = false;
unsigned long lastFlashTime = 0;
bool flashOn = true;
 
void setServoAngle(int angle) {
  angle = (angle >= 0 && angle <= 180) ? angle : (angle < 0 ? 0 : 180);
  servoPulseUs = 500 + (angle * 2000) / 180;
}
 
void servoUpdate() {
  unsigned long now = millis();
  if (now - lastServoPulse >= 20) {
    lastServoPulse = now;
    digitalWrite(PIN_SERVO, HIGH);
    delayMicroseconds(servoPulseUs);
    digitalWrite(PIN_SERVO, LOW);
  }
}
 
const int BEEP_FREQ_HIGH = 4000;
const int BEEP_FREQ_LOW  = 3000;
 
void beep(int durationMs, int frequencyHz) {
  tone(PIN_BUZZER, frequencyHz);
  delay(durationMs);
  noTone(PIN_BUZZER);
}
 
void beepDouble() {
  beep(120, BEEP_FREQ_HIGH);
  delay(80);
  beep(120, BEEP_FREQ_HIGH);
}
 
void rgbUpdate() {
  unsigned long now = millis();
  if (now - lastFlashTime >= FLASH_MS) {
    lastFlashTime = now;
    flashOn = !flashOn;
    if (isUnlocked) {
      digitalWrite(PIN_RGB_RED, LOW);
      digitalWrite(PIN_RGB_GRN, flashOn ? HIGH : LOW);
    } else {
      digitalWrite(PIN_RGB_RED, flashOn ? HIGH : LOW);
      digitalWrite(PIN_RGB_GRN, LOW);
    }
  }
}
 
void setup() {
  Serial.begin(9600);
 
  pinMode(PIN_SERVO, OUTPUT);
  pinMode(PIN_RGB_RED, OUTPUT);
  pinMode(PIN_RGB_GRN, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
 
  setServoAngle(ANGLE_LOCKED);
  digitalWrite(PIN_RGB_RED, LOW);
  digitalWrite(PIN_RGB_GRN, LOW);
  noTone(PIN_BUZZER);
 
  for (int i = 0; i < 50; i++) {
    digitalWrite(PIN_SERVO, HIGH);
    delayMicroseconds(servoPulseUs);
    digitalWrite(PIN_SERVO, LOW);
    delay(20);
  }
  beep(200, BEEP_FREQ_HIGH);
}
 
void loop() {
  servoUpdate();
  rgbUpdate();
 
#if TEST_MODE
  if (!isUnlocked && (millis() - lastTestTime >= TEST_CYCLE_MS)) {
    lastTestTime = millis();
    unlock();
  }
#else
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '1') unlock();
  }
#endif
 
  if (isUnlocked && (millis() - unlockStartTime >= UNLOCK_HOLD_MS)) {
    lock();
  }
}
 
void unlock() {
  isUnlocked = true;
  unlockStartTime = millis();
  lastFlashTime = millis();
  flashOn = true;
 
  setServoAngle(ANGLE_UNLOCKED);
  digitalWrite(PIN_RGB_RED, LOW);
  digitalWrite(PIN_RGB_GRN, HIGH);
  beepDouble();
}
 
void lock() {
  isUnlocked = false;
  lastFlashTime = millis();
  flashOn = true;
 
  setServoAngle(ANGLE_LOCKED);
  digitalWrite(PIN_RGB_RED, LOW);
  digitalWrite(PIN_RGB_GRN, LOW);
  beep(150, BEEP_FREQ_LOW);
}