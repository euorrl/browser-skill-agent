# Browser Skill Agent

用文字 Skill 定义任务，用 Playwright 操作浏览器的极简 Python 项目。

- 默认直接执行 Skill 的 `actions`，无需模型或 API 密钥。
- 添加 `--llm` 后，由模型读取页面文字并逐轮选择工具。
- 共用 22 个浏览器工具，支持语义定位、自定义下拉、动态等待、iframe、多标签页、上传和下载。
- 默认显示并保留浏览器；支持全程无界面、结束后才显示两种可选方式。

当前版本为 `0.1.0`。不包含图片输入、独立业务检查器、自动恢复模块或 ADK。网站流程写在 Skill 中，不写入通用工具。

## 快速开始

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

## 命令行参数

```powershell
.\.venv\Scripts\python -m browser_skill_agent --help
```

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `skill` | 必填 | SKILL.md 路径 |
| `--param name=value` | 无 | 任务参数，可重复使用；含空格时加引号 |
| `--llm` | 关闭 | 使用模型逐轮决策；默认顺序执行 actions |
| `--max-steps N` | 30 | 脚本步数或模型决策轮数上限 |
| `--headless` | 关闭 | 全程无窗口，不等待回车 |
| `--result-only` | 关闭 | 执行时窗口位于屏幕外，结束后显示同一会话 |
| `--keep-open` / `--no-keep-open` | 开启 | 可见浏览器结束后是否保留，默认回车后关闭 |
| `--profile-dir PATH` | 独立临时目录 | 指定跨次保留的浏览器会话目录 |
| `--json` | 关闭 | 最终结果以 JSON 输出，进度仍输出到 stderr |
| `--ignore-https-errors` | 关闭 | 仅忽略本次浏览器会话的 HTTPS 证书错误 |

`--headless` 与 `--result-only` 互斥；`--result-only` 不能与 `--no-keep-open` 组合。默认显示全部操作过程；`--result-only` 保留 DOM、输入值和标签页，不重新加载结果页，任务栏可能仍有浏览器图标。它不隐藏终端进度。

浏览器成功、受阻或执行异常后均可保留现场，前提是浏览器已成功启动且仍然存活。查看等待时间不计入任务耗时。终端输入关闭时自动退出；保留窗口需要终端进程继续运行。

`.env`、Skill 相对路径、相对 `--profile-dir` 和 `data/downloads` 均基于当前工作目录。默认每次运行创建独立临时会话，关闭后清理，不跨次保存 Cookie；不同任务可以同时保留窗口。需要复用会话时加 `--profile-dir data/profile`，同一个固定目录只能同时供一个浏览器进程使用。

## 启用 LLM

仅 `--llm` 模式需要模型配置。先创建本地配置，不覆盖已有密钥：

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

每轮都会请求模型，通常比脚本模式慢。最终统计服务端报告的输入、输出和总 Token；缺失统计时显示未知或不完整，不估算费用。当前每轮发送完整 Skill（包括 actions）、工具说明、页面快照和最近六次操作结果，详见 [架构与模型交互](docs/architecture.md)。

## 内置 Skill

| Skill | 用途 | 默认脚本 |
| --- | --- | --- |
| [chinese_encyclopedia_research](skills/chinese_encyclopedia_research/SKILL.md) | 中文高级搜索、排序、范围筛选、跨标签页调研 | 22 步，输出标题与短摘录 |
| [toolshop_filter_cart](skills/toolshop_filter_cart/SKILL.md) | 测试商城搜索、分类、排序和购物车 | 16 步，输出表格与数量 |
| [compare_python_releases](skills/compare_python_releases/SKILL.md) | 两个 Python 版本的官网资料查询 | 7 步，输出正文及文件行 |

```powershell
# 公开测试商城，不登录、不结账；任务要求购物车初始为空
.\.venv\Scripts\python -m browser_skill_agent skills/toolshop_filter_cart/SKILL.md --param keyword=pliers --param category=Pliers --param "product_name=Slip Joint Pliers" --param quantity=2 --result-only

# 读取两个版本的资料；加 --llm 才自动生成中文比较结论
.\.venv\Scripts\python -m browser_skill_agent skills/compare_python_releases/SKILL.md --param version_a=3.13.7 --param version_b=3.12.10 --param "package_name=Windows installer (64-bit)" --headless
```

版本号仅作查询示例，不是安装建议。在线网站可能改版、变更库存或无法访问；准确标题、定位器或预设条件不满足时会停止。Skill 使用参数复用同一类流程，不需要为每次点击或每组输入单独创建文件。编写格式见 [Skill 指南](docs/skills.md)。

## 输出与成功含义

中文进度写入 stderr，最终结果写入 stdout。默认不保存运行日志或逐轮模型请求。

| 状态 | 含义 | 退出码 |
| --- | --- | --- |
| `succeeded` | 脚本步骤及指定等待通过，或模型返回完成状态 | 0 |
| `blocked` | 脚本操作/等待受阻、达到上限，或模型报告无法继续 | 1 |
| `failed` | 配置、启动、接口或执行循环出现异常 | 1 |

参数格式错误由命令行解析器返回退出码 2。成功状态不代表独立核验了业务结果；读取摘录也不代表阅读全文。脚本结果的 `outputs` 包含读取数据与来源，模型总结位于 `message`。两种模式都提供 `mode`、`elapsed_seconds` 和 `usage`；正常执行结果包含 `turns` 和最终 `url`，启动异常时可能没有这些字段。

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
  output.py              # 中文进度、结果与 JSON 输出
  tools/                 # 定位、观察、交互、等待、导航、文件操作
skills/                  # 三个可复用任务，网站特定步骤放在这里
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
- **LLM 慢或用量大**：每轮重复传入上下文并等待响应；默认脚本不调用模型。当前没有请求缓存、持久任务记忆或逐轮耗时分析。
- **能力边界**：没有截图输入、验证码处理、系统原生窗口操作或任意 JavaScript 执行工具。虚拟列表、画布和复杂拖拽受网页实现限制。模型提示不支持密码输入任务；底层工具不是权限隔离沙箱，只运行可信 Skill。

## 许可证

[MIT](LICENSE)。
