//
// Created by refactoring JoyRide class
//

#ifndef MOTORCONTROLLER_H
#define MOTORCONTROLLER_H

#include <Arduino.h>
#include <CytronMotorDriver.h>

enum MotionDirection {
    STOP = 0,
    FORWARD = 1,
    BACKWARD = 2,
    LEFT = 3,
    RIGHT = 4,
    FORWARD_LEFT = 5,
    FORWARD_RIGHT = 6,
    BACKWARD_LEFT = 7,
    BACKWARD_RIGHT = 8,
    ROBOT_RESET = 9,
    KEEPALIVE_CMD = 10
};

class MotorController {
public:
    MotorController(
        CytronMD *motor_fl,
        CytronMD *motor_fr,
        CytronMD *motor_rl,
        CytronMD *motor_rr
    );

    void move(MotionDirection direction, int speed);
    void stop();
    void setMotorSpeeds(int fl_speed, int fr_speed, int rl_speed, int rr_speed);
    void moveWithDirectControl(int fl_speed, int fr_speed, int rl_speed, int rr_speed);

private:
    CytronMD *motor_fl;
    CytronMD *motor_fr;
    CytronMD *motor_rl;
    CytronMD *motor_rr;
};

#endif //MOTORCONTROLLER_H