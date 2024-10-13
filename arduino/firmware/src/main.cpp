#include <Arduino.h>
#include "CytronMotorDriver.h"
#include "DFRobot_RGBLCD1602.h"

// Define Joystick pins
const int PIN_J_FORWARD = 22;
const int PIN_J_BACK = 25;
const int PIN_J_LEFT = 24;
const int PIN_J_RIGHT = 23;

const int CHILD_MAX_SPEED = 60;
const unsigned long CHILD_ACCELERATION_TIME = 1000; // Time to reach full speed in milliseconds

// LCD
const int colorR = 0;
const int colorG = 128;
const int colorB = 0;

// Define the motor driver pins
CytronMD motor_fl(PWM_PWM, 2, 3);   
CytronMD motor_rl(PWM_PWM, 4, 5);
CytronMD motor_fr(PWM_PWM, 6, 7);   
CytronMD motor_rr(PWM_PWM, 8, 9);

DFRobot_RGBLCD1602 lcd(0x2D, 16, 2);

void setup_joystick() {
  for(int i=22;i<26;i++)
    pinMode(i,INPUT);
}

//Sharp sensors
const float distance_constant = 0.0048828125;
unsigned long lastUpdateTimeSharp = 0;
unsigned long lastUpdateTimeJoy = 0;
const unsigned long updateInterval = 1000;

void sharp() {
    //https://www.instructables.com/How-to-Use-the-Sharp-IR-Sensor-GP2Y0A41SK0F-Arduin/
    float volts_fl = analogRead(A0)*distance_constant;  // value from sensor * (5/1024)
    float volts_fr = analogRead(A1)*distance_constant;
    float volts_rl = analogRead(A2)*distance_constant;
    float volts_rr = analogRead(A3)*distance_constant;

    int distance_fl = 13*pow(volts_fl, -1); // worked out from datasheet graph
    int distance_fr = 13*pow(volts_fr, -1);
    int distance_rl = 13*pow(volts_rl, -1);
    int distance_rr = 13*pow(volts_rr, -1);

    unsigned long currentTime = millis();
    if (currentTime - lastUpdateTimeSharp >= updateInterval) {
        lcd.clear();

        lcd.print(String("fl: " + String(distance_fl) + " |fr: " + String(distance_fr) + "\n|rl: " + String(distance_rl) + " |rr: " + String(distance_rr)));
        lastUpdateTimeSharp = currentTime;
    }
}

void setup() {
  lcd.init();
  lcd.clear();
  lcd.setRGB(colorR, colorG, colorB);
    
  // Print a message to the LCD.
  lcd.print("hello!");
  setup_joystick();
}

void j_ride(int forward, int backward, int left, int right) {

    unsigned long currentTime = millis();
    unsigned long deltaTime = currentTime - lastUpdateTimeJoy;
    lastUpdateTimeJoy = currentTime;

    bool j_forward = digitalRead(PIN_J_FORWARD);
    bool j_backward = digitalRead(PIN_J_BACK);
    bool j_left = digitalRead(PIN_J_LEFT);
    bool j_right = digitalRead(PIN_J_RIGHT);

    int targetSpeed = 0;
    if (forward || backward || left || right) {
        targetSpeed = CHILD_MAX_SPEED;
    }

    // Calculate speed change
    int speedChange = (int)((float)CHILD_MAX_SPEED * deltaTime / CHILD_ACCELERATION_TIME);
    int currentSpeed = 0;

    // Accelerate or decelerate
    if (targetSpeed > currentSpeed) {
      currentSpeed = min(currentSpeed + speedChange, CHILD_MAX_SPEED);
    } else if (targetSpeed < currentSpeed) {
      currentSpeed = max(currentSpeed - speedChange, 0);
    }

  if (j_forward == HIGH && j_backward == LOW && j_left == LOW && j_right == LOW) {  //forward
    motor_fl.setSpeed(currentSpeed);
    motor_fr.setSpeed(currentSpeed);
    motor_rl.setSpeed(currentSpeed);
    motor_rr.setSpeed(currentSpeed);
  } else if (j_forward == LOW && j_backward == HIGH && j_left == LOW && j_right == LOW) { //back
    motor_fl.setSpeed(-currentSpeed);
    motor_fr.setSpeed(-currentSpeed);
    motor_rl.setSpeed(-currentSpeed);
    motor_rr.setSpeed(-currentSpeed);
  } else if (j_forward == LOW && j_backward == LOW && j_left == HIGH && j_right == LOW) { //dead left
    motor_fl.setSpeed(-currentSpeed);
    motor_fr.setSpeed(currentSpeed);
    motor_rl.setSpeed(-currentSpeed);
    motor_rr.setSpeed(currentSpeed);
  } else if (j_forward == LOW && j_backward == LOW && j_left == LOW && j_right == HIGH) { //dead right
    motor_fl.setSpeed(currentSpeed);
    motor_fr.setSpeed(-currentSpeed);
    motor_rl.setSpeed(currentSpeed);
    motor_rr.setSpeed(-currentSpeed);
  } else {
    //stop
    motor_fl.setSpeed(0);
    motor_fr.setSpeed(0);
    motor_rl.setSpeed(0);
    motor_rr.setSpeed(0);
  }
}

