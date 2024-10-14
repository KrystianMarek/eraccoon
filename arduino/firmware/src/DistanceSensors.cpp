//
// Created by Krystian Marek on 14/10/2024.
//

#include "DistanceSensors.h"

DistanceSensors::DistanceSensors() {
    this->ticker = new Ticker(10);
}

void DistanceSensors::checkDistance() {
    if (this->ticker->tick()) {
        float volts_fl = analogRead(A0)*distance_constant;  // value from sensor * (5/1024)
        float volts_fr = analogRead(A1)*distance_constant;
        float volts_rl = analogRead(A2)*distance_constant;
        float volts_rr = analogRead(A3)*distance_constant;

        distance_fl = 13*pow(volts_fl, -1); // worked out from datasheet graph
        distance_fr = 13*pow(volts_fr, -1);
        distance_rl = 13*pow(volts_rl, -1);
        distance_rr = 13*pow(volts_rr, -1);
    }
}

bool DistanceSensors::frontCollison() {
    checkDistance();
    return (distance_fl < colissionDistance || distance_fr < colissionDistance);
}

bool DistanceSensors::rearCollison() {
    checkDistance();
    return (distance_rl < colissionDistance || distance_rr < colissionDistance);
}