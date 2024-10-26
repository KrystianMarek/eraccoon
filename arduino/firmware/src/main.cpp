#include <Arduino.h>
#include <JoyRide.h>
#include <DistanceSensors.h>

#include "CytronMotorDriver.h"
#include "DFRobot_RGBLCD1602.h"

// Define Joystick pins
constexpr int PIN_J_FORWARD = 22;
constexpr int PIN_J_BACK = 25;
constexpr int PIN_J_LEFT = 24;
constexpr int PIN_J_RIGHT = 23;

constexpr int CHILD_MAX_SPEED = 60;
constexpr unsigned long CHILD_ACCELERATION_TIME = 1000; // Time to reach full speed in milliseconds

// LCD
const int colorR = 0;
const int colorG = 128;
const int colorB = 0;

DFRobot_RGBLCD1602 lcd(0x2D, 16, 2);

void setup_joystick() {
  for(int i=22;i<26;i++)
    pinMode(i,INPUT);
}

JoyRide *joyRide;
DistanceSensors *distanceSensors;

void setup() {
  lcd.init();
  lcd.clear();
  lcd.setRGB(colorR, colorG, colorB);
    
  // Print a message to the LCD.
  lcd.print("hello3!");
  Serial.begin(115200);
  Serial.println("<Arduino is ready>");

  setup_joystick();
    distanceSensors = new DistanceSensors();

  joyRide = new JoyRide(PIN_J_FORWARD, PIN_J_BACK, PIN_J_LEFT, PIN_J_RIGHT,
  CHILD_ACCELERATION_TIME, CHILD_MAX_SPEED,
  new CytronMD(PWM_PWM, 2, 3), new CytronMD(PWM_PWM, 6, 7),
  new CytronMD(PWM_PWM, 4, 5), new CytronMD(PWM_PWM, 8, 9)
  );
}

// The loop routine runs over and over again forever.
void loop() {
  joyRide->ride(false, distanceSensors);
}