import logging
import re
import socket
import subprocess
import sys

from pathlib import Path
from typing import Union


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"[{socket.gethostname()}] {name}")


def run_shell_command(cmd: str) -> str:
    return subprocess.run(cmd, text=True, shell=True, stdout=sys.stdout, check=True).stdout


def get_latest_filename(file_names: list[str]) -> str:
    file_names.sort(key=lambda x: int(re.sub(r"\D", "", x)))
    return file_names[-1]


def read_lines(text_path: Union[str, Path]) -> list[str]:
    text_path = Path(text_path)
    lines = text_path.read_text().split("\n")

    if not lines[-1]:
        lines = lines[:-1]

    return lines
