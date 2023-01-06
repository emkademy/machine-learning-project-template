import json
import os

from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Union

from fsspec import AbstractFileSystem, filesystem

from {{cookiecutter.project_name}}.utils.utils import get_logger

GCS_PREFIX = "gs://"
GCS_FILE_SYSTEM_NAME = "gcs"
LOCAL_FILE_SYSTEM_NAME = "file"
TMP_FILE_PATH = "/tmp/translated"


def choose_file_system(path: str) -> AbstractFileSystem:
    path = str(path)
    return filesystem(GCS_FILE_SYSTEM_NAME) if path.startswith(GCS_PREFIX) else filesystem(LOCAL_FILE_SYSTEM_NAME)


def open_file(path: str, mode: str = "r") -> Any:
    file_system = choose_file_system(path)
    return file_system.open(path, mode)


def write_file(path: str, mode: str, callback: Callable[[Union[str, StringIO, BytesIO]], None]) -> None:
    if mode == "w":
        io = StringIO()
    elif mode == "wb":
        io = BytesIO()  # type: ignore
    else:
        raise RuntimeError("'mode' parameter can be one of: {'w', 'wb'}")

    try:
        callback(io)
    except TypeError:
        with TemporaryDirectory() as tmp_dir_name:
            tmp_file_name = os.path.join(tmp_dir_name, "tmp_file")
            callback(tmp_file_name)

            with open(tmp_file_name, mode.replace("w", "r")) as temp_f:
                io.write(temp_f.read())

    with open_file(path, mode) as f:
        f.write(io.getvalue())


def read_file(path: str, mode: str) -> Union[str, bytes]:
    allowed_modes = {"r", "rb"}
    if mode not in allowed_modes:
        raise RuntimeError(f"'mode' parameter can be one of: {allowed_modes}")

    with open_file(path, mode) as f:
        data = f.read()

    return data  # type: ignore


def is_dir(path: str) -> bool:
    file_system = choose_file_system(path)
    is_dir: bool = file_system.isdir(path)
    return is_dir


def is_file(path: str) -> bool:
    file_system = choose_file_system(path)
    is_file: bool = file_system.isfile(path)
    return is_file


def is_path_exist(path: str) -> bool:
    filesystem = choose_file_system(path)
    exist: bool = filesystem.exists(path)
    return exist


def make_dirs(path: str) -> None:
    file_system = choose_file_system(path)
    file_system.makedirs(path, exist_ok=True)


def list_paths(data_path: str, check_path_suffix: bool = False, path_suffix: str = ".csv") -> list[str]:
    file_system = choose_file_system(data_path)
    if not file_system.isdir(data_path):
        return []
    paths: list[str] = file_system.ls(data_path)
    if check_path_suffix:
        paths = [path for path in paths if path.endswith(path_suffix)]
    if GCS_FILE_SYSTEM_NAME in file_system.protocol:
        gs_paths: list[str] = [GCS_PREFIX + file_path for file_path in paths]
        return gs_paths
    else:
        return paths


def copy_dir(source_dir: str, target_dir: str) -> None:
    logger = get_logger(Path(__file__).name)
    logger.info(f"Copying dir {source_dir} to {target_dir}")
    if not is_dir(target_dir):
        make_dirs(target_dir)
    source_files = list_paths(source_dir)
    for source_file in source_files:
        target_file = os.path.join(target_dir, os.path.basename(source_file))
        if is_file(source_file):
            with open_file(source_file, mode="rb") as source, open_file(target_file, mode="wb") as target:
                content = source.read()
                target.write(content)
        else:
            raise ValueError(f"Copying supports flat dirs only – failed on {source_file}")


def copy_file(source_file: str, target_path: str) -> None:
    logger = get_logger(Path(__file__).name)
    logger.info(f"Copying file from {source_file} to {target_path}")
    with open_file(source_file, mode="rb") as source, open_file(target_path, mode="wb") as target:
        content = source.read()
        target.write(content)


def translate_gcs_dir_to_local(path: str) -> str:
    if path.startswith(GCS_PREFIX):
        path = path.rstrip("/")
        local_path = os.path.join(TMP_FILE_PATH, os.path.split(path)[-1])
        if not os.path.isdir(local_path):
            os.makedirs(local_path)
        copy_dir(path, local_path)
        return local_path
    return path


def translate_gcs_file_to_local(path: str) -> str:
    if path.startswith(GCS_PREFIX):
        path = path.rstrip("/")
        local_path = os.path.join(TMP_FILE_PATH, os.path.basename(path))
        if os.path.exists(local_path):
            return local_path

        if not os.path.isdir(TMP_FILE_PATH):
            os.makedirs(TMP_FILE_PATH)
        copy_file(path, local_path)
        return local_path

    return path


def load_json(path: str) -> dict[str, Any]:
    data = read_file(path, "r")
    return json.loads(data)
