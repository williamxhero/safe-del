from collections.abc import Sequence
from dataclasses import dataclass

from safe_del.models import DeleteRequest


VERSION_TEXT = "safe-del 0.1.0"

HELP_TEXT = """\
用法:
  safe-del [选项] 目标 [目标 ...]

说明:
  目标可以是文件、目录或通配符。匹配到的目标会被移动到回收站，不会直接永久删除。
  为防止误删，禁止删除整个分区、系统根目录或根目录下全部内容，例如 C:、D:\\、C:\\*、/、/*、/**。

常见兼容参数:
  /q                  静默模式
  /s                  通配符递归匹配子目录
  /f /p /a /a:...     接受并兼容，当前不改变删除行为
  -f --force          忽略未匹配目标
  -i -I               接受并兼容，当前不交互确认
  -r -R --recursive   通配符递归匹配子目录
  -d --dir            接受并兼容，目录仍会移动到回收站
  -p --parents        接受并兼容，当前只处理显式传入目标
  -v --verbose        接受并兼容，默认会输出处理结果
  --interactive[=值]  接受并兼容，当前不交互确认
  --one-file-system   接受并兼容
  --preserve-root     接受并兼容
  --no-preserve-root  接受但不会关闭 safe-del 根目录保护
  --ignore-fail-on-non-empty 接受并兼容
  --quiet             静默模式
  --interactive=never 接受并兼容
  --version           显示版本
"""


class CliUsageError(ValueError):
    pass


class HelpRequested(Exception):
    pass


class VersionRequested(Exception):
    pass


@dataclass(frozen=True)
class CliParseState:
    recursive: bool
    quiet: bool
    ignore_missing: bool


def parse_cli_args(argv: Sequence[str]) -> DeleteRequest:
    state = CliParseState(recursive=False, quiet=False, ignore_missing=False)
    targets: list[str] = []
    parse_options = True

    for raw_token in argv:
        token = raw_token
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and _is_help_token(token):
            raise HelpRequested()
        if parse_options and _is_version_token(token):
            raise VersionRequested()
        if parse_options and token.startswith("--"):
            state = _apply_long_option(token, state)
            continue
        if parse_options and _is_slash_option(token):
            state = _apply_slash_option(token, state)
            continue
        if parse_options and _is_short_option(token):
            state = _apply_short_option(token, state)
            continue
        targets.append(token)

    if not targets:
        raise CliUsageError("缺少删除目标。")

    return DeleteRequest(
        targets=targets,
        recursive=state.recursive,
        quiet=state.quiet,
        ignore_missing=state.ignore_missing,
    )


def _is_help_token(token: str) -> bool:
    return token in {"/?", "-h", "--help"}


def _is_version_token(token: str) -> bool:
    return token == "--version"


def _is_slash_option(token: str) -> bool:
    if not token.startswith("/"):
        return False
    if len(token) == 2 and token[1].isalpha():
        return True
    return token.lower().startswith("/a")


def _is_short_option(token: str) -> bool:
    return token.startswith("-") and len(token) > 1 and not token.startswith("--")


def _apply_long_option(token: str, state: CliParseState) -> CliParseState:
    if token == "--recursive":
        return CliParseState(recursive=True, quiet=state.quiet, ignore_missing=state.ignore_missing)
    if token == "--force":
        return CliParseState(recursive=state.recursive, quiet=state.quiet, ignore_missing=True)
    if token == "--quiet":
        return CliParseState(recursive=state.recursive, quiet=True, ignore_missing=state.ignore_missing)
    if token in _NOOP_LONG_OPTIONS:
        return state
    if _is_noop_long_option_with_value(token):
        return state
    raise CliUsageError(f"不支持的参数: {token}")


_NOOP_LONG_OPTIONS = {
    "--dir",
    "--interactive",
    "--one-file-system",
    "--no-preserve-root",
    "--preserve-root",
    "--parents",
    "--verbose",
    "--ignore-fail-on-non-empty",
}


def _is_noop_long_option_with_value(token: str) -> bool:
    if token.startswith("--interactive="):
        return token in {"--interactive=never", "--interactive=once", "--interactive=always"}
    if token.startswith("--preserve-root="):
        return token == "--preserve-root=all"
    return False


def _apply_slash_option(token: str, state: CliParseState) -> CliParseState:
    lower_token = token.lower()
    if lower_token == "/s":
        return CliParseState(recursive=True, quiet=state.quiet, ignore_missing=state.ignore_missing)
    if lower_token == "/q":
        return CliParseState(recursive=state.recursive, quiet=True, ignore_missing=state.ignore_missing)
    if lower_token in {"/f", "/p"}:
        return state
    if lower_token == "/a":
        return state
    if lower_token.startswith("/a:"):
        return state
    raise CliUsageError(f"不支持的参数: {token}")


def _apply_short_option(token: str, state: CliParseState) -> CliParseState:
    current_recursive = state.recursive
    current_quiet = state.quiet
    current_ignore_missing = state.ignore_missing

    for flag in token[1:]:
        if flag in {"r", "R"}:
            current_recursive = True
            continue
        if flag == "f":
            current_ignore_missing = True
            continue
        if flag in {"d", "i", "I", "p", "v"}:
            continue
        if flag == "q":
            current_quiet = True
            continue
        raise CliUsageError(f"不支持的参数: {token}")

    return CliParseState(
        recursive=current_recursive,
        quiet=current_quiet,
        ignore_missing=current_ignore_missing,
    )
