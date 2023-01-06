import argparse

from {{cookiecutter.project_name}}.utils.config_utils import compose_config, config_args_parser, create_final_config


def generate_final_config(args: argparse.Namespace) -> None:
    config_path = args.config_path
    config_name = args.config_name
    overrides = args.overrides

    config = compose_config(config_path=config_path, config_name=config_name, overrides=overrides, to_object=False)
    create_final_config(config)


if __name__ == "__main__":
    generate_final_config(config_args_parser())
