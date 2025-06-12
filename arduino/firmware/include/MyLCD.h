//
// Created by Krystian Marek on 10/11/2024.
//

#ifndef LCD_H
#define LCD_H

#include <Arduino.h>
#include <Ticker.h>
#include "DFRobot_RGBLCD1602.h"


class MyLCD {
    public:
        MyLCD();
        void print(String str);
        void print(const char* str);
        void clear();
        void setCursor(int col, int row);
        void setColor(int r, int g, int b);

    private:
        Ticker *ticker;
        DFRobot_RGBLCD1602 *lcd;
        int colorR = 0;
        int colorG = 128;
        int colorB = 0;
        unsigned long lastUpdate = 0;
        static const unsigned long UPDATE_INTERVAL = 100; // Min 100ms between updates
};



#endif //LCD_H
