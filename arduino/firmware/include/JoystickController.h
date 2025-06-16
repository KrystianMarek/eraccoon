//
// Created by refactoring JoyRide class
//

#ifndef JOYSTICKCONTROLLER_H
#define JOYSTICKCONTROLLER_H

#include <Arduino.h>
#include <Ticker.h>
#include "MotorController.h"

struct JoyState {
    bool forward;
    bool backward;
    bool left;
    bool right;
    int speed;
    MotionDirection direction;
};

class JoystickController {
public:
    JoystickController(
        int pin_forward,
        int pin_backward,
        int pin_left,
        int pin_right,
        int acc_time,
        int max_speed
    );

    JoyState getJoystickState();
    bool isActive();

private:
    int pin_forward;
    int pin_backward;
    int pin_left;
    int pin_right;
    int acc_time;
    int max_speed;
    int speed;

    long elapsedMillis;
    Ticker *ticker;

    JoyState _calculateSpeed();
    JoyState _setSpeed();
    MotionDirection _determineDirection(bool forward, bool backward, bool left, bool right);
};

#endif //JOYSTICKCONTROLLER_H