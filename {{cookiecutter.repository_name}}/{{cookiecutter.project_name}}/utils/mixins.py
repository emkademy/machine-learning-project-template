from typing import Any


class DictExpansionMixin:
    def keys(self) -> list[str]:
        return [key for key in self.__dict__ if not key.startswith("__")]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
