import logging

from typing import TYPE_CHECKING

from hydra.utils import instantiate

from {{cookiecutter.project_name}}.training.data_modules import DataModule
from {{cookiecutter.project_name}}.utils.config_utils import get_pickle_config, instantiate_trainer, setup_logger
from {{cookiecutter.project_name}}.utils.io_utils import is_file

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from {{cookiecutter.project_name}}.config_schemas.config_schema import Config


@get_pickle_config(config_path="{{cookiecutter.project_name}}/configs/automatically_generated/", config_name="config")
def train(config: "Config") -> None:
    setup_logger()


if __name__ == "__main__":
    train()
