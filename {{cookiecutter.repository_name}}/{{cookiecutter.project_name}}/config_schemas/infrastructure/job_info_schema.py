import getpass
import typing as t

from dataclasses import field

from hydra.core.config_store import ConfigStore
from omegaconf import SI
from pydantic.dataclasses import dataclass

from {{cookiecutter.project_name}}.utils.mixins import DictExpansionMixin


@dataclass
class JobInfo(DictExpansionMixin):
    task_id: str
    experiment_name: str
    run_tag: str = "run"
    run_name: str = SI("${.run_tag}-${now:%Y%m%d%H%M%S}")
    job_id: str = SI("${.experiment_name}-${.run_name}")
    labels: dict[str, str] = field(
        default_factory=lambda: {"env": "dev", "project": "{{cookiecutter.project_name}}", **_get_label_for_launching_user()}
    )
    run_id: t.Optional[str] = None
    experiment_id: t.Optional[str] = None


def _get_label_for_launching_user() -> dict[str, str]:
    launching_user = getpass.getuser()
    if launching_user:
        return {"user": launching_user.replace(".", "-")}
    else:
        return {}


def setup_config() -> None:
    cs = ConfigStore.instance()
    cs.store(group="job_info", name="job_info_schema", node=JobInfo)
