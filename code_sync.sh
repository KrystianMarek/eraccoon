#!/usr/bin/env bash

set -ex

rsync -ar --progress arduino jetson \
  --exclude jetson/remote/.idea \
  --exclude jetson/remote/.venv \
  --exclude jetson/multiplexer/.venv \
  --exclude jetson/multiplexer/motor-controller-proxy-latest.tar \
  --exclude jetson/remote/remote-control-service-latest.tar \
  "${ER_SSH_USER}@${ER_JETSON_IP}:~/eraccoon"
