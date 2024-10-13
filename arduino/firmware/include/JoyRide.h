//
// Created by Krystian Marek on 13/10/2024.
//

#ifndef JOYRIDE_H
#define JOYRIDE_H

#include <Arduino.h>
#include <CytronMotorDriver.h>
#include <Ticker.h>


class JoyRide {
public:
    JoyRide(
        int pin_forward,
        int pin_backward,
        int pin_left,
        int pin_right,
        int acc_time,
        int max_speed,
        CytronMD *motor_fl,
        CytronMD *motor_fr,
        CytronMD *motor_rl,
        CytronMD *motor_rr
        );

    void ride(bool padLock);
private:
    int pin_forward;
    int pin_backward;
    int pin_left;
    int pin_right;
    int acc_time;
    int max_speed;
    int speed;
    CytronMD *motor_fl;
    CytronMD *motor_fr;
    CytronMD *motor_rl;
    CytronMD *motor_rr;

    unsigned long elapsedMillis;
    Ticker *ticker;

    void _ride(int speed);
};



#endif //JOYRIDE_H
