#!/usr/bin/env bash

rsync -ar arduino "${ER_SSH_USER}@${ER_JETSON_IP}:~/"
