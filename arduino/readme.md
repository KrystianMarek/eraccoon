Updating arduino directly from jetson via [arduino-cli](https://arduino.github.io/arduino-cli/0.35/)

# Firmware update
**compile**
```shell
arduino-cli compile -b arduino:mbed_giga:giga ~/arduino/firmware
```
**upload**
```shell
sudo arduino-cli upload -b arduino:mbed_giga:giga -p /dev/ttyACM0 ~/arduino/firmware
```
