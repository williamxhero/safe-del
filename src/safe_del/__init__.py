from safe_del.api import delete_targets
from safe_del.cli import main
from safe_del.models import DeleteFailure, DeleteResult

__all__ = ["DeleteFailure", "DeleteResult", "delete_targets", "main"]
