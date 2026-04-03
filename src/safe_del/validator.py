import ntpath
import re
from collections.abc import Sequence


_DRIVE_ONLY_PATTERN = re.compile(r"^[A-Za-z]:$")
_DRIVE_ROOT_PATTERN = re.compile(r"^[A-Za-z]:\\$")
_WILDCARD_CHARS = "*?[]"
_ROOT_WILDCARD_PARTS = {"*", "*.*", "**"}


class DangerousTargetError(ValueError):
    pass


def validate_delete_targets(targets: Sequence[str]) -> None:
    dangerous_targets = [target for target in targets if is_dangerous_target(target)]
    if dangerous_targets:
        joined_targets = ", ".join(dangerous_targets)
        raise DangerousTargetError(
            f"禁止删除整个分区或分区根下全部内容: {joined_targets}"
        )


def is_dangerous_target(target: str) -> bool:
    normalized = normalize_target(target)
    if is_drive_only_target(normalized):
        return True
    if is_drive_root_target(normalized):
        return True
    if has_wildcard(normalized) and is_drive_root_wildcard_target(normalized):
        return True
    return False


def normalize_target(target: str) -> str:
    return target.replace("/", "\\")


def is_drive_only_target(target: str) -> bool:
    return bool(_DRIVE_ONLY_PATTERN.fullmatch(target))


def is_drive_root_target(target: str) -> bool:
    return bool(_DRIVE_ROOT_PATTERN.fullmatch(target))


def has_wildcard(target: str) -> bool:
    return any(char in target for char in _WILDCARD_CHARS)


def is_drive_root_wildcard_target(target: str) -> bool:
    drive, tail = ntpath.splitdrive(target)
    if drive == "" or not tail.startswith("\\"):
        return False

    relative_pattern = tail.lstrip("\\")
    if relative_pattern == "":
        return False

    parts = [part for part in relative_pattern.split("\\") if part != ""]
    if not parts:
        return False

    for part in parts:
        if part not in _ROOT_WILDCARD_PARTS:
            return False

    return True
