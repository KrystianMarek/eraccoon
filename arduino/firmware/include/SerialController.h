//
// Created for serial communication with PC
//

#ifndef SERIALCONTROLLER_H
#define SERIALCONTROLLER_H

#include <Arduino.h>
#include "MotorController.h"
#include "DistanceSensors.h"

struct SerialCommand {
    MotionDirection direction;
    int speed;
    bool valid;
};

class SerialController {
public:
    SerialController();

    SerialCommand getCommand();
    void sendSensorData(DistanceSensors *sensors);
    bool hasCommand();

private:
    String inputString;
    bool commandReady;

    SerialCommand parseCommand(String command);
    MotionDirection parseDirection(String dir);
};

#endif //SERIALCONTROLLER_H