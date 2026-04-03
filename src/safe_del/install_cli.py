import os
import shutil
import subprocess
import sys
import winreg
from collections.abc import Sequence
from dataclasses import dataclass


HELP_TEXT = """\
用法:
  safe-del-install

说明:
  为当前用户安装 safe-del 的命令映射。

覆盖范围:
  PowerShell:
    Remove-Item
    del
    erase
    rm
    rd
    ri
    rmdir
  cmd:
    del
    erase
    rd
    rmdir
    rm
    unlink

限制:
  只覆盖会加载 profile 的 PowerShell 会话。
  只覆盖未显式关闭 AutoRun 的 cmd 会话。
  不覆盖批处理内部命令展开。
  不覆盖第三方程序直接调用系统删除 API。
  不覆盖其他 shell 自带的删除实现。
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
class InstallContext:
    install_root: str
    powershell_hook_path: str
    cmd_hook_path: str
    safe_del_path: str
    profile_targets: list[ProfileTarget]
    existing_cmd_autorun: str


@dataclass(frozen=True)
class InstallResult:
    written_files: list[str]
    updated_profiles: list[str]
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
    powershell_hook_path = os.path.join(install_root, "safe-del-hook.ps1")
    cmd_hook_path = os.path.join(install_root, "safe-del-cmd-init.cmd")
    profile_targets = resolve_profile_targets()
    existing_cmd_autorun = read_cmd_autorun_value()
    return InstallContext(
        install_root=install_root,
        powershell_hook_path=powershell_hook_path,
        cmd_hook_path=cmd_hook_path,
        safe_del_path=safe_del_path,
        profile_targets=profile_targets,
        existing_cmd_autorun=existing_cmd_autorun,
    )


def resolve_safe_del_path() -> str:
    safe_del_path = shutil.which("safe-del")
    if safe_del_path is None:
        raise CliUsageError("未找到 safe-del，请先执行 `pip install -e .` 或 `pip install .`。")
    return os.path.abspath(safe_del_path)


def resolve_profile_targets() -> list[ProfileTarget]:
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
    written_files = write_runtime_files(context)
    updated_profiles = install_powershell_profiles(context)
    cmd_autorun_value = install_cmd_autorun(context)
    return InstallResult(
        written_files=written_files,
        updated_profiles=updated_profiles,
        cmd_autorun_value=cmd_autorun_value,
    )


def write_runtime_files(context: InstallContext) -> list[str]:
    os.makedirs(context.install_root, exist_ok=True)

    powershell_hook = build_powershell_hook(context.safe_del_path)
    cmd_hook = build_cmd_hook(context.safe_del_path)

    write_text_file(context.powershell_hook_path, powershell_hook)
    write_text_file(context.cmd_hook_path, cmd_hook)

    return [context.powershell_hook_path, context.cmd_hook_path]


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


def install_powershell_profiles(context: InstallContext) -> list[str]:
    updated_profiles: list[str] = []
    for profile_target in context.profile_targets:
        install_powershell_profile(profile_target.path, context.powershell_hook_path)
        updated_profiles.append(profile_target.path)
    return updated_profiles


def install_powershell_profile(profile_path: str, hook_path: str) -> None:
    existing = read_text_file(profile_path)
    block = build_profile_block(hook_path)
    updated = upsert_profile_block(existing, block)
    write_text_file(profile_path, updated)


def read_text_file(path: str) -> str:
    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8", errors="replace") as file:
        return file.read()


def build_profile_block(hook_path: str) -> str:
    escaped_path = hook_path.replace("'", "''")
    return f"""{PROFILE_MARKER_START}
. '{escaped_path}'
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


def install_cmd_autorun(context: InstallContext) -> str:
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
    lines.append("已更新 PowerShell profile:")
    for path in result.updated_profiles:
        lines.append(f"  {path}")

    lines.append("")
    lines.append("cmd AutoRun:")
    lines.append(f"  {result.cmd_autorun_value}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
