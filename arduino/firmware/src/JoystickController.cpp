//
// Created by refactoring JoyRide class
//

#include "JoystickController.h"

JoystickController::JoystickController(
    int pin_forward,
    int pin_backward,
    int pin_left,
    int pin_right,
    int acc_time,
    int max_speed
) {
    this->pin_forward = pin_forward;
    this->pin_backward = pin_backward;
    this->pin_left = pin_left;
    this->pin_right = pin_right;
    this->acc_time = acc_time;
    this->max_speed = max_speed;
    this->speed = 0;
    this->ticker = new Ticker(10);
    this->elapsedMillis = 0;
}

JoyState JoystickController::getJoystickState() {
    if (ticker->tick()) {
        return this->_setSpeed();
    }

    // Return current state if ticker hasn't ticked
    JoyState joyState;
    joyState.forward = digitalRead(pin_forward);
    joyState.backward = digitalRead(pin_backward);
    joyState.left = digitalRead(pin_left);
    joyState.right = digitalRead(pin_right);
    joyState.speed = speed;
    joyState.direction = _determineDirection(joyState.forward, joyState.backward, joyState.left, joyState.right);

    return joyState;
}

bool JoystickController::isActive() {
    return digitalRead(pin_forward) || digitalRead(pin_backward) ||
           digitalRead(pin_left) || digitalRead(pin_right);
}

JoyState JoystickController::_calculateSpeed() {
    JoyState joyState;
    joyState.forward = digitalRead(pin_forward);
    joyState.backward = digitalRead(pin_backward);
    joyState.left = digitalRead(pin_left);
    joyState.right = digitalRead(pin_right);

    const long currentTime = millis();
    long deltaTime = currentTime > elapsedMillis ? currentTime - elapsedMillis : 0;
    int accelerationRate = max_speed / acc_time;
    int deltaSpeed = accelerationRate * deltaTime;

    if (joyState.forward || joyState.backward || joyState.left || joyState.right) { // accelerate
        if (deltaTime < acc_time) { // within acceleration window
            speed = min(max_speed, deltaSpeed);
        } else { // past acceleration window
            speed = max_speed;
        }
    } else { // decelerate
        if (deltaTime < acc_time) { // within deceleration window
            speed = max(0, speed - deltaSpeed);
        } else { // past deceleration window
            speed = 0;
        }
    }

    if (currentTime > (elapsedMillis + acc_time)) {
        elapsedMillis = currentTime;
    }

    joyState.speed = speed;
    joyState.direction = _determineDirection(joyState.forward, joyState.backward, joyState.left, joyState.right);

    return joyState;
}

JoyState JoystickController::_setSpeed() {
    JoyState joyState;
    joyState.forward = digitalRead(pin_forward);
    joyState.backward = digitalRead(pin_backward);
    joyState.left = digitalRead(pin_left);
    joyState.right = digitalRead(pin_right);

    if (joyState.forward || joyState.backward || joyState.left || joyState.right) {
        speed = max_speed;
    } else {
        speed = 0;
    }

    joyState.speed = speed;
    joyState.direction = _determineDirection(joyState.forward, joyState.backward, joyState.left, joyState.right);

    return joyState;
}

MotionDirection JoystickController::_determineDirection(bool forward, bool backward, bool left, bool right) {
    if (forward && !backward && !left && !right) {
        return FORWARD;
    } else if (backward && !forward && !left && !right) {
        return BACKWARD;
    } else if (left && !right && !forward && !backward) {
        return LEFT;
    } else if (right && !left && !forward && !backward) {
        return RIGHT;
    } else if (forward && left && !backward && !right) {
        return FORWARD_LEFT;
    } else if (forward && right && !backward && !left) {
        return FORWARD_RIGHT;
    } else if (backward && left && !forward && !right) {
        return BACKWARD_LEFT;
    } else if (backward && right && !forward && !left) {
        return BACKWARD_RIGHT;
    } else {
        return STOP;
    }
}