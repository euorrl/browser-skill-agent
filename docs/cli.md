# 命令行使用

从项目根目录运行以下命令。安装步骤见 [README](../README.md)。

## 命令行参数

```powershell
.\.venv\Scripts\python -m browser_skill_agent --help
```

| 参数                                 | 默认值       | 作用                                              |
| ------------------------------------ | ------------ | ------------------------------------------------- |
| `skill`                            | 必填         | SKILL.md 路径                                     |
| `--param name=value`               | 无           | 任务参数，可重复使用；含空格时加引号              |
| `--llm`                            | 关闭         | 使用模型分批决策；默认顺序执行 actions            |
| `--approval human/ai/allow`        | human        | 关键操作人工确认、AI 审核或全部允许，独立于 --llm |
| `--max-steps N`                    | 30           | 执行步数上限；LLM 模式包含 finish 和无效计划      |
| `--headless`                       | 关闭         | 后台运行，可人工登录；结束后关闭                  |
| `--result-only`                    | 关闭         | 执行时窗口最小化，结束后显示同一会话          |
| `--keep-open` / `--no-keep-open` | 开启         | 可见浏览器结束后是否保留，默认回车后关闭          |
| `--profile-dir PATH`               | 独立临时目录 | 指定跨次保留的浏览器会话目录                      |
| `--json`                           | 关闭         | 最终结果以 JSON 输出，进度仍输出到 stderr         |
| `--ignore-https-errors`            | 关闭         | 仅忽略本次浏览器会话的 HTTPS 证书错误             |

`--headless` 与 `--result-only` 互斥；`--result-only` 不能与 `--no-keep-open` 组合。默认显示全部操作过程；`--result-only` 保留 DOM、输入值和标签页，不重新加载结果页，任务栏可能仍有浏览器图标。它不隐藏终端进度。运行中可从任务栏恢复窗口查看，不会再将窗口移到屏幕外。

浏览器成功、受阻或执行异常后均可保留现场，前提是浏览器已成功启动且仍然存活。查看等待时间不计入任务耗时。终端输入关闭时自动退出；保留窗口需要终端进程继续运行。

`.env`、Skill 相对路径、相对 `--profile-dir` 和 `files/downloads` 均基于当前工作目录。默认每次运行创建独立临时会话，关闭后清理，不跨次保存 Cookie；不同任务可以同时保留窗口。需要复用会话时加 `--profile-dir data/profile`，同一个固定目录只能同时供一个浏览器进程使用。

## 启用 LLM

`--llm` 或 `--approval ai` 需要模型配置。先创建本地配置，不覆盖已有密钥：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

在 `.env` 中填写：

```dotenv
MODEL_BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_API_KEY=你的密钥
MODEL_NAME=glm-5.3-flash
```

服务须兼容 Chat Completions，支持纯文字消息和 `response_format: {"type": "json_object"}`。程序自动向 BASE_URL 追加 `/chat/completions`。示例使用 [GLM-5.3-Flash](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash)，也可配置其他兼容服务。

```powershell
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_encyclopedia_research/SKILL.md --param "topic_a=人工智能" --param "topic_b=机器学习" --llm --result-only
```

每个阶段都会请求模型，通常比脚本模式慢。Skill 提供目标、完成证据和观察建议，LLM 根据实际页面决定连续操作及观察节点，不按固定步数拆分。阶段内可连续读取多份结果，完成计划后统一判断进展；需要立即依据新信息决策时，在动作顶层设置 `observe_after: true`；遇到操作/等待失败、导航、标签页变化或获准的关键操作也会提前交回模型，授权拒绝则停止任务。`--batch-size` 已移除，旧命令请删掉该参数；`--max-steps` 仍限制整个任务的执行步数，默认 30。最终统计服务端报告的输入、输出和总 Token；缺失统计时显示未知或不完整，不估算费用。每次发送去除脚本 actions 的 Skill、工具说明、最多 10,000 字符自动快照、最近六次操作、最近八份读取证据及上一阶段执行情况，详见 [架构与模型交互](architecture.md)。

## 文件上传与下载

使用 Skill 声明的普通参数，例如 `--param "file=报告.pdf"`、`--param "save_as=月度报告.csv"`。只有 file_params 明确映射的参数才参与文件配置；默认使用 files/uploads 和 files/downloads，与 data/profile 分开。专用上传下载 CLI 参数已移除。只允许上传本次选择的文件，同名下载自动加编号，详见 [文件管理](files.md)。

## 输出与成功含义

中文进度写入 stderr，最终结果写入 stdout。默认不保存运行日志或逐轮模型请求。

| 状态          | 含义                                            | 退出码 |
| ------------- | ----------------------------------------------- | ------ |
| `succeeded` | 脚本步骤及指定等待通过，或模型返回完成状态      | 0      |
| `blocked`   | 脚本操作/等待受阻、达到上限，或模型报告无法继续 | 1      |
| `failed`    | 配置、启动、接口或执行循环出现异常              | 1      |

参数格式错误由命令行解析器返回退出码 2。成功状态不代表独立核验了业务结果；读取摘录也不代表阅读全文。脚本结果的 `outputs` 包含读取数据与来源，模型总结位于 `message`。两种模式都提供 `mode`、`elapsed_seconds` 和 `usage`；正常执行结果包含 `turns` 和最终 `url`；LLM 模式的 turns/llm_calls 为模型调用次数，steps 为执行步数（含 finish 和无效计划），启动异常时可能没有这些字段。

需要保存本次运行，可自行重定向：

```powershell
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_encyclopedia_research/SKILL.md --param "topic_a=人工智能" --param "topic_b=机器学习" --headless --json > result.json 2> progress.log
```

## 常见问题与限制

- **浏览器启动立即关闭**：若使用固定 `--profile-dir`，检查是否仍有旧任务占用；关闭旧任务或换用不同目录。默认临时会话可避免此冲突。
- **窗口还在，终端没返回**：任务可能已经结束，正在等待回车；以最终状态为准。
- **定位到多个同名元素**：通过容器、可见性或真实标识缩小范围，不默认选择第一个。详见 [工具库](tools.md)。
- **页面尚未加载**：使用结果条件等待；短时 DOM 稳定不等于业务加载完成。脚本等待失败即停止，LLM 模式会收到错误并重新决策。
- **证书错误**：可信站点可加 `--ignore-https-errors`，不影响模型 API 的 TLS，也不能解决验证码、403 或登录权限。
- **LLM 慢或用量大**：每批重复传入上下文并等待响应；默认脚本不调用模型。读取证据只在本次运行内保留，当前没有请求缓存、跨次任务记忆或逐轮耗时分析。
- **能力边界**：没有截图输入、验证码处理、系统原生窗口操作或任意 JavaScript 执行工具。虚拟列表、画布和复杂拖拽受网页实现限制。账号密码由运行时保管，扫码或验证码交还用户；底层工具不是权限隔离沙箱，只运行可信 Skill。
