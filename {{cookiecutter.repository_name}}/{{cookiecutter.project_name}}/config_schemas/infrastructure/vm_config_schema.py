import dataclasses
import typing as t

from dataclasses import field
from enum import Enum

from hydra.core.config_store import ConfigStore
from omegaconf import MISSING, SI
from pydantic.dataclasses import dataclass


class VMMode(Enum):
    STANDARD = "STANDARD"
    SPOT = "SPOT"
    PREEMPTIBLE = "PREEMPTIBLE"


@dataclass
class MachineConfig:
    machine_type: str
    accelerator_count: int
    accelerator_type: str
    train_machine_mode: VMMode = VMMode.SPOT


@dataclass
class VMTemplateConfig:
    defaults: list[t.Any] = field(default_factory=lambda: [{"machine": "v100_x1"}])

    project_id: str = SI("${infrastructure.project_id}")
    machine: MachineConfig = MISSING
    disk_image_name: str = MISSING
    disk_image_project_id: str = SI("${infrastructure.project_id}")
    disks: list[str] = field(default_factory=lambda: [])
    labels: dict[str, str] = SI("${job_info.labels}")
    docker_image_tag: str = MISSING
    startup_script_path: str = "scripts/vm_startup/training_startup_script.sh"
    boot_disk_name: str = "{{cookiecutter.project_name}}-boot-disk"
    disk_size_gb: int = 250
    node_count: int = 1
    scopes: list[str] = dataclasses.field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/cloud.useraccounts.readonly",
            "https://www.googleapis.com/auth/cloudruntimeconfig",
        ]
    )
    network: str = "https://www.googleapis.com/compute/v1/projects/{{cookiecutter.project_name}}/global/networks/default"
    subnetwork: str = "https://www.googleapis.com/compute/v1/projects/{{cookiecutter.project_name}}/regions/{{cookiecutter.gcp_region}}/subnetworks/default"


def setup_config() -> None:
    cs = ConfigStore.instance()
    cs.store(group="infrastructure/vm_config", name="vm_template_schema", node=VMTemplateConfig)
    cs.store(group="infrastructure/vm_config/machine", name="machine_schema", node=MachineConfig)
