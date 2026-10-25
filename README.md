# Browser Skill Agent

基于 Python 和 Playwright 的本地浏览器流程自动化项目。支持录制网页操作、生成可编辑的 Skill、配置参数执行流程，以及在工作台中管理和定时运行任务。

默认按固定步骤执行，不调用 LLM。生成流程、对话配置、AI 授权和模型执行使用 `.env` 中配置的模型服务。

## 功能

| 功能 | 说明 |
| --- | --- |
| 流程工作台 | 管理流程、配置参数、查看结果与日志、重命名和删除 |
| 操作录制 | 独立浏览器录制，记录操作、页面变化、标签页及文件事件 |
| Skill 生成 | 根据录制和可选说明提取参数、生成步骤与阶段定义 |
| 两种执行模式 | 默认顺序执行 `actions`；可选 LLM 根据页面文字按阶段规划 |
| 授权与登录 | 关键操作支持人工确认、AI 审核或全部允许；支持登录接管 |
| 计划与定时 | 预先配置参数与运行选项，在指定时间执行一次 |
| 验证与修复 | 独立会话执行、结果检查、失败诊断和有限次数修复 |
| 浏览器工具 | 动态等待、容器定位、iframe、多标签页、下拉筛选及上传下载 |

当前版本为 `0.1.0`。录制生成的流程需要验证，不能保证任意网站一次生成即可运行。步骤执行完成、业务结果核验和双模式验证是不同状态。项目不包含截图模型输入，也不依赖 ADK。

## 安装

已验证环境：Windows、Python 3.12、Microsoft Edge。项目要求 Python 3.10+，当前浏览器入口使用 Edge；其他系统尚未验证。

```powershell
git clone https://github.com/euorrl/browser-skill-agent.git
cd browser-skill-agent
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
```

系统需安装 Microsoft Edge，无需另行下载 Playwright Chromium。后续命令均在项目根目录执行。

## 启动工作台

```powershell
.\.venv\Scripts\python -m browser_skill_agent studio
```

工作台在本地 Edge 页面中运行，无需 Node.js、前端构建或额外 Web 服务。

1. 在“我的流程”中选择已有流程，检查参数和授权方式后运行。
2. 点击“录制新流程”，在独立浏览器中操作；关闭录制浏览器后，可选填名称、任务说明与参数建议，再生成流程。
3. 查看执行日志和结果；需要调整时，可编辑默认参数或通过右侧对话提出修改要求。
4. 在“计划与定时”中选择流程，配置参数、执行时间和运行选项后保存。

定时功能要求工作台保持打开、电脑处于唤醒状态。关闭期间错过的计划不会自动补跑。详细行为见 [工作台使用](docs/studio.md)。

## 配置模型（可选）

执行已有流程的固定步骤不需要模型配置。生成流程、对话和验证修复等功能需要兼容 Chat Completions 的服务。

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

在 `.env` 中填写服务地址、API 密钥和模型名称，配置项见 [.env.example](.env.example)。配置不会提交到 Git。模型服务需支持文字消息和 JSON 对象响应；相关页面文字、录制摘要或流程定义会按使用功能发送到该服务。

## 命令行运行

直接执行现有流程：

```powershell
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_encyclopedia_research/SKILL.md --param "topic_a=人工智能" --param "topic_b=机器学习"
```

默认显示浏览器、使用人工关键操作授权，结束后保留窗口。回到终端按回车关闭。此示例需要本机能够访问中文维基百科。

常用选项：

| 参数 | 用途 |
| --- | --- |
| `--llm` | 启用模型执行，默认关闭 |
| `--approval human/ai/allow` | 选择关键操作授权方式，默认 `human` |
| `--max-steps 30` | 设置执行步数上限，不是模型调用次数 |
| `--headless` / `--result-only` | 后台运行或结束后显示结果页面 |
| `--no-keep-open` | 执行结束后关闭浏览器 |
| `--json` | 将最终结果以 JSON 写入标准输出 |

更多参数、输出字段和问题排查见 [命令行使用](docs/cli.md)。录制、生成与验证分别使用 `record`、`generate`、`validate` 子命令，详见对应文档。

## 项目结构

```text
src/browser_skill_agent/
├── cli.py                 # 命令行入口
├── skill.py               # Skill 解析与参数绑定
├── runtime.py             # 固定步骤与 LLM 执行
├── tools/                 # 浏览器工具与定位、等待、文件操作
├── recording/             # 用户操作录制与记录
├── generation/            # 录制摘要、模型生成及格式校验
├── sandbox/               # 执行验证、诊断与有限修复
└── studio/                # 本地工作台、流程存储与定时计划
skills/                    # 流程定义与示例参数
tests/                     # 本地测试和在线验证脚本
docs/                      # 使用、开发和历史验证文档
data/                      # 本地录制、索引、计划和验证报告（不提交）
files/                     # 上传、下载与录制文件（不提交）
```

`skills/<目录>/SKILL.md` 是流程执行定义，`example_params.json` 保存示例参数。工作台将示例参数作为默认值；普通执行 CLI 通过 `--param` 显式传入参数。密码只保留在当前工作台会话内，不写入流程文件。

## 示例与验证范围

仓库包含百科查询、文档导航、日期转换、折叠面板和弹窗等示例，具体定义见 [skills/](skills/)。网站页面可能变化，历史测试通过不代表当前所有参数均可运行。

B 站分享示例含手工修正，其脚本实测结果不能作为自动生成能力的证明。各示例与历史测试的来源和范围见 [验证记录索引](docs/README.md#验证记录)。

## 开发与测试

安装采用可编辑模式，修改 Python 源码后无需重新安装；已运行的工作台需要重启。

```powershell
.\.venv\Scripts\python tests/generation.py
.\.venv\Scripts\python tests/sandbox_contract.py
.\.venv\Scripts\python tests/studio_schedules.py
```

上述测试不请求真实模型；浏览器测试需要 Edge。测试分组、在线测试及提交约定见 [开发指南](docs/development.md)。

## 文档

- [文档索引](docs/README.md)：按使用、开发和验证记录分类。
- [工作台](docs/studio.md) · [命令行](docs/cli.md)
- [录制](docs/recording.md) · [生成](docs/generation.md) · [验证与修复](docs/sandbox.md)
- [Skill 格式](docs/skills.md) · [工具库](docs/tools.md) · [架构](docs/architecture.md)
- [操作授权](docs/authorization.md) · [登录接管](docs/login.md) · [文件管理](docs/files.md)

## 使用边界

这是本地单用户应用。同一工作台一次执行一个任务；保留任务浏览器会占用执行位置。验证模块使用独立浏览器和文件目录，但不是操作系统安全沙箱，不能撤销网站上的真实提交。验证码和扫码交由用户完成；不提供任意 JavaScript 执行或系统原生窗口自动化工具。

## 许可证

[MIT](LICENSE)。
