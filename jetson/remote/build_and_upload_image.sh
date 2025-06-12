#!/usr/bin/env bash

image_name="eraccoon-remote"

docker build -t "${image_name}" ./
docker save "${image_name}" -o "build/${image_name}.tar"