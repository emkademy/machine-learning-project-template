import argparse
import importlib
import logging.config
import os
import pickle
import sys

from dataclasses import asdict
from functools import partial
from io import BytesIO, StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

import hydra
import yaml

from hydra import compose, initialize
from hydra.types import TaskFunction
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf

from {{cookiecutter.project_name}}.config_schemas import config_schema
from {{cookiecutter.project_name}}.config_schemas.trainer.trainer_schema import TrainerConfig
from {{cookiecutter.project_name}}.utils.io_utils import open_file
from {{cookiecutter.project_name}}.utils.utils import get_logger

CONFIG_UTILS_LOGGER = get_logger(Path(__file__).name)


if TYPE_CHECKING:
    from {{cookiecutter.project_name}}.config_schemas.config_schema import Config


def get_config(
    config_path: str, config_name: str
) -> Callable[[TaskFunction], Callable[[Optional[dict[Any, Any]]], None]]:
    setup_config()
    setup_logger()

    def main_decorator(task_function: TaskFunction) -> Callable[[Optional[dict[Any, Any]]], None]:
        @hydra.main(config_path=config_path, config_name=config_name, version_base=None)
        def decorated_main(dict_config: Optional[dict[Any, Any]] = None) -> None:
            config = OmegaConf.to_object(dict_config)
            task_function(config)

        return decorated_main  # type: ignore

    return main_decorator


def get_pickle_config(config_path: str, config_name: str) -> Callable[[TaskFunction], Callable[[], None]]:
    setup_config()
    setup_logger()

    def main_decorator(task_function: TaskFunction) -> Callable[[], None]:
        def decorated_main() -> None:
            config = load_pickle_config(config_path, config_name)
            task_function(config)

        return decorated_main

    return main_decorator


def create_final_config(config: DictConfig) -> None:
    config_save_dir = Path("./{{cookiecutter.project_name}}/configs/automatically_generated/")
    prepare_config_dir(config_save_dir)

    pickle_config_save_path = config_save_dir / "config.pickle"
    CONFIG_UTILS_LOGGER.info(f"Saving automatically generated config to {pickle_config_save_path}")

    config_object = OmegaConf.to_object(config)
    save_config_as_pickle(config_object, pickle_config_save_path)  # type: ignore

    yaml_config_save_path = config_save_dir / "config.yaml"
    save_config_as_yaml(config_object, yaml_config_save_path)  # type: ignore


def prepare_config_dir(config_save_dir: Path) -> None:
    config_save_dir.mkdir(parents=True, exist_ok=True)
    create_init_py(config_save_dir)
    create_gitignore(config_save_dir)


def create_init_py(config_save_dir: Path) -> None:
    (config_save_dir / "__init__.py").touch(exist_ok=True)


def create_gitignore(config_save_dir: Path) -> None:
    (config_save_dir / ".gitignore").write_text(f"# Generated automatically by {sys.argv[0]}\n*\n")


def load_pickle_config(config_path: str, config_name: str) -> "Config":
    with open_file(os.path.join(config_path, f"{config_name}.pickle"), "rb") as f:
        config: "Config" = pickle.load(f)
    return config


def config_args_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--config-path", type=str, default="../configs/", help="Directory of the config")
    parser.add_argument("--config-name", type=str, default="config", help="Name of the config")
    parser.add_argument("--overrides", nargs="*", help="Hydra config overrides", default=[])
    return parser.parse_args()


def compose_config(
    config_path: str, config_name: str, overrides: Optional[list[str]] = None, to_object: bool = True
) -> Any:
    setup_config()
    setup_logger()
    if overrides is None:
        overrides = []
    with initialize(version_base=None, config_path=config_path, job_name="config-compose"):
        config = compose(config_name=config_name, overrides=overrides)
        if to_object:
            config = OmegaConf.to_object(config)  # type: ignore
    return config


def setup_config() -> None:
    config_schema.setup_config()


def setup_logger() -> None:
    with open_file("./{{cookiecutter.project_name}}/configs/hydra/job_logging/custom.yaml", "r") as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    logging.config.dictConfig(config)


def save_config_as_yaml(config: "Config", save_path: str) -> None:
    text_io = StringIO()
    text_io.writelines(
        [
            f"# Do not edit this file. It is automatically generated by {sys.argv[0]}.\n",
            "# If you want to modify configuration, edit source files in {{cookiecutter.project_name}}/configs directory.\n",
            "\n",
        ]
    )

    config_header = load_config_header()
    text_io.write(config_header)
    text_io.write("\n")

    OmegaConf.save(config, text_io, resolve=True)
    with open_file(save_path, "w") as f:
        f.write(text_io.getvalue())


def save_config_as_pickle(config: "Config", save_path: str) -> None:
    bytes_io = BytesIO()
    pickle.dump(config, bytes_io)
    with open_file(save_path, "wb") as f:
        f.write(bytes_io.getvalue())


def load_config_header() -> str:
    with open("./{{cookiecutter.project_name}}/configs/automatically_generated/full_config_header.yaml", "r") as f:
        return f.read()


def remove_attribute_return_as_dict(config: Any, *parameters_to_remove: str) -> dict[str, Any]:
    config_as_dict = asdict(config)
    for parameter_to_remove in parameters_to_remove:
        del config_as_dict[parameter_to_remove]
    return config_as_dict


def custom_instantiate(config: Any) -> Any:
    config_as_dict = asdict(config)
    if "_target_" not in config_as_dict:
        raise ValueError("'config' has to have '_target_' key in order to be instantiated...")

    _target_ = config_as_dict["_target_"]
    _partial_ = config_as_dict.get("_partial_", False)

    config_as_dict.pop("_target_", None)
    config_as_dict.pop("_partial_", None)

    splitted_target = _target_.split(".")
    module_name, class_name = ".".join(splitted_target[:-1]), splitted_target[-1]

    module = importlib.import_module(module_name)
    _class = getattr(module, class_name)
    if _partial_:
        return partial(_class, **config_as_dict)
    return _class(**config_as_dict)