//
// Created by refactoring JoyRide class
//

#include "MotorController.h"

MotorController::MotorController(
    CytronMD *motor_fl,
    CytronMD *motor_fr,
    CytronMD *motor_rl,
    CytronMD *motor_rr
) {
    this->motor_fl = motor_fl;
    this->motor_fr = motor_fr;
    this->motor_rl = motor_rl;
    this->motor_rr = motor_rr;
}

void MotorController::move(MotionDirection direction, int speed) {
    // Add debug output to see what commands are actually being executed
    static MotionDirection lastDirection = STOP;
    static int lastSpeed = 0;

    if (direction != lastDirection || speed != lastSpeed) {
        Serial.print("🚗 MOTOR: Executing ");
        switch(direction) {
            case FORWARD: Serial.print("FORWARD"); break;
            case BACKWARD: Serial.print("BACKWARD"); break;
            case LEFT: Serial.print("LEFT"); break;
            case RIGHT: Serial.print("RIGHT"); break;
            case FORWARD_LEFT: Serial.print("FORWARD_LEFT"); break;
            case FORWARD_RIGHT: Serial.print("FORWARD_RIGHT"); break;
            case BACKWARD_LEFT: Serial.print("BACKWARD_LEFT"); break;
            case BACKWARD_RIGHT: Serial.print("BACKWARD_RIGHT"); break;
            case STOP: Serial.print("STOP"); break;
            case ROBOT_RESET: Serial.print("RESET"); break;
            default: Serial.print("UNKNOWN"); break;
        }
        Serial.print(" at speed ");
        Serial.println(speed);
        lastDirection = direction;
        lastSpeed = speed;
    }

    switch(direction) {
        case FORWARD:
            motor_fl->setSpeed(speed);
            motor_fr->setSpeed(speed);
            motor_rl->setSpeed(speed);
            motor_rr->setSpeed(speed);
            break;
        case BACKWARD:
            motor_fl->setSpeed(-speed);
            motor_fr->setSpeed(-speed);
            motor_rl->setSpeed(-speed);
            motor_rr->setSpeed(-speed);
            break;
        case LEFT:
            motor_fl->setSpeed(-speed);
            motor_fr->setSpeed(speed);
            motor_rl->setSpeed(-speed);
            motor_rr->setSpeed(speed);
            break;
        case RIGHT:
            motor_fl->setSpeed(speed);
            motor_fr->setSpeed(-speed);
            motor_rl->setSpeed(speed);
            motor_rr->setSpeed(-speed);
            break;
        case FORWARD_LEFT:
            motor_fl->setSpeed(speed/2);
            motor_fr->setSpeed(speed);
            motor_rl->setSpeed(speed/2);
            motor_rr->setSpeed(speed);
            break;
        case FORWARD_RIGHT:
            motor_fl->setSpeed(speed);
            motor_fr->setSpeed(speed/2);
            motor_rl->setSpeed(speed);
            motor_rr->setSpeed(speed/2);
            break;
        case BACKWARD_LEFT:
            motor_fl->setSpeed(-speed/2);
            motor_fr->setSpeed(-speed);
            motor_rl->setSpeed(-speed/2);
            motor_rr->setSpeed(-speed);
            break;
        case BACKWARD_RIGHT:
            motor_fl->setSpeed(-speed);
            motor_fr->setSpeed(-speed/2);
            motor_rl->setSpeed(-speed);
            motor_rr->setSpeed(-speed/2);
            break;
        case STOP:
        case ROBOT_RESET:
        default:
            stop();
            break;
    }
}

void MotorController::stop() {
    motor_fl->setSpeed(0);
    motor_fr->setSpeed(0);
    motor_rl->setSpeed(0);
    motor_rr->setSpeed(0);
}

void MotorController::setMotorSpeeds(int fl_speed, int fr_speed, int rl_speed, int rr_speed) {
    motor_fl->setSpeed(fl_speed);
    motor_fr->setSpeed(fr_speed);
    motor_rl->setSpeed(rl_speed);
    motor_rr->setSpeed(rr_speed);
}