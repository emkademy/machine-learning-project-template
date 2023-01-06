from typing import Literal
import pytest


@pytest.fixture
def two() -> Literal[2]:
    return 2
