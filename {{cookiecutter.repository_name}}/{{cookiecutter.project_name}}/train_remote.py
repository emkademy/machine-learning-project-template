from typing import TYPE_CHECKING

from {{cookiecutter.project_name}}.utils.config_utils import get_pickle_config, setup_logger
from {{cookiecutter.project_name}}.utils.gcp_training_launcher import DistributedJobLauncher

if TYPE_CHECKING:
    from {{cookiecutter.project_name}}.config_schemas.config_schema import Config


@get_pickle_config(config_path="{{cookiecutter.project_name}}/configs/automatically_generated/", config_name="config")
def run(config: "Config") -> None:
    setup_logger()
    launcher = DistributedJobLauncher(config.infrastructure.project_id, config.infrastructure.zone)
    training_info = launcher.run_remote_training(config.infrastructure)
    training_info.print_job_info()


if __name__ == "__main__":
    run()  # type: ignore
