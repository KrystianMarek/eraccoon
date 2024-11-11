//
// Created by Krystian Marek on 10/11/2024.
//
#include "SerialLogger.h"

SerialLogger::SerialLogger() {
    this->ticker = new Ticker(100);
    Serial.begin(115200);
}

void SerialLogger::print(const String& message) const {
    if (this->ticker->tick()) {
        Serial.print(message);
    }
}

void SerialLogger::println(const String& message) const {
    if (this->ticker->tick()) {
        Serial.println(message);
    }
}
