import os
import typing as t

from dataclasses import field

from hydra.core.config_store import ConfigStore
from omegaconf import MISSING, SI
from pydantic.dataclasses import dataclass

from {{cookiecutter.project_name}}.config_schemas.infrastructure import vm_config_schema
from {{cookiecutter.project_name}}.config_schemas.infrastructure.job_info_schema import JobInfo
from {{cookiecutter.project_name}}.config_schemas.infrastructure.vm_config_schema import VMTemplateConfig


@dataclass
class InfrastructureConfig:
    defaults: list[t.Any] = field(default_factory=lambda: [{"vm_config": "default"}])

    project_id: str = "{{cookiecutter.gcp_project_id}}"
    zone: str = "{{cookiecutter.gcp_zone}}"
    vm_config: VMTemplateConfig = MISSING
    job_info: JobInfo = SI("${job_info}")
    gcs_bucket: str = "gs://{{cookiecutter.project_name}}"
    python_hash_seed: int = 42

    def base_path(self) -> str:
        return os.path.join(
            self.gcs_bucket, "tasks", self.job_info.task_id, self.job_info.experiment_name, self.job_info.run_name
        )


def setup_config() -> None:
    cs = ConfigStore.instance()
    cs.store(group="infrastructure", name="infrastructure_schema", node=InfrastructureConfig)

    vm_config_schema.setup_config()
