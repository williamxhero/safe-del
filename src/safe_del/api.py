from safe_del.models import DeleteRequest, DeleteResult
from safe_del.resolver import resolve_targets
from safe_del.service import move_to_trash


def delete_targets(targets: list[str], recursive: bool = False) -> DeleteResult:
    request = DeleteRequest(targets=targets, recursive=recursive, quiet=False)
    resolved_targets = resolve_targets(request)
    return move_to_trash(resolved_targets)
