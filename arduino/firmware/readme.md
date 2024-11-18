# board

- [documentation](https://docs.arduino.cc/hardware/giga-r1-wifi/)
- [schematic](chrome-extension://efaidnbmnnnibpcajpcglclefindmkaj/https://docs.arduino.cc/resources/schematics/ABX00063-schematics.pdf)

## radio
Murata LBEE5KL1DX-883  
Infineon CYW4343W Chipset for 802.11b/g/n + Bluetooth  

[datasheet](https://www.murata.com/products/productdata/8813651165214/type1dx.pdf) 
> That's true, Bluetooth Classic is currently not supported by the official Arduino libraries
> but is present in hardware.  
[issue](https://forum.arduino.cc/t/bluetooth-classic-on-giga-r1/1110561)

[Cypress Linux WiFi Driver](https://community.infineon.com/t5/Knowledge-Base-Articles/Cypress-Linux-WiFi-Driver-Release-FMAC-2020-06-25/ta-p/252500)

libraries 
- [ArduinoBLE](https://docs.arduino.cc/libraries/arduinoble/)
- [ps5](https://github.com/felis/USB_Host_Shield_2.0?tab=readme-ov-file#ps5-library)
- [dualsense](https://github.com/yesbotics/dualsense-controller-arduino/tree/main)

###  enabling bluetooth classic  

- https://community.infineon.com/t5/AIROC-Bluetooth/Classic-bluetooth-api-using-cyw4343w-in-LAIRD-EWB/td-p/357523
- https://github.com/Infineon/btstack
- [cortex m7 wiced dualmode](https://github.com/Infineon/btstack/tree/master/stack/COMPONENT_WICED_DUALMODE/COMPONENT_CM7)

# Development
Switched to PlatformIO + clion.  
There is an [issue](https://github.com/platformio/platform-ststm32/issues/702) with my board on this platform.

Code is compiled on mac, then rsynced to the jetson, and from there uploaded to Arduino.

## build
```shell
pio run
```

# serial console
```shell
minicom -b 115200 -o -D /dev/ttyACM0
```

# ToDo
- connect ps5 | dualsense pad  
  via usb dongle:  
  https://github.com/felis/USB_Host_Shield_2.0?tab=readme-ov-file#ps5-library  
  https://docs.arduino.cc/tutorials/giga-r1-wifi/giga-usb/  