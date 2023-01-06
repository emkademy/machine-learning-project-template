from typing import Optional

from hydra.core.config_store import ConfigStore
from omegaconf import OmegaConf
from pydantic.dataclasses import dataclass

from {{cookiecutter.project_name}}.config_schemas.infrastructure import infrastructure_schema, job_info_schema
from {{cookiecutter.project_name}}.utils.mixins import DictExpansionMixin


@dataclass
class Config(DictExpansionMixin):
    infrastructure: infrastructure_schema.InfrastructureConfig
    job_info: job_info_schema.JobInfo
    seed: int = 1234

def setup_config() -> None:
    cs = ConfigStore.instance()
    cs.store(name="config_schema", node=Config)

    job_info_schema.setup_config()
    infrastructure_schema.setup_config()
