#pragma once

#include "Arduino.h"
#include "MotorController.h"

class SafetySystem {
private:
    int frontLeftPin;
    int frontRightPin;
    int rearLeftPin;
    int rearRightPin;

    int frontLeftDistance;
    int frontRightDistance;
    int rearLeftDistance;
    int rearRightDistance;

    const int COLLISION_DISTANCE = 7;  // cm
    const float DISTANCE_CONSTANT = 0.0048828125;  // 5V/1024

    void updateDistances();

public:
    SafetySystem(int frontLeftPin, int frontRightPin, int rearLeftPin, int rearRightPin);

    // Core safety checks
    bool isMovementSafe(MotionDirection direction) const;
    void update();

    // Sensor readings
    int getFrontLeftDistance() const { return frontLeftDistance; }
    int getFrontRightDistance() const { return frontRightDistance; }
    int getRearLeftDistance() const { return rearLeftDistance; }
    int getRearRightDistance() const { return rearRightDistance; }

    // Collision states
    bool isFrontBlocked() const;
    bool isRearBlocked() const;
};