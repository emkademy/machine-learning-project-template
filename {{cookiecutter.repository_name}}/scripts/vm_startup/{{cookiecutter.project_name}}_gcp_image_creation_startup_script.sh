#!/usr/bin/env bash

CURRENT_DOCKER_IMAGE_URL="${GCP_DOCKER_IMAGE_NAME}:v1"

apt-get update && apt-get install -y linux-headers-4.19.0-20-cloud-amd64

/opt/deeplearning/install-driver.sh
gcloud auth configure-docker --quiet

# Pull docker image
time docker pull "${CURRENT_DOCKER_IMAGE_URL}"
