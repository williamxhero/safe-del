import os
import shutil

from safe_del.models import DeleteFailure, TrashCleanResult


def empty_trash() -> TrashCleanResult:
    trash_roots = resolve_trash_roots()
    deleted_count, failures = clean_trash_roots(trash_roots)
    cleaned_roots = [trash_root for trash_root in trash_roots if os.path.exists(trash_root)]
    return TrashCleanResult(cleaned_roots=cleaned_roots, deleted_count=deleted_count, failures=failures)


def resolve_trash_roots() -> list[str]:
    user_id = os.getuid()
    candidates = [resolve_home_trash_root()]

    for mount_point in resolve_mount_points():
        candidates.append(os.path.join(mount_point, f".Trash-{user_id}"))
        candidates.append(os.path.join(mount_point, ".Trash", str(user_id)))

    roots: list[str] = []
    seen_roots: set[str] = set()
    for candidate in candidates:
        root = os.path.abspath(candidate)
        identity = os.path.normcase(os.path.normpath(root))
        if identity in seen_roots:
            continue
        seen_roots.add(identity)
        roots.append(root)

    return roots


def resolve_home_trash_root() -> str:
    data_home = os.environ.get("XDG_DATA_HOME", "")
    if data_home == "":
        data_home = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(data_home, "Trash")


def resolve_mount_points() -> list[str]:
    mountinfo_path = "/proc/self/mountinfo"
    if not os.path.exists(mountinfo_path):
        return ["/"]

    mount_points: list[str] = []
    with open(mountinfo_path, "r", encoding="utf-8", errors="replace") as file:
        for line in file:
            mount_point = parse_mountinfo_mount_point(line)
            if mount_point == "":
                continue
            mount_points.append(mount_point)
    return mount_points


def parse_mountinfo_mount_point(line: str) -> str:
    fields = line.split(" ")
    if len(fields) < 5:
        return ""
    return decode_mountinfo_path(fields[4])


def decode_mountinfo_path(value: str) -> str:
    result = ""
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 3 < len(value):
            code = value[index + 1 : index + 4]
            if code.isdigit():
                result += chr(int(code, 8))
                index += 4
                continue
        result += char
        index += 1
    return result


def clean_trash_roots(trash_roots: list[str]) -> tuple[int, list[DeleteFailure]]:
    deleted_count = 0
    failures: list[DeleteFailure] = []

    for trash_root in trash_roots:
        if not os.path.isdir(trash_root):
            continue

        files_count, files_failures = clean_trash_child_directory(os.path.join(trash_root, "files"))
        info_count, info_failures = clean_trash_child_directory(os.path.join(trash_root, "info"))
        deleted_count += files_count + info_count
        failures.extend(files_failures)
        failures.extend(info_failures)

    return deleted_count, failures


def clean_trash_child_directory(directory: str) -> tuple[int, list[DeleteFailure]]:
    if not os.path.isdir(directory):
        return 0, []

    deleted_count = 0
    failures: list[DeleteFailure] = []
    for entry in os.scandir(directory):
        try:
            delete_trash_entry(entry.path)
            deleted_count += 1
        except OSError as exc:
            failures.append(DeleteFailure(path=entry.path, message=str(exc)))
    return deleted_count, failures


def delete_trash_entry(path: str) -> None:
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
        return
    os.unlink(path)
