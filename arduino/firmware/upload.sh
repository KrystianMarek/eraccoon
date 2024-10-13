#!/usr/bin/env bash

set -v

rsync -ar .pio/build/giga "${ER_SSH_USER}@${ER_JETSON_IP}:~/"
ssh "${ER_SSH_USER}@${ER_JETSON_IP}" "arduino-cli -b arduino:mbed_giga:giga -p /dev/ttyACM0 upload -i ~/giga/firmware.elf"