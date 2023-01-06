#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
echo "TRAINING: Startup script location ${DIR}"

export NCCL_ASYNC_ERROR_HANDLING=1
export GCP_LOGGING_ENABLED="TRUE"

JOB_ID=$(curl --silent http://metadata.google.internal/computeMetadata/v1/instance/attributes/job_id -H "Metadata-Flavor: Google")
TASK_ID=$(curl --silent http://metadata.google.internal/computeMetadata/v1/instance/attributes/task_id -H "Metadata-Flavor: Google")
CLUSTER_ID=$(curl --silent http://metadata.google.internal/computeMetadata/v1/instance/attributes/cluster_id -H "Metadata-Flavor: Google")
GCP_DOCKER_REGISTRY_URL=$(curl --silent http://metadata.google.internal/computeMetadata/v1/instance/attributes/gcp_docker_registry_url -H "Metadata-Flavor: Google")
NODE_COUNT=$(curl --silent http://metadata.google.internal/computeMetadata/v1/instance/attributes/node_count -H "Metadata-Flavor: Google")

CUSTOM_PYTHONHASHSEED=$(curl --silent --fail http://metadata.google.internal/computeMetadata/v1/instance/attributes/python_hash_seed -H "Metadata-Flavor: Google" || echo "42")

ZONE=$(curl --silent http://metadata.google.internal/computeMetadata/v1/instance/attributes/zone -H "Metadata-Flavor: Google")
BASE_PATH=$(curl --silent http://metadata.google.internal/computeMetadata/v1/instance/attributes/base_path -H "Metadata-Flavor: Google")

echo '=========== Training: downloading docker image ============'
gcloud auth configure-docker --quiet {{cookiecutter.gcp_docker_registry}}-docker.pkg.dev
time docker pull "${GCP_DOCKER_REGISTRY_URL}"

echo '=========== TRAINING: start  ============'
docker run --init --rm --gpus all --ipc host --user root --hostname "$(hostname)" --privileged \
  --log-driver=gcplogs -v /mnt:/mnt:ro \
  -e BASE_PATH="${BASE_PATH}" \
  -e PYTHONHASHSEED="${CUSTOM_PYTHONHASHSEED}" \
  ${GCP_DOCKER_REGISTRY_URL} \
  python -u -m {{cookiecutter.project_name}}.train ||
  (echo '=========== TRAINING: job failed ============')

echo '=========== EVALUATION: start  ============'
docker run --init --rm --gpus all --ipc host --user root --hostname "$(hostname)" --privileged \
  --log-driver=gcplogs -v /mnt:/mnt:ro \
  -e BASE_PATH="${BASE_PATH}" \
  -e PYTHONHASHSEED="${CUSTOM_PYTHONHASHSEED}" \
  ${GCP_DOCKER_REGISTRY_URL} \
  python -u -m {{cookiecutter.project_name}}.evaluate ||
  (echo '=========== EVALUATION: job failed ============')

echo -e "\n\n================= TRAINING: cleanning stage ================"
sleep 5
INSTANCE_NAME=$(hostname)
CLUSTER_SIZE=$(gcloud compute instance-groups managed describe "${CLUSTER_ID}" --zone "${ZONE}" --format="text(targetSize)" | cut -d' ' -f2)
echo "TRAINING: ${INSTANCE_NAME}: current cluster ${CLUSTER_ID} size is ${CLUSTER_SIZE}"

if [[ $CLUSTER_SIZE -lt 2 ]]; then
  echo "TRAINING: Deleting instance group ${CLUSTER_ID}"
  gcloud compute instance-groups managed delete --quiet "${CLUSTER_ID}" --zone "${ZONE}"
else
  echo "TRAINING: deleting instance ${INSTANCE_NAME} from cluster ${CLUSTER_ID}"
  gcloud compute instance-groups managed delete-instances "${CLUSTER_ID}" --instances="${INSTANCE_NAME}" --zone "${ZONE}"
  sleep 5

  echo "TRAINING: to be really sure deleting instance ${INSTANCE_NAME} from cluster ${CLUSTER_ID} again"
  gcloud compute instance-groups managed delete-instances "${CLUSTER_ID}" --instances="${INSTANCE_NAME}" --zone "${ZONE}"
fi
