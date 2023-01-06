variable "username" {
  type = string
}

packer {
  required_plugins {
    googlecompute = {
      version = ">= 0.0.1"
      source  = "github.com/hashicorp/googlecompute"
    }
  }
}

source "googlecompute" "{{cookiecutter.project_name}}-debian-nvidia-cu113" {
  project_id              = "{{cookiecutter.gcp_project_id}}"
  source_image            = "common-cu113-v20220316-debian-10"
  source_image_family     = "common-cu113-debian-10"
  source_image_project_id = ["deeplearning-platform-release"]
  image_name              = "{{cookiecutter.project_name}}-debian-nvidia-cu113"
  image_family            = "{{cookiecutter.project_name}}"
  image_description       = "Basic image with NVIDIA drivers"
  image_labels = {
    user    = var.username
    project = "{{cookiecutter.project_name}}"
  }
  image_storage_locations = ["{{cookiecutter.gcp_image_storage_location}}"]
  ssh_username            = var.username
  on_host_maintenance     = "TERMINATE"
  accelerator_type        = "projects/{{cookiecutter.gcp_project_id}}/zones/{{cookiecutter.gcp_zone}}/acceleratorTypes/nvidia-tesla-t4"
  accelerator_count       = 1
  disk_name               = "{{cookiecutter.project_name}}-debian-nvidia-cu113"
  disk_size               = 50
  disk_type               = "pd-ssd"
  instance_name           = "{{cookiecutter.project_name}}-debian-nvidia-cu113-image-creation"
  labels = {
    user    = var.username
    project = "{{cookiecutter.project_name}}"
  }
  machine_type = "n1-standard-2"
  zone         = "{{cookiecutter.gcp_zone}}"
  region       = "{{cookiecutter.gcp_region}}"
  scopes = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/cloud.useraccounts.readonly",
    "https://www.googleapis.com/auth/cloudruntimeconfig"
  ]
  startup_script_file = "./scripts/vm_startup/{{cookiecutter.project_name}}_gcp_image_creation_startup_script.sh"
}

build {
  sources = ["sources.googlecompute.{{cookiecutter.project_name}}-debian-nvidia-cu113"]
}

