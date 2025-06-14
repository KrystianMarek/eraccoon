//
// Created for serial communication with PC
//

#ifndef SERIALCONTROLLER_H
#define SERIALCONTROLLER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "MotorController.h"
#include "DistanceSensors.h"

enum CommandType {
    TANK_COMMAND,
    MECANUM_COMMAND,
    LEGACY_COMMAND,
    INVALID_COMMAND
};

struct SerialCommand {
    CommandType type;
    MotionDirection direction;  // For tank/legacy commands
    int speed;                  // For tank/legacy commands
    int motor_speeds[4];        // For mecanum commands: [left_front, left_rear, right_front, right_rear]
    bool valid;
};

class SerialController {
public:
    SerialController();

    SerialCommand getCommand();
    bool sendSensorData(DistanceSensors *sensors);
    bool hasCommand();

private:
    String inputString;
    bool commandReady;

    SerialCommand parseCommand(String command);
    SerialCommand parseJsonCommand(String command);
    SerialCommand parseLegacyCommand(String command);
    MotionDirection parseDirection(String dir);
};

#endif //SERIALCONTROLLER_H