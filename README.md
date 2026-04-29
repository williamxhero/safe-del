# safe-del

[English](README_EN.md) | 中文

为 AI 和 Agent 打造的 删除工具。当我的 D 盘被 Codex 彻底清空，花了 500 块钱也没有恢复数据后，我痛定思痛，让 Codex 帮我写了这个，专门面向 AI，XX Code 和 AI Agent 的删除工具。

`safe-del` 是跨平台安全删除命令，当前支持 Windows 和 Ubuntu/Linux。

它不会直接永久删除文件，而是把目标移动到系统回收站。



## 安装

在当前目录执行：

```shell
pip install .
```

如果要开发模式安装：

```shell
pip install -e .
```

安装完成后，可以直接调用：

Windows:

```powershell
safe-del E:\something\*.tmp
```

Ubuntu/Linux:

```bash
safe-del ~/downloads/*.tmp
```



## 基本用法

支持多个文件、目录和通配符：

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

兼容的常见参数：

- Windows `del`、`erase`: `/q`、`/f`、`/p`、`/s`、`/a`、`/a:...`
- Windows `rd`、`rmdir`: `/s`、`/q`
- GNU `rm`: `-f`、`-i`、`-I`、`-r`、`-R`、`-d`、`-v`、`--force`、`--interactive`、`--interactive=never`、`--interactive=once`、`--interactive=always`、`--one-file-system`、`--no-preserve-root`、`--preserve-root`、`--preserve-root=all`、`--recursive`、`--dir`、`--verbose`
- GNU `rmdir`: `-p`、`-v`、`--parents`、`--verbose`、`--ignore-fail-on-non-empty`
- GNU `unlink`: `--help`、`--version`
- safe-del 通用: `--quiet`、`--help`、`--version`、`--`
- 短参数可以组合，例如 `-rf`、`-fr`、`-rvf`

说明：

- `/s`、`-r`、`-R`、`--recursive` 会让通配符递归匹配子目录。
- `-f`、`--force` 会忽略未匹配目标。
- `-i`、`-I`、`--interactive...` 会被接受，但 safe-del 当前不会交互确认。
- `-d`、`--dir`、`-p`、`--parents`、`--one-file-system`、`--preserve-root...`、`--ignore-fail-on-non-empty` 会被接受以兼容原命令调用；safe-del 仍只处理显式传入的目标。
- `--no-preserve-root` 会被接受，但不会关闭 safe-del 的根目录保护。
- 直接传入已存在的目录时，会把整个目录移动到回收站。
- 没有匹配到的目标会单独列出，并返回非零退出码。
- 为防止误删，Windows 下禁止删除整个分区或分区根下全部内容，例如 `C:`、`D:\`、`C:\*`、`C:\*.*`、`E:\**`。
- 为防止误删，Ubuntu/Linux 下禁止删除系统根目录或根目录下全部内容，例如 `/`、`/*`、`/*.*`、`/**`、`/**/*`。



## 本机命令映射

仓库现在提供了 `safe-del-install`，用于把当前用户常见的交互式删除命令映射到 `safe-del`。让 AI 就算直接调用系统删除命令，也会由 safe-del 接管，以防不测。

执行：

Windows:

```powershell
safe-del-install
```

Ubuntu/Linux:

```bash
safe-del-install
```

Windows 安装后会覆盖这些命令：

- PowerShell: `Remove-Item`、`del`、`erase`、`rm`、`rd`、`ri`、`rmdir`
- cmd: `del`、`erase`、`rd`、`rmdir`、`rm`、`unlink`

Windows 安装动作包括：

- 在 `~/.safe-del/` 下写入 PowerShell 和 cmd 初始化脚本
- 更新当前用户的 PowerShell profile
- 更新当前用户的 `cmd` AutoRun

Ubuntu/Linux 安装后会覆盖这些交互式 shell 命令：

- `rm`
- `rmdir`
- `unlink`
- `del`
- `erase`
- `rd`

其中 `rm`、`del`、`erase` 适合按删除文件习惯使用；`rmdir`、`rd` 适合按删除目录习惯使用；`unlink` 适合按删除单个路径习惯使用。所有命令最终都会进入同一个 safe-del 参数兼容层。

Ubuntu/Linux 安装动作包括：

- 在 `~/.safe-del/` 下写入 POSIX shell 初始化脚本
- 更新当前用户的 `~/.bashrc` 和 `~/.profile`
- 如果当前 shell 是 zsh，或已存在 `~/.zshrc`，同时更新 `~/.zshrc`

限制：

- 只覆盖会加载 profile 的 PowerShell 会话
- 只覆盖未显式关闭 AutoRun 的 cmd 会话
- 不覆盖批处理内部命令展开
- 只覆盖会加载 profile 的 Ubuntu/Linux 交互式 shell 会话
- 不覆盖脚本内部显式调用 `command rm`、`/bin/rm`、`/usr/bin/rm` 等真实删除命令
- 不覆盖第三方程序直接调用系统删除 API
- 不覆盖 Git Bash、WSL、BusyBox 等没有加载上述 profile 的其他 shell 自带删除实现



## 示例

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



## 给 Agent 的规则

```markdown
**最高优先级强制规则**：任何删除操作必须且只能使用 safe-del。严禁使用 del、erase、rm、rmdir、rd 或任何其他删除命令，严禁通过脚本、别名、封装或间接方式绕过。

safe-del 用法：
safe-del [选项] 目标 [目标 ...]

说明：
目标可以是文件、目录或通配符。
匹配到的目标会被移动到回收站，不会直接永久删除。
Windows 下禁止删除整个分区或分区根下全部内容。
Ubuntu/Linux 下禁止删除系统根目录或根目录下全部内容。

常见兼容参数：
/q 静默模式
/s -r -R --recursive 通配符递归匹配子目录
-f --force 忽略未匹配目标
-i -I --interactive... 接受并兼容，当前不交互确认
-d --dir -p --parents -v --verbose --one-file-system --preserve-root... --ignore-fail-on-non-empty 接受并兼容
/f /p /a /a:... 接受并兼容
```
