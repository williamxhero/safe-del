from safe_del.models import DeleteRequest, DeleteResult
from safe_del.resolver import resolve_targets
from safe_del.service import move_to_trash
from safe_del.validator import validate_delete_targets


def delete_targets(targets: list[str], recursive: bool = False) -> DeleteResult:
    validate_delete_targets(targets)
    request = DeleteRequest(targets=targets, recursive=recursive, quiet=False)
    resolved_targets = resolve_targets(request)
    return move_to_trash(resolved_targets)
