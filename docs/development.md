# 开发与提交指南

## 环境和验证

在项目根目录完成 README 中的可编辑安装。下面的本地回归测试使用本机 Microsoft Edge 和本地页面，模型请求使用预设响应或 HTTP mock，不需要 .env 密钥或公网网站。真实网站评测见下方“在线评测”，LLM 模式会产生真实用量。

```powershell
.\.venv\Scripts\python tests/recording.py
.\.venv\Scripts\python tests/smoke.py
.\.venv\Scripts\python tests/llm_batches.py
.\.venv\Scripts\python tests/stage_navigation.py
.\.venv\Scripts\python tests/approval.py
.\.venv\Scripts\python tests/browser_tools.py
.\.venv\Scripts\python tests/file_paths.py
.\.venv\Scripts\python tests/dynamic_page.py
.\.venv\Scripts\python tests/script_mode.py
.\.venv\Scripts\python tests/browser_lifecycle.py
.\.venv\Scripts\python tests/browser_display.py
git diff --check
```

| 脚本 | 覆盖内容 |
| --- | --- |
| llm_batches.py | 可变长度阶段、未知组件观察、失败、显式观察/导航边界和多次读取连续执行、总预算、历史证据及上下文裁剪 |
| stage_navigation.py | 预期导航及新建/切换标签页连续读取，URL 不符、等待缺失/失败和意外弹窗中断 |
| approval.py | 三种授权策略、拒绝无副作用、对象变化、批次停止和审核 Token |
| recording.py | 录制控制、用户事件、动态状态、文件、跨源框架、重启隔离和密码遮蔽 |
| smoke.py | Skill 参数绑定、模型 HTTP 适配、工具错误回传和执行次数上限 |
| browser_tools.py | 原生/自定义下拉、容器定位、iframe、标签页、弹窗、上传下载 |
| file_paths.py | 上传范围、授权拒绝、文件编号、下载命名、同名避让和 CLI 文件参数 |
| dynamic_page.py | DOM 替换、隐藏副本、延迟启用、遮挡、列表重排及等待失败不重放 |
| script_mode.py | 默认无密钥 CLI、动态响应等待、脚本中止、Token 累计和缺失统计 |
| browser_lifecycle.py | 结果先输出、保留/关闭窗口、并发独立会话、固定目录和 CLI 显示模式 |
| browser_display.py | 屏幕外执行、标签页切换、结束后恢复窗口且保留 DOM/输入值 |

后两项会短暂显示测试窗口，测试结束自行关闭。测试不是产品运行时的独立业务检查器，也不能保证任意线上网站或模型均可完成任务。

在线验证应显式运行对应 Skill。默认脚本不消耗模型 Token；`--llm` 或 `--approval ai` 会调用真实服务。默认关键操作需要人工确认，无人值守测试需明确选择授权策略。历史中文 Skill 验证见 [中文网站验证](chinese-skills-validation.md)，阶段修正后的全量结果见 [阶段执行评测](stage-evaluation.md)；页面、库存、网络和模型响应可能变化，历史耗时不作为性能保证。

## 修改约定

- 面向用户的说明、注释与 prompt 使用中文；接口名称、字段名保持英文。
- 新网站的流程优先写在 Skill 中；只把可复用的操作能力加入 tools。
- 修改工具时同步更新 tools/help.py、docs/tools.md，必要时补充能证明行为的测试。
- 不引入图片、ADK 或独立检查/恢复模块来扩大当前功能范围。

## 在线评测

先在项目根目录生成不包含用户数据的两个样本 PNG；已有同名文件不会覆盖，评测会校验样本哈希：

```powershell
.\.venv\Scripts\python examples/prepare_sample_files.py
.\.venv\Scripts\python tests/evaluate_skills.py --modes script
```

需要完整双模式评测时，先配置 `.env` 中的模型，再执行：

```powershell
.\.venv\Scripts\python tests/evaluate_skills.py
```

默认依次运行 script 和 llm，覆盖当前全部 10 个 Skill；固定 allow 授权，每种模式最多两个独立浏览器并行，不自动重试失败任务。LLM 模式会调用真实服务并产生 Token 消耗。北京时间转换场景要求本机时区与 Skill 的 Asia/Shanghai 基准一致。

单独运行一个案例：

```powershell
.\.venv\Scripts\python tests/live_chinese_skills.py --skill element_cn_tabs --mode script
.\.venv\Scripts\python tests/live_chinese_skills.py --skill element_cn_tabs --mode llm
```

全量报告默认保存于 `.cache/stage-evaluation-时间/`；单项报告默认保存于 `.cache/live-validation/`。两种入口均可用 `--report-root` 指定报告目录。每次单项运行包含 report.json、trace.json、stages.json 和 progress.log；全量入口额外写入 index.json。stages.json 记录模型决策、请求耗时和上一阶段状态，不保存完整请求上下文或密钥。脚本模式的 stages.json 为空列表。

通过要求 Runtime 正常报告成功且测试端独立核验通过；任一案例失败，全量入口返回非零退出码。即使网页动作已经完成，最终模型总结超时仍算整轮失败。测试端核验不是产品运行时新增的业务检查模块。最新报告见 [阶段执行评测](stage-evaluation.md)；该文档及 JSON 汇总是一次评测快照，不会在每次运行后自动更新。

## 提交范围

按当前差异选择需要提交的源码、Skill、测试、示例和文档；不要沿用某次历史提交的文件清单。提交公开的评测结论可以包含文档和不含密钥的汇总 JSON，原始运行记录仍留在本地。

不包含：真实 `.env`、`.venv/`、`data/`、`files/`、`.cache/`、`__pycache__/`、本机上传下载结果和运行日志。分享记录前检查网页内容、路径与会话信息，不把真实 API 密钥写入示例配置。

建议使用 Conventional Commits：功能使用 `feat`，行为修正使用 `fix`，仅文档调整使用 `docs`。标题写具体改变，正文说明执行边界与验证结果，不将重测通过写成首次全部成功，也不将局部文件核验通过写成整轮模型任务成功。

提交前检查 diff、测试结果和暂存范围。暂存、提交和推送是独立操作，文档中的命令示例不是自动执行指令。
