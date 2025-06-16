//
// Created by Krystian Marek on 13/10/2024.
//

#include "JoyRide.h"
#include <DistanceSensors.h>

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

void JoyRide::ride(bool padLock, DistanceSensors *distance_sensors) {
    if (padLock) return;

    if (ticker->tick()) {
        this->_ride(this->_setSpeed(), distance_sensors);
        // this->_ride(this->_calculateSpeed(), distance_sensors);
    }
}

JoyState JoyRide::_calculateSpeed() {
    auto joyState = JoyState();
    joyState.forward = digitalRead(pin_forward);
    joyState.backward = digitalRead(pin_backward);
    joyState.left = digitalRead(pin_left);
    joyState.right = digitalRead(pin_right);

    const long currentTime = millis();
    long deltaTime = currentTime > elapsedMillis ? currentTime - elapsedMillis : 0;
    int accelerationRate = max_speed / acc_time;
    int deltaSpeed = accelerationRate * deltaTime;

    if (joyState.forward || joyState.backward || joyState.left || joyState.right) { // accelerate
        if ( deltaTime < acc_time ) { // within acceleration / declaration window
            speed = min(max_speed, deltaSpeed);
        } else { // past acceleration / declaration window
            speed = max_speed;
        }
    } else { // decelerate
        if ( deltaTime < acc_time ) { // within acceleration / declaration window
            speed = max(0, speed - deltaSpeed);
        } else { // past acceleration / declaration window
            speed = 0;
        }
    }

    if (currentTime > (elapsedMillis + acc_time)) {
        elapsedMillis = currentTime;
    }

    return joyState;
}

JoyState JoyRide::_setSpeed() {
    auto joyState = JoyState();
    joyState.forward = digitalRead(pin_forward);
    joyState.backward = digitalRead(pin_backward);
    joyState.left = digitalRead(pin_left);
    joyState.right = digitalRead(pin_right);

    if (joyState.forward || joyState.backward || joyState.left || joyState.right) { // accelerate
        speed = max_speed;
    } else { // decelerate
        speed = 0;
    }

    return joyState;
}

void JoyRide::_ride(JoyState joyState, DistanceSensors *distance_sensors) {
    if (joyState.forward && not joyState.backward && not joyState.left && not joyState.right) {//forward
        if (not distance_sensors->frontCollison()) {
            motor_fl->setSpeed(speed);
            motor_fr->setSpeed(speed);
            motor_rl->setSpeed(speed);
            motor_rr->setSpeed(speed);
        } else {
            motor_fl->setSpeed(0);
            motor_fr->setSpeed(0);
            motor_rl->setSpeed(0);
            motor_rr->setSpeed(0);
        }
    } else if (joyState.backward && not joyState.forward && not joyState.left && not joyState.right) { //back
        if (not distance_sensors->rearCollison()) {
            motor_fl->setSpeed(-speed);
            motor_fr->setSpeed(-speed);
            motor_rl->setSpeed(-speed);
            motor_rr->setSpeed(-speed);
        } else {
            motor_fl->setSpeed(0);
            motor_fr->setSpeed(0);
            motor_rl->setSpeed(0);
            motor_rr->setSpeed(0);
        }
    } else if (joyState.left and not joyState.right and not joyState.forward and not joyState.backward) { //dead left
        motor_fl->setSpeed(-speed);
        motor_fr->setSpeed(speed);
        motor_rl->setSpeed(-speed);
        motor_rr->setSpeed(speed);
    } else if (joyState.right and not joyState.left and not joyState.forward and not joyState.backward) { //dead right
        motor_fl->setSpeed(speed);
        motor_fr->setSpeed(-speed);
        motor_rl->setSpeed(speed);
        motor_rr->setSpeed(-speed);
    } else {
        //stop
        motor_fl->setSpeed(speed);
        motor_fr->setSpeed(speed);
        motor_rl->setSpeed(speed);
        motor_rr->setSpeed(speed);
    }
}
