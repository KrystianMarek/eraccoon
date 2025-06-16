#pragma once

#include "MotorController.h"

struct SerialCommand {
    MotionDirection direction;
    int speed;
    bool valid;
};