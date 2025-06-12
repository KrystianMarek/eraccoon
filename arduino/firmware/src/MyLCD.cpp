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
    lastUpdate = millis();
}

void MyLCD::print(String str) {
    lcd->print(str.c_str());
}

void MyLCD::print(const char* str) {
    lcd->print(str);
}

void MyLCD::clear() {
    lcd->clear();
}

void MyLCD::setCursor(int col, int row) {
    lcd->setCursor(col, row);
}

void MyLCD::setColor(int r, int g, int b) {
    colorR = r;
    colorG = g;
    colorB = b;
    lcd->setRGB(r, g, b);
}