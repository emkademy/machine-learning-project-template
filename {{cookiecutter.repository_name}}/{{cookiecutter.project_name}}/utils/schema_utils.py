from typing import Optional


def ensure_valid_parameter_value(
    parameter_name: str,
    current_parameter_value: Optional[str],
    allowed_parameter_values: set[str],
    can_be_none: bool = False,
) -> None:
    if current_parameter_value is None and can_be_none:
        return
    if current_parameter_value not in allowed_parameter_values:
        raise ValueError(f"'{parameter_name}' parameter can only be one of: {allowed_parameter_values}")
