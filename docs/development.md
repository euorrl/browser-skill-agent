# 开发与提交指南

## 环境和验证

在项目根目录完成 README 中的可编辑安装。测试使用本机 Microsoft Edge 和本地页面，模型请求通过 HTTP mock 验证，不需要 .env 密钥或公网网站。

```powershell
.\.venv\Scripts\python tests/smoke.py
.\.venv\Scripts\python tests/browser_tools.py
.\.venv\Scripts\python tests/dynamic_page.py
.\.venv\Scripts\python tests/script_mode.py
.\.venv\Scripts\python tests/browser_lifecycle.py
.\.venv\Scripts\python tests/browser_display.py
git diff --check
```

| 脚本 | 覆盖内容 |
| --- | --- |
| smoke.py | Skill 参数绑定、模型 HTTP 适配、工具错误回传和执行次数上限 |
| browser_tools.py | 原生/自定义下拉、容器定位、iframe、标签页、弹窗、上传下载 |
| dynamic_page.py | DOM 替换、隐藏副本、延迟启用、遮挡、列表重排及等待失败不重放 |
| script_mode.py | 默认无密钥 CLI、动态响应等待、脚本中止、Token 累计和缺失统计 |
| browser_lifecycle.py | 结果先输出、保留/关闭窗口、并发独立会话、固定目录和 CLI 显示模式 |
| browser_display.py | 屏幕外执行、标签页切换、结束后恢复窗口且保留 DOM/输入值 |

后两项会短暂显示测试窗口，测试结束自行关闭。测试不是产品运行时的独立业务检查器，也不能保证任意线上网站或模型均可完成任务。

在线验证应显式运行对应 Skill。默认脚本不消耗模型 Token；`--llm` 会调用真实服务。已在开发过程中验证三个内置 Skill 的脚本流程；页面、库存、网络和模型响应可能变化，历史耗时不作为性能保证。

## 修改约定

- 面向用户的说明、注释与 prompt 使用中文；接口名称、字段名保持英文。
- 新网站的流程优先写在 Skill 中；只把可复用的操作能力加入 tools。
- 修改工具时同步更新 tools/help.py、docs/tools.md，必要时补充能证明行为的测试。
- 不引入图片、ADK 或独立检查/恢复模块来扩大当前功能范围。

## 提交范围

本次首个功能提交包含：`.gitignore`、`.env.example`、`pyproject.toml`、`README.md`、`src/`、`skills/`、`tests/`、`docs/`。现有 LICENSE 保持不变。

不包含：真实 `.env`、`.venv/`、`data/`、`.cache/`、`__pycache__/`、本机结果文件和运行日志。分享日志或提交结果文件前留意其网页内容、路径与会话信息。不要将真实 API 密钥写入示例配置。

仓库已有基础 Initial commit；这里的“首次提交”指首次加入可运行实现。建议采用 Conventional Commits 风格：

```text
feat: 实现 Skill 驱动的浏览器执行器

- 支持默认脚本执行和可选 LLM 决策，统计服务端 Token 用量
- 提供语义定位、动态等待、多标签页及文件操作工具
- 支持三种窗口显示方式、结束后保留及独立浏览器会话
- 添加三个参数化 Skill、中文文档和本地浏览器测试
```

提交前检查 diff、测试结果和暂存范围。是否暂存、提交和推送由维护者决定；文档中的示例不是自动执行指令。
