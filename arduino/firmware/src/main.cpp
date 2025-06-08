#include <Arduino.h>
#include <JoyRide.h>
#include <DistanceSensors.h>

#include "CytronMotorDriver.h"
#include "MyLCD.h"
#include <SerialLogger.h>
#include "Pad.h"

// Define Joystick pins
constexpr int PIN_J_FORWARD = 22;
constexpr int PIN_J_BACK = 25;
constexpr int PIN_J_LEFT = 24;
constexpr int PIN_J_RIGHT = 23;

constexpr int CHILD_MAX_SPEED = 60;
constexpr unsigned int CHILD_ACCELERATION_TIME = 1000; // Time to reach full speed in milliseconds

void setup_joystick() {
  for(int i=22;i<26;i++)
    pinMode(i,INPUT);
}

JoyRide *joyRide;
DistanceSensors *distanceSensors;
MyLCD *lcd;
SerialLogger *logger;
Pad *pad;

void setup() {
  lcd = new MyLCD();
  // Print a message to the LCD.
  lcd->print("hello4!");
  logger = new SerialLogger();
  // Serial.begin(115200);
  logger->println("<Arduino is ready>");

  // https://forum.arduino.cc/t/bluetooth-classic-on-giga-r1/1110561 !!
  // pad = new Pad(logger, "AC:36:1B:D9:96:5E");

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
  // pad->connect();
  joyRide->ride(false, distanceSensors);
}