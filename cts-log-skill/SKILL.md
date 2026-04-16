---
name: cts-log-skill
description: 分析 Android CTS 用例失败原因。输入：完整日志文件 + 用例代码 + 执行结果。自动将日志切片（默认 5000 行/片），逐片分析并压缩上下文，最终给出根因定位与解决方案。
---

# cts-log-skill — Android CTS 日志分析

## 概述

CTS 日志通常数万行，无法一次性分析。本 skill 采用**滚动上下文**策略：

1. 切分日志 → 多个片段
2. 逐片分析，每片结束后**压缩上下文**
3. 用压缩后的上下文 + 下一片段继续分析
4. 所有片段分析完毕后，输出**根因 + 解决方案**

脚本路径：
```
C:\Users\cmk\.claude\skills\cts-log-skill\scripts\split_log.py
```

---

## 触发时机

- 用户说"分析 CTS 日志"、"CTS 用例失败了"、"帮我看看 CTS 报错"
- 用户提供了日志文件路径、用例代码、或执行结果
- 用户想定位 Android CTS/GTS/VTS 测试失败的根因

---

## 必要输入

| 输入 | 说明 | 是否必须 |
|------|------|---------|
| 日志文件路径 | 完整的 CTS log 文件（`.txt` / `.log`） | **必须** |
| 用例代码 | 失败用例的源码或文件路径 | 推荐（有助于精准定位） |
| 执行结果 | `PASS`/`FAIL` 概览、错误摘要 | 推荐 |
| `--chunk-size` | 每片行数，默认 5000 | 可选 |

如用户未提供日志文件路径，**先询问**，再执行后续步骤。

---

## 执行流程

### 第 0 步：收集输入

确认以下信息已就绪：
- `LOG_FILE`：日志文件绝对路径
- `TEST_CODE`：用例代码内容或路径
- `TEST_RESULT`：执行结果摘要
- `CHUNK_SIZE`：片段大小（默认 5000）

---

### 第 1 步：切分日志

```bash
python "C:\Users\cmk\.claude\skills\cts-log-skill\scripts\split_log.py" \
    "<LOG_FILE>" \
    --chunk-size <CHUNK_SIZE>
```

- 脚本会在 `C:\Users\cmk\.claude\skills\cts-log-skill\workspace\<日志文件名>\` 下生成：
  - `chunk_001_of_NNN.log` … `chunk_NNN_of_NNN.log`
  - `split_summary.json`（包含总行数、片段数、各片段路径）
- 读取 `split_summary.json` 获取 `chunk_files` 列表和 `total_chunks`

---

### 第 2 步：初始化分析状态

```
running_summary = ""          # 滚动压缩上下文，初始为空
current_chunk_index = 1
total_chunks = N              # 从 split_summary.json 读取
```

---

### 第 3 步：逐片分析循环

对每个片段 `chunk_i`（i = 1 … N）执行：

#### 3a. 读取片段内容

使用 Read 工具读取 `chunk_i` 的文件内容。

#### 3b. 分析当前片段

用以下提示词结构进行分析（**在当前对话中直接推理，不需要新建对话**）：

```
【分析任务】Android CTS 日志分析 —— 片段 {i}/{N}

【用例代码】
{TEST_CODE}

【执行结果】
{TEST_RESULT}

【已有分析摘要】（前 {i-1} 片段的压缩结论，首片为空）
{running_summary}

【当前日志片段 {i}/{N}】
{chunk_content}

【分析要求】
1. 结合用例代码和执行结果，从当前片段中提取与失败相关的关键信息：
   - 异常堆栈（Exception / Error / Crash）
   - FAIL 标记行及上下文
   - 关键 logcat 错误（E/W 级别）
   - 与用例逻辑直接相关的日志
2. 基于已有摘要 + 当前片段，更新根因假设
3. 如已能确定根因，明确说明；否则描述当前线索和待验证假设
4. 输出本片段分析结论（200~400 字）
```

#### 3c. 压缩上下文

每片分析完毕后，立即用以下提示词**压缩** running_summary：

```
【上下文压缩任务】

【旧摘要】
{running_summary}

【本片段（{i}/{N}）分析结论】
{current_chunk_analysis}

【压缩要求】
将旧摘要与本片段结论合并，输出一份精炼摘要（300 字以内）：
- 保留最重要的根因线索和异常信息
- 丢弃重复、无关的细节
- 记录当前根因假设状态（已确认 / 待验证 / 无线索）
- 格式：纯文本，不需要 Markdown 标题
```

将压缩结果赋值给 `running_summary`，继续下一片。

---

### 第 4 步：输出最终报告

所有片段分析完毕后，基于最终 `running_summary` 输出完整报告：

```
【最终分析报告】

## 问题概述
<用例名称、失败现象简述>

## 根因定位
<精确的失败原因，引用关键日志行或堆栈>

## 证据链
<按时间/逻辑顺序列出支撑根因的关键日志片段>

## 解决方案
<具体可操作的修复步骤，按优先级排列>

## 验证方法
<如何确认修复是否有效>

## 补充说明
<不确定点、潜在相关问题、或需要进一步信息>
```

---

## 注意事项

### 关键日志特征（重点关注）

```
# 异常和崩溃
java.lang.* Exception
android.test.* Error
FATAL EXCEPTION
Process: ... crashed

# CTS 框架
FAIL:
Test failed
AssertionError
junit.framework.AssertionFailedError

# 系统级错误
E AndroidRuntime
E ActivityManager
W System.err

# 超时
TimeoutException
TIMEOUT

# 权限问题
SecurityException
Permission denied

# 设备状态
Device not found
adb: error
```

### 分析优先级

1. **堆栈追踪** — 直接指向失败代码位置
2. **Assert 错误** — 期望值 vs 实际值
3. **E/F 级 logcat** — 系统级错误
4. **测试框架日志** — CTS runner 输出
5. **W 级 logcat** — 潜在问题警告

### 上下文压缩原则

- **保留**：异常类型、失败行号、关键错误消息、根因假设
- **丢弃**：正常运行的日志、重复的 INFO 级别输出、已排除的假设
- **标注**：不确定的线索用 `[?]` 标记

---

## 命令参考

```bash
# 基本用法（5000 行/片）
python "C:\Users\cmk\.claude\skills\cts-log-skill\scripts\split_log.py" "D:\logs\cts_result.log"

# 自定义片段大小
python "C:\Users\cmk\.claude\skills\cts-log-skill\scripts\split_log.py" "D:\logs\cts_result.log" --chunk-size 3000

# 自定义输出目录
python "C:\Users\cmk\.claude\skills\cts-log-skill\scripts\split_log.py" "D:\logs\cts_result.log" -o "D:\logs\chunks"

# 仅输出文件路径列表
python "C:\Users\cmk\.claude\skills\cts-log-skill\scripts\split_log.py" "D:\logs\cts_result.log" --list-only
```

---

## 目录结构

```
C:\Users\cmk\.claude\skills\cts-log-skill\
├── SKILL.md
├── scripts\
│   └── split_log.py          ← 日志切分脚本
└── workspace\                ← 运行时自动创建
    └── <日志文件名>\
        ├── chunk_001_of_NNN.log
        ├── chunk_002_of_NNN.log
        ├── ...
        └── split_summary.json
```
