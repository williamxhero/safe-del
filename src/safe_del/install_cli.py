import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias


HELP_TEXT = """\
用法:
  safe-del-install

说明:
  为当前用户安装 safe-del 的命令映射。

覆盖范围:
  Windows PowerShell:
    Remove-Item
    del
    erase
    rm
    rd
    ri
    rmdir
  Windows cmd:
    del
    erase
    rd
    rmdir
    rm
    unlink
  Ubuntu/Linux POSIX shell:
    rm
    rmdir
    unlink
    del
    erase
    rd

限制:
  只覆盖会加载 profile 的交互式 shell 会话。
  不覆盖脚本内部显式调用 command rm、/bin/rm 或系统删除 API。
"""


PROFILE_MARKER_START = "# safe-del hook start"
PROFILE_MARKER_END = "# safe-del hook end"
CMD_AUTORUN_KEY = r"Software\Microsoft\Command Processor"
CMD_AUTORUN_NAME = "AutoRun"


class CliUsageError(ValueError):
    pass


class HelpRequested(Exception):
    pass


@dataclass(frozen=True)
class ProfileTarget:
    shell_name: str
    path: str


@dataclass(frozen=True)
class WindowsInstallContext:
    install_root: str
    powershell_hook_path: str
    cmd_hook_path: str
    safe_del_path: str
    profile_targets: list[ProfileTarget]
    existing_cmd_autorun: str


@dataclass(frozen=True)
class PosixInstallContext:
    install_root: str
    hook_path: str
    safe_del_path: str
    profile_targets: list[ProfileTarget]


InstallContext: TypeAlias = WindowsInstallContext | PosixInstallContext


@dataclass(frozen=True)
class InstallResult:
    written_files: list[str]
    updated_profiles: list[ProfileTarget]
    cmd_autorun_value: str


def main(argv: Sequence[str] | None = None) -> int:
    configure_output_streams()
    args = list(sys.argv[1:] if argv is None else argv)

    try:
        parse_cli_args(args)
        context = prepare_install_context()
        result = install_command_mapping(context)
    except HelpRequested:
        print(HELP_TEXT)
        return 0
    except CliUsageError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        print("使用 `safe-del-install --help` 查看帮助。", file=sys.stderr)
        return 2

    print(format_install_message(result))
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

    if len(argv) == 1 and argv[0] in {"-h", "--help", "/?"}:
        raise HelpRequested()

    raise CliUsageError(f"不支持的参数: {' '.join(argv)}")


def prepare_install_context() -> InstallContext:
    safe_del_path = resolve_safe_del_path()
    install_root = os.path.join(os.path.expanduser("~"), ".safe-del")
    if os.name == "nt":
        return prepare_windows_install_context(install_root, safe_del_path)
    return prepare_posix_install_context(install_root, safe_del_path)


def prepare_windows_install_context(install_root: str, safe_del_path: str) -> WindowsInstallContext:
    powershell_hook_path = os.path.join(install_root, "safe-del-hook.ps1")
    cmd_hook_path = os.path.join(install_root, "safe-del-cmd-init.cmd")
    profile_targets = resolve_windows_profile_targets()
    existing_cmd_autorun = read_cmd_autorun_value()
    return WindowsInstallContext(
        install_root=install_root,
        powershell_hook_path=powershell_hook_path,
        cmd_hook_path=cmd_hook_path,
        safe_del_path=safe_del_path,
        profile_targets=profile_targets,
        existing_cmd_autorun=existing_cmd_autorun,
    )


def prepare_posix_install_context(install_root: str, safe_del_path: str) -> PosixInstallContext:
    hook_path = os.path.join(install_root, "safe-del-posix.sh")
    profile_targets = resolve_posix_profile_targets()
    return PosixInstallContext(
        install_root=install_root,
        hook_path=hook_path,
        safe_del_path=safe_del_path,
        profile_targets=profile_targets,
    )


def resolve_safe_del_path() -> str:
    candidate_paths = [resolve_sibling_safe_del_path()]
    path_value = shutil.which("safe-del")
    if path_value is not None:
        candidate_paths.append(path_value)

    for candidate_path in candidate_paths:
        if candidate_path != "" and os.path.exists(candidate_path):
            return os.path.abspath(candidate_path)

    raise CliUsageError("未找到 safe-del，请先执行 `pip install -e .` 或 `pip install .`。")


