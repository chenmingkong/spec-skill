---
name: spec-skill
description: 当用户要求同步规范、从 GitHub 拉取上层规范、更新规范锁、运行规范检查或初始化 openspec 时使用。直接通过内置 Python 脚本触发 spec sync/check/init 工作流，无需安装 spec CLI。
---

# spec-skill

## 概述

通过内置 Python 脚本直接运行 spec 命令（`sync`、`check`、`init`），脚本位于：

```
C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py
```

无需 `pip install` 安装整个 CLI —— 脚本通过 `sys.path` 自包含加载。

## 触发时机

- 用户说"同步规范"、"拉取规范"、"更新 specs"
- 用户说"检查规范"、"验证合规性"、"run spec check"
- 用户说"初始化 openspec"、"spec init"
- 用户想刷新 `openspec/merged/` 下的产物

## 脚本结构

```
C:\Users\cmk\.claude\skills\spec-skill\scripts\
├── run_spec.py          ← 入口脚本（执行此文件）
└── spec_cli\
    ├── __init__.py
    ├── cli.py
    ├── config.py
    ├── github.py
    ├── merger.py
    ├── parser.py
    └── checker.py
```

## 项目根路径识别

脚本在 C 盘，项目可能在任意盘符（如 D 盘）。

**始终使用 `$(pwd)` 作为 `--root` 的值** —— Claude Code 的 Bash 工具从会话工作目录运行命令，`$(pwd)` 会在运行时自动展开为当前项目路径。

```
--root "$(pwd)"   将当前 shell 目录作为项目根传入，无论脚本在哪个盘都能正确识别。
```

内部原理：
1. `--root "$(pwd)"` → `os.chdir(项目根)` → Python 进程 cwd 切换
2. `find_config()` 调用 `Path.cwd()` 从项目根向上查找 `openspec/config.yaml`
3. 无需手动传 `--config`，自动发现

## 命令

### sync — 从 GitHub 拉取上层规范并生成产物

```bash
# 基本用法（GITHUB_TOKEN 从环境变量读取）
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync

# 显式传 token
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync --token <YOUR_TOKEN>

# 显式传 config 路径（覆盖自动查找）
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync --config openspec/config.yaml
```

### check — 验证 must 字段合规性

```bash
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" check

# JSON 格式输出
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" check --json
```

### init — 初始化 openspec/ 目录结构

```bash
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" init
```

## sync 执行步骤

1. 确保 `GITHUB_TOKEN` 已设置：
   ```bash
   export GITHUB_TOKEN=<your-token>
   # 或通过 --token 参数传入
   ```

2. 在项目目录下执行（`$(pwd)` 由 shell 自动展开为项目根路径）：
   ```bash
   python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync
   ```

3. 将生成的文件提交到仓库：
   ```
   openspec/merged/effective-spec.md
   openspec/merged/.spec-compliance.yaml
   openspec/.spec-lock.yaml
   ```

## sync 做了什么

`cli.py sync()` 执行流程：
- 读取 `openspec/config.yaml` 中的 `spec_sources`
- 通过 GitHub API 解析每个 source 的版本 tag
- 下载规范文件并解析需求/覆盖声明
- 合并各层级并生成合规产物
- 报告 must 需求数量及缺失 justification 的项

## 依赖

如缺少依赖包，执行以下命令安装：
```bash
pip install click requests pyyaml
```

## 常见问题

| 问题 | 解决方法 |
|------|----------|
| `GITHUB_TOKEN` 未设置 | 设置环境变量或使用 `--token` 参数 |
| `config.yaml` 找不到 | 先运行 `init` 命令，或检查 `--root` 路径是否正确 |
| 未声明 `spec_sources` | 编辑 `openspec/config.yaml` 添加 sources |
| `ModuleNotFoundError: click` | 执行 `pip install click requests pyyaml` |
| 使用了错误目录 | 始终传 `--root "$(pwd)"`，不要硬编码路径 |
| 找不到脚本 | 确认路径：`C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py` |
