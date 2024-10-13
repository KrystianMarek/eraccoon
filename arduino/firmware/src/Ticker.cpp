//
// Created by Krystian Marek on 13/10/2024.
//

#include "Ticker.h"

Ticker::Ticker(unsigned long updateEveryMillis) {
  this->updateEveryMillis = updateEveryMillis;
  this->elapsedMillis = 0;
}

bool Ticker::tick() {
  const unsigned long currentTime = millis();
  if (currentTime > this->elapsedMillis + this->updateEveryMillis) {
    this->elapsedMillis = currentTime;
    return true;
  }

  return false;
}