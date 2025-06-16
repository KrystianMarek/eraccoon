#include <Arduino.h>
#include "DistanceSensors.h"
#include "CytronMotorDriver.h"
#include "MyLCD.h"
#include "MotorController.h"
#include "JoystickController.h"
#include "SerialController.h"
#include "RobotController.h"

// Define Joystick pins
constexpr int PIN_J_FORWARD = 22;
constexpr int PIN_J_BACK = 25;
constexpr int PIN_J_LEFT = 24;
constexpr int PIN_J_RIGHT = 23;

constexpr int CHILD_MAX_SPEED = 60;
constexpr unsigned int CHILD_ACCELERATION_TIME = 1000; // Time to reach full speed in milliseconds

void setup_joystick() {
  // Set up joystick pins with pullup resistors
  // This ensures pins read HIGH when not pressed, LOW when pressed
  for(int i=22;i<26;i++)
    pinMode(i,INPUT_PULLUP);

  Serial.println("🎮 Joystick pins 22-25 configured with INPUT_PULLUP");
}

MotorController *motorController;
JoystickController *joystickController;
SerialController *serialController;
RobotController *robotController;
DistanceSensors *distanceSensors;
MyLCD *lcd;

void setup() {
  // Initialize Serial communication first
  Serial.begin(115200);

  // Wait a bit for serial to stabilize and send multiple startup messages
  delay(1000);
  Serial.println();
  Serial.println("🚀 ===== ARDUINO ROBOT STARTING =====");
  Serial.println("🔧 System: Initializing...");
  Serial.print("💾 RAM: ");
  Serial.print(11.7);
  Serial.println("% used");
  Serial.print("⚡ Flash: ");
  Serial.print(15.0);
  Serial.println("% used");

  lcd = new MyLCD();
  // Print a message to the LCD.
  lcd->print("hello11!");

  Serial.println("📺 LCD: Initialized");
  Serial.println("🎮 Joystick: Configuring pins...");

  setup_joystick();
  distanceSensors = new DistanceSensors();
  Serial.println("📡 Sensors: Initialized");

  // Create motor controller
  motorController = new MotorController(
    new CytronMD(PWM_PWM, 2, 3), new CytronMD(PWM_PWM, 6, 7),
    new CytronMD(PWM_PWM, 4, 5), new CytronMD(PWM_PWM, 8, 9)
  );
  Serial.println("🚗 Motors: Initialized");

  // Create joystick controller
  joystickController = new JoystickController(
    PIN_J_FORWARD, PIN_J_BACK, PIN_J_LEFT, PIN_J_RIGHT,
    CHILD_ACCELERATION_TIME, CHILD_MAX_SPEED
  );
  Serial.println("🕹️  Joystick Controller: Ready");

  // Create serial controller (initializes Serial communication)
  serialController = new SerialController();
  Serial.println("📡 Serial Controller: Ready");

  // Create robot controller that orchestrates everything
  robotController = new RobotController(
    motorController, joystickController, serialController, distanceSensors, lcd
  );
  Serial.println("🤖 Robot Controller: Ready");
  Serial.println("✅ SYSTEM READY - Awaiting commands");
  Serial.println("📋 Commands: FORWARD:speed, BACKWARD:speed, LEFT:speed, RIGHT:speed, STOP:0, RESET:0");
  Serial.println("===== STARTUP COMPLETE =====");
  Serial.println();
}

// The loop routine runs over and over again forever.
void loop() {
  // Simple periodic ready message during startup
  static unsigned long lastReadyMessage = 0;
  unsigned long currentTime = millis();

  // Send ready message every 10 seconds for first 60 seconds after boot
  if (currentTime < 60000 && currentTime - lastReadyMessage > 10000) {
    Serial.println("🚀 SYSTEM READY - Accepting connections");
    lastReadyMessage = currentTime;
  }

  // pad->connect();
  robotController->update();
}