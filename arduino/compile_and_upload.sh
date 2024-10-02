#!/usr/bin/env bash

set -e

arduino-cli compile -b arduino:mbed_giga:giga ~/arduino/firmware
sudo arduino-cli upload ~/arduino/firmware -b arduino:mbed_giga:giga -p /dev/ttyACM0 -t -v