# safe-del

`safe-del` 是一个 Windows 下的安全删除命令。

它不会直接永久删除文件，而是把目标移动到回收站，可作为 `del`、`erase`、`rm` 这类删除命令的替代。适合放心的交给AI / Agents 去操作文件。

## 安装

在当前目录执行：

```powershell
pip install .
```

如果要开发模式安装：

```powershell
pip install -e .
```

安装完成后，任意目录都可以直接调用：

```powershell
safe-del E:\something\*.tmp
```

## 支持的调用方式

支持多个文件、多个通配符参数：

```powershell
safe-del a.tmp b.tmp
safe-del *.tmp *.log
safe-del E:\cache\*.tmp D:\temp\debug-*.txt
```

兼容常见删除参数格式：

```powershell
safe-del /q *.tmp
safe-del /s E:\logs\*.tmp
safe-del -rf build
safe-del --recursive *.tmp
```

当前支持的常见参数：

- `/q`
- `/f`
- `/p`
- `/s`
- `/a`、`/a:...`
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

- `/s`、`-r`、`-R`、`--recursive` 会让通配符按递归方式匹配子目录。
- 直接传入已存在的目录时，会把整个目录移动到回收站。
- 没有匹配到的参数会在结果里单独列出，并返回非零退出码。

## 示例

```powershell
safe-del /q /s *.tmp
safe-del -rf D:\work\build
safe-del E:\downloads\*.crdownload E:\downloads\*.tmp
```



## 给Agent的prompt：

## 安全须知

```markdown
**最高优先级强制规则**：任何删除操作必须且只能使用 safe-del。严禁使用 del、erase、rm、rmdir、rd 或任何其他删除命令，严禁通过脚本、别名、封装或间接方式绕过。

safe-del 用法：
safe-del [选项] 目标 [目标 ...] 
说明: 目标可以是文件、目录或通配符。 
匹配到的目标会被移动到回收站，不会直接永久删除。 
常见兼容参数: 
/q 静默模式 
/s -r -R --recursive 通配符递归匹配子目录
/f /p /a /a:... -f --force --interactive=never 接受并兼容，当前不改变删除行为。
```
