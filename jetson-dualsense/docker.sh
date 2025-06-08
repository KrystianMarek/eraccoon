#!/usr/bin/env bash

image_name="jetson-dualsense"

docker build -t "${image_name}" ./
docker save "${image_name}" -o "build/${image_name}.tar"