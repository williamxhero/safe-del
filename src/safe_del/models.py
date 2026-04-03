from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteRequest:
    targets: list[str]
    recursive: bool
    quiet: bool


@dataclass(frozen=True)
class ResolvedTargets:
    matched_paths: list[str]
    missing_inputs: list[str]


@dataclass(frozen=True)
class DeleteFailure:
    path: str
    message: str


@dataclass(frozen=True)
class DeleteResult:
    moved_paths: list[str]
    missing_inputs: list[str]
    failures: list[DeleteFailure]
