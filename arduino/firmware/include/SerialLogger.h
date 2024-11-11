//
// Created by Krystian Marek on 10/11/2024.
//

#ifndef SERIALLOGGER_H
#define SERIALLOGGER_H

#include <Arduino.h>
#include <Ticker.h>


class SerialLogger {
  public :
    SerialLogger();
    void println(const String &message) const;
    void print(const String& message) const;

  private:
    Ticker *ticker;

};

#endif //SERIALLOGGER_H