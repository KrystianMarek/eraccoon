#!/usr/bin/env bash

rsync -ar arduino jetson-dualsense \
  --exclude jetson-dualsense/.idea \
  --exclude jetson-dualsense/.venv \
  "${ER_SSH_USER}@${ER_JETSON_IP}:~/"
