//
// Created by Krystian Marek on 13/10/2024.
//

#ifndef TICKER_H
#define TICKER_H

#include <Arduino.h>

class Ticker {
  public:
    explicit Ticker(unsigned long updateEveryMillis);
    bool tick();


  private:
    unsigned long updateEveryMillis;
    unsigned long elapsedMillis;
};



#endif //TICKER_H
