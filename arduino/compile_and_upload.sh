#!/usr/bin/env bash

set -e

#arduino-cli compile -b arduino:mbed_giga:giga ~/arduino/firmware
#sudo arduino-cli upload ~/arduino/firmware -b arduino:mbed_giga:giga -p /dev/ttyACM0 -t -v

# https://github.com/platformio/platform-ststm32/issues/702
#pio run

arduino-cli -b arduino:mbed_giga:giga -p /dev/ttyACM0 upload -i .pio/build/giga/firmware.elf