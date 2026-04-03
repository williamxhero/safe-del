import sys
from collections.abc import Sequence

from safe_del.api import delete_targets
from safe_del.arguments import HELP_TEXT, CliUsageError, HelpRequested, parse_cli_args
from safe_del.models import DeleteResult
from safe_del.validator import DangerousTargetError


def main(argv: Sequence[str] | None = None) -> int:
    configure_output_streams()
    args = list(sys.argv[1:] if argv is None else argv)

    try:
        request = parse_cli_args(args)
    except HelpRequested:
        print(HELP_TEXT)
        return 0
    except CliUsageError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        print("使用 `safe-del --help` 查看帮助。", file=sys.stderr)
        return 2

    try:
        result = delete_targets(targets=request.targets, recursive=request.recursive)
    except DangerousTargetError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        return 2

    message = format_result_message(result, request.quiet)
    stream = sys.stderr if has_errors(result) else sys.stdout

    if message != "":
        print(message, file=stream)

    if has_errors(result):
        return 1
    return 0


def configure_output_streams() -> None:
    configure_output_stream(sys.stdout)
    configure_output_stream(sys.stderr)


def configure_output_stream(stream: object) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return

    encoding = getattr(stream, "encoding", "")
    if isinstance(encoding, str) and encoding.lower() == "utf-8":
        return

    reconfigure(encoding="utf-8", errors="replace")


def has_errors(result: DeleteResult) -> bool:
    return bool(result.missing_inputs or result.failures)


def format_result_message(result: DeleteResult, quiet: bool) -> str:
    lines: list[str] = []

    if not quiet and result.moved_paths:
        lines.append(f"已移入回收站: {len(result.moved_paths)} 项")
        for path in result.moved_paths:
            lines.append(path)

    if result.missing_inputs:
        lines.append(f"未匹配到目标: {len(result.missing_inputs)} 项")
        for raw_input in result.missing_inputs:
            lines.append(raw_input)

    if result.failures:
        lines.append(f"移入回收站失败: {len(result.failures)} 项")
        for failure in result.failures:
            lines.append(f"{failure.path} | {failure.message}")

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
