//
// Created by Krystian Marek on 13/10/2024.
//

#include "JoyRide.h"

JoyRide::JoyRide(
        const int pin_forward,
        const int pin_backward,
        const int pin_left,
        const int pin_right,
        const int acc_time,
        const int max_speed,
        CytronMD *motor_fl,
        CytronMD *motor_fr,
        CytronMD *motor_rl,
        CytronMD *motor_rr
        ) {
    
    this->pin_forward = pin_forward;
    this->pin_backward = pin_backward;
    this->pin_left = pin_left;
    this->pin_right = pin_right;
    this->acc_time = acc_time;
    this->max_speed = max_speed;
    this->speed = 0;
    this->motor_fl = motor_fl;
    this->motor_fr = motor_fr;
    this->motor_rl = motor_rl;
    this->motor_rr = motor_rr;

    this->ticker = new Ticker(10);

    this->elapsedMillis = 0;
}

void JoyRide::ride(const bool padLock) {
    if (padLock) return;

    const unsigned long currentTime = millis();
    int16_t speed = 0;
    
    if ((currentTime + acc_time) < elapsedMillis ) {
        speed = static_cast<int16_t>(max_speed * (currentTime - elapsedMillis) / acc_time);
    } else {
        speed = max_speed;
        elapsedMillis = currentTime;
    }
    
    if (ticker->tick()) {
        this->_ride(speed);
    }
}

void JoyRide::_ride(int speed) {
    bool forward = digitalRead(pin_forward);
    bool backward = digitalRead(pin_backward);
    bool left = digitalRead(pin_left);
    bool right = digitalRead(pin_right);

    
    if (forward && not backward && not left && not right) {  //forward
        motor_fl->setSpeed(speed);
        motor_fr->setSpeed(speed);
        motor_rl->setSpeed(speed);
        motor_rr->setSpeed(speed);
    } else if (backward && not forward && not left && not right) { //back
        motor_fl->setSpeed(-speed);
        motor_fr->setSpeed(-speed);
        motor_rl->setSpeed(-speed);
        motor_rr->setSpeed(-speed);
    } else if (left and not right and not forward and not backward) { //dead left
        motor_fl->setSpeed(-speed);
        motor_fr->setSpeed(speed);
        motor_rl->setSpeed(-speed);
        motor_rr->setSpeed(speed);
    } else if (right and not left and not forward and not backward) { //dead right
        motor_fl->setSpeed(speed);
        motor_fr->setSpeed(-speed);
        motor_rl->setSpeed(speed);
        motor_rr->setSpeed(-speed);
    } else {
        //stop
        motor_fl->setSpeed(0);
        motor_fr->setSpeed(0);
        motor_rl->setSpeed(0);
        motor_rr->setSpeed(0);
    }
}