def resolve_sibling_safe_del_path() -> str:
    script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    executable_names = ["safe-del"]
    if os.name == "nt":
        executable_names.append("safe-del.exe")

    for executable_name in executable_names:
        candidate_path = os.path.join(script_dir, executable_name)
        if os.path.exists(candidate_path):
            return candidate_path

    return ""


def resolve_windows_profile_targets() -> list[ProfileTarget]:
    profile_targets: list[ProfileTarget] = []
    seen_paths: set[str] = set()

    for shell_name in ("powershell", "pwsh"):
        profile_path = query_profile_path(shell_name)
        if profile_path == "":
            continue

        identity = os.path.normcase(os.path.normpath(profile_path))
        if identity in seen_paths:
            continue

        seen_paths.add(identity)
        profile_targets.append(ProfileTarget(shell_name=shell_name, path=profile_path))

    if profile_targets:
        return profile_targets

    fallback_path = os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "WindowsPowerShell",
        "profile.ps1",
    )
    return [ProfileTarget(shell_name="powershell", path=fallback_path)]


def resolve_posix_profile_targets() -> list[ProfileTarget]:
    home_path = os.path.expanduser("~")
    profile_targets: list[ProfileTarget] = []
    seen_paths: set[str] = set()

    for profile_target in build_posix_profile_candidates(home_path):
        identity = os.path.normcase(os.path.normpath(profile_target.path))
        if identity in seen_paths:
            continue

        seen_paths.add(identity)
        profile_targets.append(profile_target)

    return profile_targets


def build_posix_profile_candidates(home_path: str) -> list[ProfileTarget]:
    candidates = [
        ProfileTarget(shell_name="bash", path=os.path.join(home_path, ".bashrc")),
        ProfileTarget(shell_name="sh", path=os.path.join(home_path, ".profile")),
    ]

    current_shell = os.path.basename(os.environ.get("SHELL", ""))
    if current_shell == "zsh" or os.path.exists(os.path.join(home_path, ".zshrc")):
        candidates.append(ProfileTarget(shell_name="zsh", path=os.path.join(home_path, ".zshrc")))

    return candidates


