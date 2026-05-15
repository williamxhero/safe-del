import sys
from collections.abc import Sequence

from safe_del.models import TrashCleanResult
from safe_del.trash_cleaner import empty_trash


HELP_TEXT = """\
用法:
  safe-del-empty-trash

说明:
  清空 safe-del 使用的 Freedesktop Trash 回收站目录。
"""


class CliUsageError(ValueError):
    pass


class HelpRequested(Exception):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    configure_output_streams()
    args = list(sys.argv[1:] if argv is None else argv)

    try:
        parse_cli_args(args)
        result = empty_trash()
    except HelpRequested:
        print(HELP_TEXT)
        return 0
    except CliUsageError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        print("使用 `safe-del-empty-trash --help` 查看帮助。", file=sys.stderr)
        return 2

    message = format_result_message(result)
    stream = sys.stderr if result.failures else sys.stdout
    print(message, file=stream)
    if result.failures:
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


def parse_cli_args(argv: Sequence[str]) -> None:
    if not argv:
        return

    if len(argv) == 1 and argv[0] in {"-h", "--help"}:
        raise HelpRequested()

    raise CliUsageError(f"不支持的参数: {' '.join(argv)}")


def format_result_message(result: TrashCleanResult) -> str:
    lines = [f"已清空回收站条目: {result.deleted_count} 项"]

    if result.cleaned_roots:
        lines.append("已检查回收站:")
        for trash_root in result.cleaned_roots:
            lines.append(f"  {trash_root}")

    if result.failures:
        lines.append(f"清空失败: {len(result.failures)} 项")
        for failure in result.failures:
            lines.append(f"{failure.path} | {failure.message}")

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
