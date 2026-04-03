from safe_del.models import DeleteFailure, DeleteResult, ResolvedTargets


def move_to_trash(resolved_targets: ResolvedTargets) -> DeleteResult:
    from send2trash import send2trash

    moved_paths: list[str] = []
    failures: list[DeleteFailure] = []

    for path in resolved_targets.matched_paths:
        try:
            send2trash(path)
            moved_paths.append(path)
        except OSError as exc:
            failures.append(DeleteFailure(path=path, message=str(exc)))

    return DeleteResult(
        moved_paths=moved_paths,
        missing_inputs=resolved_targets.missing_inputs,
        failures=failures,
    )
