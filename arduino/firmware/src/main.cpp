#include <Arduino.h>
#include <JoyRide.h>

#include "CytronMotorDriver.h"
#include "DFRobot_RGBLCD1602.h"

// Define Joystick pins
constexpr int PIN_J_FORWARD = 22;
constexpr int PIN_J_BACK = 25;
constexpr int PIN_J_LEFT = 24;
constexpr int PIN_J_RIGHT = 23;

constexpr int CHILD_MAX_SPEED = 60;
constexpr unsigned long CHILD_ACCELERATION_TIME = 2000; // Time to reach full speed in milliseconds

// LCD
const int colorR = 0;
const int colorG = 128;
const int colorB = 0;

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

JoyRide *joyRide;

void setup() {
  lcd.init();
  lcd.clear();
  lcd.setRGB(colorR, colorG, colorB);
    
  // Print a message to the LCD.
  lcd.print("hello2!");
  setup_joystick();

  joyRide = new JoyRide(PIN_J_FORWARD, PIN_J_BACK, PIN_J_LEFT, PIN_J_RIGHT,
  CHILD_ACCELERATION_TIME, CHILD_MAX_SPEED,
  new CytronMD(PWM_PWM, 2, 3), new CytronMD(PWM_PWM, 6, 7),
  new CytronMD(PWM_PWM, 4, 5), new CytronMD(PWM_PWM, 8, 9)
  );
}

// The loop routine runs over and over again forever.
void loop() {
  joyRide->ride(false);
  // sharp();
}