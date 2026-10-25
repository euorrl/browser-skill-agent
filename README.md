# Browser Skill Agent

用文字 Skill 定义任务，用 Playwright 操作浏览器的极简 Python 项目。

- 默认直接执行 Skill 的 `actions`，无需模型或 API 密钥。
- 添加 `--llm` 后，由模型读取页面文字，按阶段规划小批次工具操作。
- 关键操作默认由人工确认；`--approval ai` 改由模型审核，`--approval allow` 全部允许。
- 共用 22 个浏览器工具，支持语义定位、自定义下拉、动态等待、iframe、多标签页、上传和下载。
- 默认显示并保留浏览器；支持全程无界面、结束后才显示两种可选方式。

当前版本为 `0.1.0`。不包含图片输入或 ADK；后台验证支持固定结果验收与有限修复，普通运行不启用自动修复。网站流程写在 Skill 中，不写入通用工具。

## 快速开始

打开中文流程工作台，管理流程、对话填写参数或录制新流程：

```powershell
.\.venv\Scripts\python -m browser_skill_agent studio
```

工作台自动带入录制参数，录制使用独立浏览器，关闭录制浏览器后可选填生成指导，再生成流程；运行时可选择启用 LLM，默认关闭。详见[工作台说明](docs/studio.md)。

已录制的流程可生成 Skill 草稿（使用 `.env` 模型配置，不执行网页操作）：

```powershell
.\.venv\Scripts\python -m browser_skill_agent generate data/recordings/<录制编号>
```

草稿、演示参数与生成报告保存到 `skills/`。生成不等于执行验证；详见[生成说明](docs/generation.md)。

已验证环境：Windows、Microsoft Edge、Python 3.12。项目要求 Python 3.10+；当前 CLI 固定使用 Edge，其他系统尚未验证。

```powershell
git clone https://github.com/euorrl/browser-skill-agent.git
cd browser-skill-agent
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
```

系统须安装 Microsoft Edge，无需另行下载 Playwright Chromium。从项目根目录运行中文网站示例：

```powershell
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_encyclopedia_research/SKILL.md --param "topic_a=人工智能" --param "topic_b=机器学习"
```

默认执行 22 个脚本步骤，不调用 LLM。结果包含两个条目的标题、来源和各最多 600 字符的摘录。任务结束后窗口保持打开，回到终端按回车关闭。需要本机能访问中文维基百科。

也可使用 `.\.venv\Scripts\browser-skill-agent.exe`，参数相同。可编辑安装后，修改源码无需重新安装。

## 录制用户操作

从真实操作开始沉淀流程，先录制，再进入后续 Skill 生成阶段：

```powershell
.\.venv\Scripts\python -m browser_skill_agent record
```

输入网址 → 开始录制 → 正常操作网页 → 回到控制页结束并保存。支持带确认的“重新开始”，保留登录会话并隔离旧记录；网页已经发生的操作不会撤销。完整、连贯的演示有助于后续生成 Skill，不必为了流畅而加快操作。

记录保存到 `data/recordings/`，下载保存到 `files/recordings/`。当前只完成录制与记录，不调用 LLM，也不自动提取参数或生成 Skill。详见 [录制指南](docs/recording.md)。

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
| `--headless`                       | 关闭         | 全程无窗口，不等待回车                            |
| `--result-only`                    | 关闭         | 执行时窗口位于屏幕外，结束后显示同一会话          |
| `--keep-open` / `--no-keep-open` | 开启         | 可见浏览器结束后是否保留，默认回车后关闭          |
| `--profile-dir PATH`               | 独立临时目录 | 指定跨次保留的浏览器会话目录                      |
| `--json`                           | 关闭         | 最终结果以 JSON 输出，进度仍输出到 stderr         |
| `--ignore-https-errors`            | 关闭         | 仅忽略本次浏览器会话的 HTTPS 证书错误             |

`--headless` 与 `--result-only` 互斥；`--result-only` 不能与 `--no-keep-open` 组合。默认显示全部操作过程；`--result-only` 保留 DOM、输入值和标签页，不重新加载结果页，任务栏可能仍有浏览器图标。它不隐藏终端进度。

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

每个阶段都会请求模型，通常比脚本模式慢。Skill 提供目标、完成证据和观察建议，LLM 根据实际页面决定连续操作及观察节点，不按固定步数拆分。阶段内可连续读取多份结果，完成计划后统一判断进展；需要立即依据新信息决策时，在动作顶层设置 `observe_after: true`；遇到操作/等待失败、导航、标签页变化或获准的关键操作也会提前交回模型，授权拒绝则停止任务。`--batch-size` 已移除，旧命令请删掉该参数；`--max-steps` 仍限制整个任务的执行步数，默认 30。最终统计服务端报告的输入、输出和总 Token；缺失统计时显示未知或不完整，不估算费用。每次发送去除脚本 actions 的 Skill、工具说明、最多 10,000 字符自动快照、最近六次操作、最近八份读取证据及上一阶段执行情况，详见 [架构与模型交互](docs/architecture.md)。

## 文件上传与下载

使用 Skill 声明的普通参数，例如 `--param "file=报告.pdf"`、`--param "save_as=月度报告.csv"`。只有 file_params 明确映射的参数才参与文件配置；默认使用 files/uploads 和 files/downloads，与 data/profile 分开。专用上传下载 CLI 参数已移除。只允许上传本次选择的文件，同名下载自动加编号，详见 [文件管理](docs/files.md)。

## 内置 Skill

