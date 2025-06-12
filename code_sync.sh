#!/usr/bin/env bash

set -ex

rsync -ar --progress arduino jetson \
  --exclude jetson/remote/.idea \
  --exclude jetson/remote/.venv \
  --exclude jetson/multiplexer/.venv \
  "${ER_SSH_USER}@${ER_JETSON_IP}:~/eraccoon"
