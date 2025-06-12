//
// Created to orchestrate robot control from multiple sources
//

#ifndef ROBOTCONTROLLER_H
#define ROBOTCONTROLLER_H

#include <Arduino.h>
#include "MotorController.h"
#include "JoystickController.h"
#include "SerialController.h"
#include "DistanceSensors.h"
#include "Ticker.h"
#include "MyLCD.h"

class RobotController {
public:
    RobotController(
        MotorController *motorController,
        JoystickController *joystickController,
        SerialController *serialController,
        DistanceSensors *distanceSensors,
        MyLCD *lcd
    );

    void update();

private:
        MotorController *motorController;
    JoystickController *joystickController;
    SerialController *serialController;
    DistanceSensors *distanceSensors;
    MyLCD *lcd;

    Ticker *sensorReportTicker;
    Ticker *lcdUpdateTicker;

    // Serial command persistence
    SerialCommand lastSerialCommand;
    unsigned long lastSerialCommandTime;
    static const unsigned long SERIAL_COMMAND_TIMEOUT = 1000; // Keep command active for 1000ms for visible movement

    // Serial connection monitoring
    unsigned long lastSerialActivity;
    static const unsigned long SERIAL_DISCONNECT_TIMEOUT = 5000; // 5 seconds without serial = disconnected

    // Safety system state tracking
    bool wasPreviouslyBlocked;

    void handleJoystickControl();
    bool isMovementSafe(MotionDirection direction);
    bool hasActiveSerialCommand();
    void updateLCDDisplay();
    void resetAllStates();
};

#endif //ROBOTCONTROLLER_H