//
// Created by Krystian Marek on 11/11/2024.
//

#ifndef PAD_H
#define PAD_H


#include <ArduinoBLE.h>
#include <Ticker.h>
#include <Arduino.h>
#include <format.h>
#include <SerialLogger.h>

class Pad {
    public:
        Pad(SerialLogger *logger, const String &address);
        void connect();

    private:
        Ticker *tickerScan;
        boolean connected = false;
        String address;
        BLEDevice device;
        SerialLogger *logger;

        void explorerPeripheral(BLEDevice peripheral);
        void exploreService(BLEService service);
        void exploreCharacteristic(BLECharacteristic characteristic);
        void exploreDescriptor(BLEDescriptor descriptor);
        void printData(const unsigned char data[], int length);
};



#endif //PAD_H