// The loop routine runs over and over again forever.
void loop() {
  j_ride(digitalRead(PIN_J_FORWARD), digitalRead(PIN_J_BACK), digitalRead(PIN_J_LEFT), digitalRead(PIN_J_RIGHT));
  sharp();
}

/*

const int DESIRED_SPEED = 255; // Maximum motor speed
const unsigned long ACCELERATION_TIME = 1000; // Time to reach full speed in milliseconds

unsigned long lastUpdateTime = 0;
int currentSpeed = 0;

void controlMotors() {
  unsigned long currentTime = millis();
  unsigned long deltaTime = currentTime - lastUpdateTime;
  lastUpdateTime = currentTime;

  bool forward = digitalRead(J_FORWARD);
  bool backward = digitalRead(J_BACKWARD);
  bool left = digitalRead(J_LEFT);
  bool right = digitalRead(J_RIGHT);

  int targetSpeed = 0;
  if (forward || backward || left || right) {
    targetSpeed = DESIRED_SPEED;
  }

  // Calculate speed change
  int speedChange = (int)((float)DESIRED_SPEED * deltaTime / ACCELERATION_TIME);
  
  // Accelerate or decelerate
  if (targetSpeed > currentSpeed) {
    currentSpeed = min(currentSpeed + speedChange, DESIRED_SPEED);
  } else if (targetSpeed < currentSpeed) {
    currentSpeed = max(currentSpeed - speedChange, 0);
  }

  // Set motor speeds based on joystick input
  if (forward) {
    motor_fl.setSpeed(currentSpeed);
    motor_fr.setSpeed(currentSpeed);
    motor_rl.setSpeed(currentSpeed);
    motor_rr.setSpeed(currentSpeed);
  } else if (backward) {
    motor_fl.setSpeed(-currentSpeed);
    motor_fr.setSpeed(-currentSpeed);
    motor_rl.setSpeed(-currentSpeed);
    motor_rr.setSpeed(-currentSpeed);
  } else if (left) {
    motor_fl.setSpeed(-currentSpeed);
    motor_fr.setSpeed(currentSpeed);
    motor_rl.setSpeed(-currentSpeed);
    motor_rr.setSpeed(currentSpeed);
  } else if (right) {
    motor_fl.setSpeed(currentSpeed);
    motor_fr.setSpeed(-currentSpeed);
    motor_rl.setSpeed(currentSpeed);
    motor_rr.setSpeed(-currentSpeed);
  } else {
    // No input, stop all motors
    motor_fl.setSpeed(0);
    motor_fr.setSpeed(0);
    motor_rl.setSpeed(0);
    motor_rr.setSpeed(0);
  }
}

*/