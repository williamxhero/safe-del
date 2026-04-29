# safe-del

[中文](README.md) | English

A deletion tool built for AI and agents. After Codex completely wiped my D drive and even a 500 RMB recovery attempt failed to recover the data, I asked Codex to help build this tool: a safer delete command designed for AI, XX Code, and AI agents.

`safe-del` is a cross-platform safe delete command. It currently supports Windows and Ubuntu/Linux.

It does not permanently delete files directly. Instead, it moves targets to the system trash or recycle bin.



## Installation

Run this in the current directory:

```shell
pip install .
```

For development mode:

```shell
pip install -e .
```

After installation, you can call it directly:

Windows:

```powershell
safe-del E:\something\*.tmp
```

Ubuntu/Linux:

```bash
safe-del ~/downloads/*.tmp
```



## Basic Usage

Multiple files, directories, and wildcard patterns are supported:

Windows:

```powershell
safe-del a.tmp b.tmp
safe-del *.tmp *.log
safe-del E:\cache\*.tmp D:\temp\debug-*.txt
safe-del D:\work\build
```

Ubuntu/Linux:

```bash
safe-del a.tmp b.tmp
safe-del '*.tmp' '*.log'
safe-del ~/cache/*.tmp /tmp/debug-*.txt
safe-del ~/work/build
```

Common compatible options:

- Windows `del`, `erase`: `/q`, `/f`, `/p`, `/s`, `/a`, `/a:...`
- Windows `rd`, `rmdir`: `/s`, `/q`
- GNU `rm`: `-f`, `-i`, `-I`, `-r`, `-R`, `-d`, `-v`, `--force`, `--interactive`, `--interactive=never`, `--interactive=once`, `--interactive=always`, `--one-file-system`, `--no-preserve-root`, `--preserve-root`, `--preserve-root=all`, `--recursive`, `--dir`, `--verbose`
- GNU `rmdir`: `-p`, `-v`, `--parents`, `--verbose`, `--ignore-fail-on-non-empty`
- GNU `unlink`: `--help`, `--version`
- safe-del common options: `--quiet`, `--help`, `--version`, `--`
- Short options can be combined, for example `-rf`, `-fr`, `-rvf`

Notes:

- `/s`, `-r`, `-R`, and `--recursive` make wildcard patterns match subdirectories recursively.
- `-f` and `--force` ignore unmatched targets.
- `-i`, `-I`, and `--interactive...` are accepted, but safe-del currently does not prompt interactively.
- `-d`, `--dir`, `-p`, `--parents`, `--one-file-system`, `--preserve-root...`, and `--ignore-fail-on-non-empty` are accepted for command compatibility. safe-del still only processes explicitly passed targets.
- `--no-preserve-root` is accepted, but it does not disable safe-del root-directory protection.
- Passing an existing directory moves the whole directory to the trash or recycle bin.
- Unmatched targets are listed separately and return a non-zero exit code.
- To prevent accidental deletion on Windows, deleting an entire drive or everything under a drive root is forbidden, for example `C:`, `D:\`, `C:\*`, `C:\*.*`, `E:\**`.
- To prevent accidental deletion on Ubuntu/Linux, deleting the system root directory or everything under it is forbidden, for example `/`, `/*`, `/*.*`, `/**`, `/**/*`.



## Local Command Mapping

This repository provides `safe-del-install`, which maps common interactive delete commands for the current user to `safe-del`. If an AI directly calls a system delete command, safe-del can still take over and reduce risk.

Run:

Windows:

```powershell
safe-del-install
```

Ubuntu/Linux:

```bash
safe-del-install
```

On Windows, the installer overrides these commands:

- PowerShell: `Remove-Item`, `del`, `erase`, `rm`, `rd`, `ri`, `rmdir`
- cmd: `del`, `erase`, `rd`, `rmdir`, `rm`, `unlink`

Windows installation actions:

- Write PowerShell and cmd initialization scripts under `~/.safe-del/`
- Update the current user's PowerShell profile
- Update the current user's `cmd` AutoRun

On Ubuntu/Linux, the installer overrides these interactive shell commands:

- `rm`
- `rmdir`
- `unlink`
- `del`
- `erase`
- `rd`

`rm`, `del`, and `erase` fit file-deletion habits; `rmdir` and `rd` fit directory-deletion habits; `unlink` fits single-path deletion habits. All commands eventually go through the same safe-del option compatibility layer.

Ubuntu/Linux installation actions:

- Write a POSIX shell initialization script under `~/.safe-del/`
- Update the current user's `~/.bashrc` and `~/.profile`
- If the current shell is zsh, or `~/.zshrc` already exists, update `~/.zshrc` too

Limitations:

- Only PowerShell sessions that load the profile are covered.
- Only cmd sessions that have not explicitly disabled AutoRun are covered.
- Batch internal command expansion is not covered.
- Only Ubuntu/Linux interactive shell sessions that load the profile are covered.
- Explicit script calls such as `command rm`, `/bin/rm`, and `/usr/bin/rm` are not covered.
- Third-party programs directly calling system delete APIs are not covered.
- Git Bash, WSL, BusyBox, and other shells that do not load the updated profiles are not covered.



## Examples

```powershell
safe-del /q /s *.tmp
safe-del -rf D:\work\build
safe-del E:\downloads\*.crdownload E:\downloads\*.tmp
Remove-Item .\build -Recurse -Force
del /q *.log
rd /s /q .\dist
```

```bash
safe-del -rf ~/work/build
safe-del --recursive '*.tmp'
rm -fv missing.log old.log
rm --interactive=never -rf ~/work/build
rm -rf ~/work/build
rmdir ~/empty-dir
rmdir -pv ~/empty-parent/empty-child
unlink ~/old-link
```



## Rules For Agents

```markdown
**Highest-priority mandatory rule**: any delete operation must use safe-del and only safe-del. Do not use del, erase, rm, rmdir, rd, or any other delete command. Do not bypass this rule through scripts, aliases, wrappers, or indirect calls.

safe-del usage:
safe-del [options] target [target ...]

Description:
Targets can be files, directories, or wildcard patterns.
Matched targets are moved to the trash or recycle bin, not permanently deleted directly.
On Windows, deleting an entire drive or everything under a drive root is forbidden.
On Ubuntu/Linux, deleting the system root directory or everything under it is forbidden.

Common compatible options:
/q quiet mode
/s -r -R --recursive recursively match subdirectories for wildcard patterns
-f --force ignore unmatched targets
-i -I --interactive... accepted for compatibility; currently no interactive prompt
-d --dir -p --parents -v --verbose --one-file-system --preserve-root... --ignore-fail-on-non-empty accepted for compatibility
/f /p /a /a:... accepted for compatibility
```