def query_profile_path(shell_name: str) -> str:
    if shutil.which(shell_name) is None:
        return ""

    completed = subprocess.run(
        [shell_name, "-NoProfile", "-Command", "$PROFILE.CurrentUserAllHosts"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return ""

    return completed.stdout.strip()


def read_cmd_autorun_value() -> str:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CMD_AUTORUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, CMD_AUTORUN_NAME)
            if isinstance(value, str):
                return value
    except FileNotFoundError:
        return ""
    except OSError:
        return ""

    return ""


def install_command_mapping(context: InstallContext) -> InstallResult:
    if isinstance(context, WindowsInstallContext):
        return install_windows_command_mapping(context)
    return install_posix_command_mapping(context)


def install_windows_command_mapping(context: WindowsInstallContext) -> InstallResult:
    written_files = write_windows_runtime_files(context)
    updated_profiles = install_powershell_profiles(context)
    cmd_autorun_value = install_cmd_autorun(context)
    return InstallResult(
        written_files=written_files,
        updated_profiles=updated_profiles,
        cmd_autorun_value=cmd_autorun_value,
    )


def install_posix_command_mapping(context: PosixInstallContext) -> InstallResult:
    written_files = write_posix_runtime_files(context)
    updated_profiles = install_posix_profiles(context)
    return InstallResult(
        written_files=written_files,
        updated_profiles=updated_profiles,
        cmd_autorun_value="",
    )


def write_windows_runtime_files(context: WindowsInstallContext) -> list[str]:
    os.makedirs(context.install_root, exist_ok=True)

    powershell_hook = build_powershell_hook(context.safe_del_path)
    cmd_hook = build_cmd_hook(context.safe_del_path)

    write_text_file(context.powershell_hook_path, powershell_hook)
    write_text_file(context.cmd_hook_path, cmd_hook)

    return [context.powershell_hook_path, context.cmd_hook_path]


def write_posix_runtime_files(context: PosixInstallContext) -> list[str]:
    os.makedirs(context.install_root, exist_ok=True)
    hook = build_posix_hook(context.safe_del_path)
    write_text_file(context.hook_path, hook)
    return [context.hook_path]


def build_powershell_hook(safe_del_path: str) -> str:
    escaped_path = safe_del_path.replace("'", "''")
    return f"""\
$script:SafeDelExecutable = '{escaped_path}'

function Resolve-SafeDelTarget {{
    param(
        [object]$Value
    )

    if ($null -eq $Value) {{
        return ''
    }}

    if ($Value -is [string]) {{
        return $Value
    }}

    $fullNameProperty = $Value.PSObject.Properties['FullName']
    if ($null -ne $fullNameProperty) {{
        return [string]$fullNameProperty.Value
    }}

    return [string]$Value
}}

function Add-SafeDelTargets {{
    param(
        [System.Collections.Generic.List[string]]$TargetList,
        [object[]]$Values
    )

    foreach ($value in $Values) {{
        $target = Resolve-SafeDelTarget -Value $value
        if ($target -eq '') {{
            continue
        }}

        $TargetList.Add($target)
    }}
}}

function Add-SafeDelLiteralTargets {{
    param(
        [System.Collections.Generic.List[string]]$TargetList,
        [System.Collections.Generic.List[string]]$MissingList,
        [string[]]$Values
    )

    foreach ($value in $Values) {{
        if ($value -eq '') {{
            continue
        }}

        if (-not (Test-Path -LiteralPath $value)) {{
            $MissingList.Add($value)
            continue
        }}

        $resolvedPath = Resolve-Path -LiteralPath $value
        foreach ($item in $resolvedPath) {{
            $TargetList.Add($item.ProviderPath)
        }}
    }}
}}

function Invoke-SafeDelCommand {{
    param(
        [System.Collections.Generic.List[string]]$TargetList,
        [bool]$Recurse,
        [bool]$Force,
        [bool]$WhatIf
    )

    if ($TargetList.Count -eq 0) {{
        throw '缺少删除目标。'
    }}

    $arguments = New-Object 'System.Collections.Generic.List[string]'
    if ($Recurse) {{
        $arguments.Add('--recursive')
    }}
    if ($Force) {{
        $arguments.Add('--force')
    }}
    foreach ($target in $TargetList) {{
        $arguments.Add($target)
    }}

    if ($WhatIf) {{
        Write-Host ('safe-del ' + ($arguments -join ' '))
        return
    }}

    & $script:SafeDelExecutable @arguments
}}

function Remove-Item {{
    [CmdletBinding()]
    param(
        [Parameter(Position=0, ValueFromPipeline=$true, ValueFromPipelineByPropertyName=$true)]
        [object[]]$Path = @(),
        [string[]]$LiteralPath = @(),
        [switch]$Recurse,
        [switch]$Force,
        [bool]$Confirm = $false,
        [bool]$WhatIf = $false
    )

    begin {{
        $targets = New-Object 'System.Collections.Generic.List[string]'
        $missingLiteralTargets = New-Object 'System.Collections.Generic.List[string]'
    }}

    process {{
        Add-SafeDelTargets -TargetList $targets -Values $Path
        Add-SafeDelLiteralTargets -TargetList $targets -MissingList $missingLiteralTargets -Values $LiteralPath
    }}

    end {{
        foreach ($missingTarget in $missingLiteralTargets) {{
            Write-Error "未找到路径: $missingTarget"
        }}

        if ($targets.Count -eq 0) {{
            if ($missingLiteralTargets.Count -gt 0) {{
                $global:LASTEXITCODE = 1
            }}
            return
        }}

        Invoke-SafeDelCommand -TargetList $targets -Recurse:$Recurse.IsPresent -Force:$Force.IsPresent -WhatIf:$WhatIf

        if ($missingLiteralTargets.Count -gt 0) {{
            $global:LASTEXITCODE = 1
        }}
    }}
}}

Set-Alias -Name del -Value Remove-Item -Option AllScope -Scope Global -Force
Set-Alias -Name erase -Value Remove-Item -Option AllScope -Scope Global -Force
Set-Alias -Name rd -Value Remove-Item -Option AllScope -Scope Global -Force
Set-Alias -Name ri -Value Remove-Item -Option AllScope -Scope Global -Force
Set-Alias -Name rm -Value Remove-Item -Option AllScope -Scope Global -Force
Set-Alias -Name rmdir -Value Remove-Item -Option AllScope -Scope Global -Force
"""


def build_cmd_hook(safe_del_path: str) -> str:
    return f"""\
@echo off
doskey del="{safe_del_path}" $*
doskey erase="{safe_del_path}" $*
doskey rd="{safe_del_path}" $*
doskey rmdir="{safe_del_path}" $*
doskey rm="{safe_del_path}" $*
doskey unlink="{safe_del_path}" $*
"""


def build_posix_hook(safe_del_path: str) -> str:
    escaped_path = shell_single_quote(safe_del_path)
    return f"""\
SAFE_DEL_EXECUTABLE={escaped_path}

safe_del_command() {{
    "$SAFE_DEL_EXECUTABLE" "$@"
}}

rm() {{
    safe_del_command "$@"
}}

rmdir() {{
    safe_del_command "$@"
}}

unlink() {{
    safe_del_command "$@"
}}

del() {{
    safe_del_command "$@"
}}

erase() {{
    safe_del_command "$@"
}}

rd() {{
    safe_del_command "$@"
}}
"""


def shell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def write_text_file(path: str, content: str) -> None:
    directory = os.path.dirname(path)
    if directory != "":
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding=select_file_encoding(path), newline="\n") as file:
        file.write(content)


