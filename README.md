# safe-del

`safe-del` 是一个 Windows 下的安全删除命令。

它不会直接永久删除文件，而是把目标移动到回收站。它适合替代常见的删除命令，降低误删风险。

## 安装

在当前目录执行：

```powershell
pip install .
```

如果要开发模式安装：

```powershell
pip install -e .
```

安装完成后，可以直接调用：

```powershell
safe-del E:\something\*.tmp
```

## 基本用法

支持多个文件、目录和通配符：

```powershell
safe-del a.tmp b.tmp
safe-del *.tmp *.log
safe-del E:\cache\*.tmp D:\temp\debug-*.txt
safe-del D:\work\build
```

兼容的常见参数：

- `/q`
- `/f`
- `/p`
- `/s`
- `/a`
- `/a:...`
- `-f`
- `-i`
- `-r`
- `-R`
- `-rf`
- `-fr`
- `--force`
- `--recursive`
- `--interactive=never`

说明：

- `/s`、`-r`、`-R`、`--recursive` 会让通配符递归匹配子目录。
- 直接传入已存在的目录时，会把整个目录移动到回收站。
- 没有匹配到的目标会单独列出，并返回非零退出码。

## 本机命令映射

仓库现在提供了 `safe-del-install`，用于把当前用户常见的交互式删除命令映射到 `safe-del`。

执行：

```powershell
safe-del-install
```

安装后会覆盖这些命令：

- PowerShell: `Remove-Item`、`del`、`erase`、`rm`、`rd`、`ri`、`rmdir`
- cmd: `del`、`erase`、`rd`、`rmdir`、`rm`、`unlink`

安装动作包括：

- 在 `~/.safe-del/` 下写入 PowerShell 和 cmd 初始化脚本
- 更新当前用户的 PowerShell profile
- 更新当前用户的 `cmd` AutoRun

限制：

- 只覆盖会加载 profile 的 PowerShell 会话
- 只覆盖未显式关闭 AutoRun 的 cmd 会话
- 不覆盖批处理内部命令展开
- 不覆盖第三方程序直接调用系统删除 API
- 不覆盖 Git Bash、WSL、BusyBox 等其他 shell 自带删除实现

## 示例

```powershell
safe-del /q /s *.tmp
safe-del -rf D:\work\build
safe-del E:\downloads\*.crdownload E:\downloads\*.tmp
Remove-Item .\build -Recurse -Force
del /q *.log
rd /s /q .\dist
```

## 给 Agent 的规则

```markdown
**最高优先级强制规则**：任何删除操作必须且只能使用 safe-del。严禁使用 del、erase、rm、rmdir、rd 或任何其他删除命令，严禁通过脚本、别名、封装或间接方式绕过。

safe-del 用法：
safe-del [选项] 目标 [目标 ...]

说明：
目标可以是文件、目录或通配符。
匹配到的目标会被移动到回收站，不会直接永久删除。

常见兼容参数：
/q 静默模式
/s -r -R --recursive 通配符递归匹配子目录
/f /p /a /a:... -f --force --interactive=never 接受并兼容，当前不改变删除行为
```
