//
// Created by Krystian Marek on 14/10/2024.
//

#ifndef DISTANCESENSORS_H
#define DISTANCESENSORS_H

#include <Arduino.h>
#include <Ticker.h>


class DistanceSensors {
  public:
    DistanceSensors();
    bool frontCollison();
    bool rearCollison();
    void checkDistance();

    // Getters for distance values
    int getFrontLeftDistance() { return distance_fl; }
    int getFrontRightDistance() { return distance_fr; }
    int getRearLeftDistance() { return distance_rl; }
    int getRearRightDistance() { return distance_rr; }

  private:
    Ticker *ticker;
    const float distance_constant = 0.0048828125;
    const int colissionDistance = 7;
    int distance_fl;
    int distance_fr;
    int distance_rl;
    int distance_rr;
};

#endif //DISTANCESENSORS_H
