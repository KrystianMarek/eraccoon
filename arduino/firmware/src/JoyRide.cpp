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

    if (ticker->tick()) {
        this->_ride(this->_calculateSpeed());
    }
}

JoyState JoyRide::_calculateSpeed() {
    auto joyState = JoyState();
    joyState.forward = digitalRead(pin_forward);
    joyState.backward = digitalRead(pin_backward);
    joyState.left = digitalRead(pin_left);
    joyState.right = digitalRead(pin_right);
    joyState.speed = 0;

    const unsigned long currentTime = millis();
    long unsigned long deltaTime = abs(currentTime - elapsedMillis);
    int accelerationRate = max_speed / acc_time;

    if (joyState.forward || joyState.backward || joyState.left || joyState.right) { // accelerate
        if ( deltaTime < acc_time ) { // within acceleration / declaration window
            joyState.speed += accelerationRate * deltaTime;
        } else { // past acceleration / declaration window
            joyState.speed = max_speed;
        }
    } else { // decelerate
        if ( deltaTime < acc_time ) { // within acceleration / declaration window
            joyState.speed -= accelerationRate * deltaTime;
        } else { // past acceleration / declaration window
            joyState.speed = 0;
        }
    }

    if (currentTime > elapsedMillis + acc_time) {
        elapsedMillis = currentTime;
    }

    return joyState;
}

void JoyRide::_ride(JoyState joyState) {
    if (joyState.forward && not joyState.backward && not joyState.left && not joyState.right) {  //forward
        motor_fl->setSpeed(joyState.speed);
        motor_fr->setSpeed(joyState.speed);
        motor_rl->setSpeed(joyState.speed);
        motor_rr->setSpeed(joyState.speed);
    } else if (joyState.backward && not joyState.forward && not joyState.left && not joyState.right) { //back
        motor_fl->setSpeed(-joyState.speed);
        motor_fr->setSpeed(-joyState.speed);
        motor_rl->setSpeed(-joyState.speed);
        motor_rr->setSpeed(-joyState.speed);
    } else if (joyState.left and not joyState.right and not joyState.forward and not joyState.backward) { //dead left
        motor_fl->setSpeed(-joyState.speed);
        motor_fr->setSpeed(joyState.speed);
        motor_rl->setSpeed(-joyState.speed);
        motor_rr->setSpeed(joyState.speed);
    } else if (joyState.right and not joyState.left and not joyState.forward and not joyState.backward) { //dead right
        motor_fl->setSpeed(joyState.speed);
        motor_fr->setSpeed(-joyState.speed);
        motor_rl->setSpeed(joyState.speed);
        motor_rr->setSpeed(-joyState.speed);
    } else {
        //stop
        motor_fl->setSpeed(joyState.speed);
        motor_fr->setSpeed(joyState.speed);
        motor_rl->setSpeed(joyState.speed);
        motor_rr->setSpeed(joyState.speed);
    }
}