import glob
import os

from safe_del.models import DeleteRequest, ResolvedTargets


_WILDCARD_CHARS = "*?[]"


def resolve_targets(request: DeleteRequest) -> ResolvedTargets:
    matched_paths: list[str] = []
    missing_inputs: list[str] = []
    seen_paths: set[str] = set()

    for target in request.targets:
        expanded_paths = _expand_target(target, request.recursive)
        if not expanded_paths:
            missing_inputs.append(target)
            continue

        for expanded_path in expanded_paths:
            identity = _normalize_identity(expanded_path)
            if identity in seen_paths:
                continue
            seen_paths.add(identity)
            matched_paths.append(expanded_path)

    return ResolvedTargets(matched_paths=matched_paths, missing_inputs=missing_inputs)


def _expand_target(target: str, recursive: bool) -> list[str]:
    if _has_wildcard(target):
        return _expand_glob(target, recursive)
    if os.path.exists(target):
        return [os.path.abspath(target)]
    return []


def _has_wildcard(target: str) -> bool:
    return any(char in target for char in _WILDCARD_CHARS)


def _expand_glob(pattern: str, recursive: bool) -> list[str]:
    search_pattern = pattern
    search_recursive = False

    if recursive:
        if "**" in pattern:
            search_recursive = True
        else:
            search_pattern = _build_recursive_pattern(pattern)
            search_recursive = True

    matches = glob.glob(search_pattern, recursive=search_recursive)
    return [os.path.abspath(match) for match in matches]


def _build_recursive_pattern(pattern: str) -> str:
    anchor, relative_pattern = _split_glob_anchor(pattern)
    if relative_pattern == "":
        return os.path.join(anchor, "**")
    return os.path.join(anchor, "**", relative_pattern)


def _split_glob_anchor(pattern: str) -> tuple[str, str]:
    normalized = pattern.replace("/", os.sep)
    drive, tail = os.path.splitdrive(normalized)
    root = ""

    if tail.startswith(("\\", "/")):
        root = os.sep
        tail = tail.lstrip("\\/")

    parts = [part for part in tail.split(os.sep) if part != ""]
    anchor_parts: list[str] = []
    relative_parts: list[str] = []
    wildcard_seen = False

    for part in parts:
        if not wildcard_seen and not _has_wildcard(part):
            anchor_parts.append(part)
            continue
        wildcard_seen = True
        relative_parts.append(part)

    anchor = drive + root
    if anchor_parts:
        if anchor == "":
            anchor = os.path.join(*anchor_parts)
        else:
            anchor = os.path.join(anchor, *anchor_parts)
    if anchor == "":
        anchor = "."

    relative_pattern = ""
    if relative_parts:
        relative_pattern = os.path.join(*relative_parts)

    return anchor, relative_pattern


def _normalize_identity(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))
