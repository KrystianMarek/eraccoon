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

    private:
        Ticker *ticker;
        DFRobot_RGBLCD1602 *lcd;
        int colorR = 0;
        int colorG = 128;
        int colorB = 0;
};



#endif //LCD_H
