#include <Arduino.h>
#include <JoyRide.h>
#include <DistanceSensors.h>

#include "CytronMotorDriver.h"
#include "MyLCD.h"
#include <ArduinoBLE.h>
#include <SerialLogger.h>

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

void setup() {
  lcd = new MyLCD();
  // Print a message to the LCD.
  lcd->print("hello4!");
  logger = new SerialLogger();
  // Serial.begin(115200);
  logger->println("<Arduino is ready>");

  // begin initialization
  if (!BLE.begin()) {
    Serial.println("starting Bluetooth® Low Energy module failed!");

    while (1);
  }
  Serial.println("Bluetooth® Low Energy Central scan");
  // start scanning for peripheral
  BLE.scan();

  setup_joystick();
    distanceSensors = new DistanceSensors();

  joyRide = new JoyRide(PIN_J_FORWARD, PIN_J_BACK, PIN_J_LEFT, PIN_J_RIGHT,
  CHILD_ACCELERATION_TIME, CHILD_MAX_SPEED,
  new CytronMD(PWM_PWM, 2, 3), new CytronMD(PWM_PWM, 6, 7),
  new CytronMD(PWM_PWM, 4, 5), new CytronMD(PWM_PWM, 8, 9)
  );
}

/**
DUALSHOCK 4 Wireless Controller:
Address: 88:03:4C:06:2D:EB
Vendor ID: 0x054C
Product ID: 0x09CC
Firmware Version: 1.0.0
Minor Type: Gamepad
RSSI: -52
Services: 0x800020 < HID ACL >
 */

void _bt_scan() {
  // check if a peripheral has been discovered
  BLEDevice peripheral = BLE.available();

  if (peripheral) {
    // discovered a peripheral
    Serial.println("Discovered a peripheral");
    Serial.println("-----------------------");

    // print address
    Serial.print("Address: ");
    Serial.println(peripheral.address());

    // print the local name, if present
    if (peripheral.hasLocalName()) {
      Serial.print("Local Name: ");
      Serial.println(peripheral.localName());
    }

    // print the advertised service UUIDs, if present
    if (peripheral.hasAdvertisedServiceUuid()) {
      Serial.print("Service UUIDs: ");
      for (int i = 0; i < peripheral.advertisedServiceUuidCount(); i++) {
        Serial.print(peripheral.advertisedServiceUuid(i));
        Serial.print(" ");
      }
      Serial.println();
    }

    // print the RSSI
    Serial.print("RSSI: ");
    Serial.println(peripheral.rssi());

    Serial.println();
  }
}

// The loop routine runs over and over again forever.
void loop() {
  _bt_scan();
  joyRide->ride(false, distanceSensors);
}