预期导航可以连续执行：模型动作声明 `expected_url` 且 `wait_after` 验证目标页面成功后，可紧接着读取正文，无需仅因导航额外请求模型。意外跳转、弹窗及关键操作仍交回控制，详见 [阶段与导航](docs/architecture.md)。模型规划开始、返回及 AI 授权请求使用独立的 `【LLM】` 分隔块显示，规划返回时附等待耗时。

授权规则、拒绝后的行为及三种模式的命令见 [操作授权](docs/authorization.md)。默认人工模式遇到关键操作，在终端输入 `y`、`yes` 或直接回车允许，输入 `n` 或其他内容拒绝；输入流关闭仍拒绝。结束后显示模式会临时展示当前页面供确认。AI 审核会增加请求和 Token 消耗，即使没有启用 `--llm`。

| Skill                                                                         | 用途                                               | 默认脚本                |
| ----------------------------------------------------------------------------- | -------------------------------------------------- | ----------------------- |
| [chinese_encyclopedia_research](skills/chinese_encyclopedia_research/SKILL.md) | 中文高级搜索、排序、范围筛选、跨标签页调研         | 22 步，输出标题与短摘录 |
| [vue_cn_navigation](skills/vue_cn_navigation/SKILL.md)                         | 中文文档计数器、提示遮挡处理、SPA 跳转及两次返回   | 13 步                   |
| [element_cn_remote_select](skills/element_cn_remote_select/SKILL.md)           | 中文组件文档异步候选、动态定位、下拉精确匹配       | 5 步                    |
| [chinese_image_file_pipeline](skills/chinese_image_file_pipeline/SKILL.md)     | 两个文件分别处理及批量处理，等待完成并保存四份 PNG | 16 步                   |
| [bejson_timestamp_precision](skills/bejson_timestamp_precision/SKILL.md)       | 单选切换、动态毫秒字段、数值填写和双向转换         | 17 步                   |
| [element_cn_collapse](skills/element_cn_collapse/SKILL.md)                     | 多面板展开、动画等待、独立折叠及状态读取           | 7 步                    |
| [element_cn_dialog](skills/element_cn_dialog/SKILL.md)                         | 模态弹窗打开、取消、重开、确认及关闭等待           | 8 步                    |

历史示例的命令、覆盖范围及实测结果见 [中文网站验证](docs/chinese-skills-validation.md)。 阶段连续读取修正后的十项双模式测试及历史对比见 [阶段执行评测](docs/stage-evaluation.md)。授权全部允许用于测试；平时可保留默认人工授权。上传测试文件只含生成的色彩图案，不接入图片模型。

网站特定流程放在 Skill，通用工具不硬编码站点。页面可能改版，定位或等待条件不满足应停止。Skill 编写格式见 [指南](docs/skills.md)。

## 后台验证与修复

创建流程后默认后台验证；保存默认参数或确认聊天修改后也自动重新验证。采用全部授权和独立会话，最多修复 2 次，只有同一版流程的脚本与 LLM 两种模式都通过固定验收条件才采用修复版。文件操作有重复次数上限；它不是操作系统安全沙箱，也不能保证所有参数都适用。详见[验证与修复](docs/sandbox.md)。

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

## 项目结构与开发验证

```text
src/browser_skill_agent/
  cli.py                 # 命令行、模型配置、浏览器生命周期
  browser_display.py     # 结束后显示原浏览器窗口
  skill.py               # YAML 与正文加载、字符串参数绑定
  runtime.py             # 脚本执行、模型决策、Token 累计
  approval.py            # 关键操作识别、人工确认与 AI 审核
  output.py              # 中文进度、结果与 JSON 输出
  tools/                 # 定位、观察、交互、等待、导航、文件操作
skills/                  # 中文网站任务与组件场景，网站特定步骤放在这里
tests/                   # 本地真实 Edge + 模拟模型验证
docs/                    # 架构、Skill、工具和开发说明
pyproject.toml           # 包配置、依赖及 CLI 入口
.env.example             # 不含密钥的模型配置模板
```

开发验证和提交范围见 [开发指南](docs/development.md)。测试不需要模型密钥或公网服务，但需要安装 Edge，部分测试会短暂显示窗口。

## 常见问题与限制

- **浏览器启动立即关闭**：若使用固定 `--profile-dir`，检查是否仍有旧任务占用；关闭旧任务或换用不同目录。默认临时会话可避免此冲突。
- **窗口还在，终端没返回**：任务可能已经结束，正在等待回车；以最终状态为准。
- **定位到多个同名元素**：通过容器、可见性或真实标识缩小范围，不默认选择第一个。详见 [工具库](docs/tools.md)。
- **页面尚未加载**：使用结果条件等待；短时 DOM 稳定不等于业务加载完成。脚本等待失败即停止，LLM 模式会收到错误并重新决策。
- **证书错误**：可信站点可加 `--ignore-https-errors`，不影响模型 API 的 TLS，也不能解决验证码、403 或登录权限。
- **LLM 慢或用量大**：每批重复传入上下文并等待响应；默认脚本不调用模型。读取证据只在本次运行内保留，当前没有请求缓存、跨次任务记忆或逐轮耗时分析。
- **能力边界**：没有截图输入、验证码处理、系统原生窗口操作或任意 JavaScript 执行工具。虚拟列表、画布和复杂拖拽受网页实现限制。模型提示不支持密码输入任务；底层工具不是权限隔离沙箱，只运行可信 Skill。

## 许可证

[MIT](LICENSE)。
