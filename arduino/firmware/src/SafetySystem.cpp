#include "SafetySystem.h"

SafetySystem::SafetySystem(int frontLeftPin, int frontRightPin, int rearLeftPin, int rearRightPin)
    : frontLeftPin(frontLeftPin), frontRightPin(frontRightPin),
      rearLeftPin(rearLeftPin), rearRightPin(rearRightPin) {

    pinMode(frontLeftPin, INPUT);
    pinMode(frontRightPin, INPUT);
    pinMode(rearLeftPin, INPUT);
    pinMode(rearRightPin, INPUT);
}

void SafetySystem::update() {
    updateDistances();
}

void SafetySystem::updateDistances() {
    frontLeftDistance = analogRead(frontLeftPin) * DISTANCE_CONSTANT;
    frontRightDistance = analogRead(frontRightPin) * DISTANCE_CONSTANT;
    rearLeftDistance = analogRead(rearLeftPin) * DISTANCE_CONSTANT;
    rearRightDistance = analogRead(rearRightPin) * DISTANCE_CONSTANT;
}

bool SafetySystem::isMovementSafe(MotionDirection direction) const {
    switch(direction) {
        case FORWARD:
        case FORWARD_LEFT:
        case FORWARD_RIGHT:
            return !isFrontBlocked();

        case BACKWARD:
        case BACKWARD_LEFT:
        case BACKWARD_RIGHT:
            return !isRearBlocked();

        case LEFT:
        case RIGHT:
        case STOP:
        case ROBOT_RESET:
        default:
            return true;  // Side movements and stop are always safe
    }
}

bool SafetySystem::isFrontBlocked() const {
    return (frontLeftDistance < COLLISION_DISTANCE) ||
           (frontRightDistance < COLLISION_DISTANCE);
}

bool SafetySystem::isRearBlocked() const {
    return (rearLeftDistance < COLLISION_DISTANCE) ||
           (rearRightDistance < COLLISION_DISTANCE);
}