def select_file_encoding(path: str) -> str:
    if path.lower().endswith(".ps1"):
        return "utf-8-sig"
    return "utf-8"


def install_powershell_profiles(context: WindowsInstallContext) -> list[ProfileTarget]:
    updated_profiles: list[ProfileTarget] = []
    for profile_target in context.profile_targets:
        install_powershell_profile(profile_target.path, context.powershell_hook_path)
        updated_profiles.append(profile_target)
    return updated_profiles


def install_posix_profiles(context: PosixInstallContext) -> list[ProfileTarget]:
    updated_profiles: list[ProfileTarget] = []
    for profile_target in context.profile_targets:
        install_posix_profile(profile_target.path, context.hook_path)
        updated_profiles.append(profile_target)
    return updated_profiles


def install_powershell_profile(profile_path: str, hook_path: str) -> None:
    existing = read_text_file(profile_path)
    block = build_powershell_profile_block(hook_path)
    updated = upsert_profile_block(existing, block)
    write_text_file(profile_path, updated)


def install_posix_profile(profile_path: str, hook_path: str) -> None:
    existing = read_text_file(profile_path)
    block = build_posix_profile_block(hook_path)
    updated = upsert_profile_block(existing, block)
    write_text_file(profile_path, updated)


def read_text_file(path: str) -> str:
    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8", errors="replace") as file:
        return file.read()


def build_powershell_profile_block(hook_path: str) -> str:
    escaped_path = hook_path.replace("'", "''")
    return f"""{PROFILE_MARKER_START}
. '{escaped_path}'
{PROFILE_MARKER_END}
"""


def build_posix_profile_block(hook_path: str) -> str:
    escaped_path = shell_single_quote(hook_path)
    return f"""{PROFILE_MARKER_START}
. {escaped_path}
{PROFILE_MARKER_END}
"""


def upsert_profile_block(existing: str, block: str) -> str:
    start_index = existing.find(PROFILE_MARKER_START)
    end_index = existing.find(PROFILE_MARKER_END)

    if start_index != -1 and end_index != -1 and end_index >= start_index:
        block_end_index = end_index + len(PROFILE_MARKER_END)
        prefix = existing[:start_index].rstrip()
        suffix = existing[block_end_index:].lstrip("\r\n")
        return join_profile_sections(prefix, block.rstrip(), suffix)

    return join_profile_sections(existing.rstrip(), block.rstrip(), "")


def join_profile_sections(prefix: str, block: str, suffix: str) -> str:
    sections = [section for section in (prefix, block, suffix) if section != ""]
    if not sections:
        return ""
    return "\n\n".join(sections) + "\n"


def install_cmd_autorun(context: WindowsInstallContext) -> str:
    import winreg

    updated_value = build_cmd_autorun_value(context.existing_cmd_autorun, context.cmd_hook_path)
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, CMD_AUTORUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, CMD_AUTORUN_NAME, 0, winreg.REG_SZ, updated_value)
    return updated_value


def build_cmd_autorun_value(existing_value: str, hook_path: str) -> str:
    normalized_existing = existing_value.strip()
    hook_command = f'if exist "{hook_path}" call "{hook_path}"'

    if hook_path.lower() in normalized_existing.lower():
        return normalized_existing

    if normalized_existing == "":
        return hook_command

    return f"{hook_command} & {normalized_existing}"


def format_install_message(result: InstallResult) -> str:
    lines = ["安装完成。", "", "已写入文件:"]
    for path in result.written_files:
        lines.append(f"  {path}")

    lines.append("")
    lines.append("已更新 shell profile:")
    for profile_target in result.updated_profiles:
        lines.append(f"  {profile_target.shell_name}: {profile_target.path}")

    if result.cmd_autorun_value != "":
        lines.append("")
        lines.append("cmd AutoRun:")
        lines.append(f"  {result.cmd_autorun_value}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
