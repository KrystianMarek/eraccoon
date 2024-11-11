//
// Created by Krystian Marek on 10/11/2024.
//

#include "MyLCD.h"

MyLCD::MyLCD() {
    lcd = new DFRobot_RGBLCD1602(0x2D, 16, 2);
    ticker = new Ticker(25);
    lcd->init();
    lcd->clear();
    lcd->setRGB(colorR, colorG, colorB);
}

void MyLCD::print(String str) {
    if (ticker->tick()) {
        lcd->setCursor(0, 1);
        lcd->print(str.c_str());
    }
}