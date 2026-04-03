from collections.abc import Sequence

from safe_del.models import DeleteRequest


HELP_TEXT = """\
用法:
  safe-del [选项] 目标 [目标 ...]

说明:
  目标可以是文件、目录或通配符。
  匹配到的目标会被移动到回收站，不会直接永久删除。

常见兼容参数:
  /q                  静默模式
  /s                  通配符递归匹配子目录
  /f /p /a /a:...     接受并兼容，当前不改变删除行为
  -f                  接受并兼容
  -r -R               通配符递归匹配子目录
  --force             接受并兼容
  --recursive         通配符递归匹配子目录
  --interactive=never 接受并兼容
"""


class CliUsageError(ValueError):
    pass


class HelpRequested(Exception):
    pass


def parse_cli_args(argv: Sequence[str]) -> DeleteRequest:
    recursive = False
    quiet = False
    targets: list[str] = []
    parse_options = True

    for raw_token in argv:
        token = raw_token
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and _is_help_token(token):
            raise HelpRequested()
        if parse_options and token.startswith("--"):
            recursive, quiet = _apply_long_option(token, recursive, quiet)
            continue
        if parse_options and _is_slash_option(token):
            recursive, quiet = _apply_slash_option(token, recursive, quiet)
            continue
        if parse_options and _is_short_option(token):
            recursive, quiet = _apply_short_option(token, recursive, quiet)
            continue
        targets.append(token)

    if not targets:
        raise CliUsageError("缺少删除目标。")

    return DeleteRequest(targets=targets, recursive=recursive, quiet=quiet)


def _is_help_token(token: str) -> bool:
    return token in {"/?", "-h", "--help"}


def _is_slash_option(token: str) -> bool:
    if not token.startswith("/"):
        return False
    if len(token) == 2 and token[1].isalpha():
        return True
    return token.lower().startswith("/a")


def _is_short_option(token: str) -> bool:
    return token.startswith("-") and len(token) > 1 and not token.startswith("--")


def _apply_long_option(token: str, recursive: bool, quiet: bool) -> tuple[bool, bool]:
    if token == "--recursive":
        return True, quiet
    if token == "--force":
        return recursive, quiet
    if token == "--quiet":
        return recursive, True
    if token == "--interactive=never":
        return recursive, quiet
    raise CliUsageError(f"不支持的参数: {token}")


def _apply_slash_option(token: str, recursive: bool, quiet: bool) -> tuple[bool, bool]:
    lower_token = token.lower()
    if lower_token == "/s":
        return True, quiet
    if lower_token == "/q":
        return recursive, True
    if lower_token in {"/f", "/p"}:
        return recursive, quiet
    if lower_token == "/a":
        return recursive, quiet
    if lower_token.startswith("/a:"):
        return recursive, quiet
    raise CliUsageError(f"不支持的参数: {token}")


def _apply_short_option(token: str, recursive: bool, quiet: bool) -> tuple[bool, bool]:
    current_recursive = recursive
    current_quiet = quiet

    for flag in token[1:]:
        if flag in {"r", "R"}:
            current_recursive = True
            continue
        if flag == "f":
            continue
        if flag == "i":
            continue
        if flag == "q":
            current_quiet = True
            continue
        raise CliUsageError(f"不支持的参数: {token}")

    return current_recursive, current_quiet
