# 从录制生成 Skill 草稿

生成入口复用 `.env` 中的 `MODEL_BASE_URL`、`MODEL_API_KEY` 和 `MODEL_NAME`，正常调用一次文字模型；仅当完整输出存在结构或工具签名错误时，额外进行一次格式修正。生成过程不打开浏览器、不执行网站操作，也不自动迭代浏览器验证。

```powershell
.\.venv\Scripts\python -m browser_skill_agent generate data/recordings/<录制编号>
```

必须先在录制控制页“结束并保存”。仅接受 `schema_version: 1` 且状态为 `completed` 的记录。

生成采用流式接收，连接后定期显示等待时间和正文字符数，不展示或保存推理内容。GLM-5.3/GLM-5.3-Flash 使用 `reasoning_effort: low`，其他模型不发送该参数。输出预算为 16384 Token（服务端可能将推理计入预算）；截断、断流或缺少正常结束标记时不保存不完整草稿。

推理参数依据 [Z.AI 官方思考模式说明](https://docs.z.ai/guides/capabilities/thinking)。不通过 `thinking: disabled` 关闭 GLM-5.3 系列的强制思考。

模型读取超时及流式接收过程的总时长检查默认 300 秒，可用 `--timeout 600` 调整。总时长在收到数据时检查，阻塞读取仍受读取超时限制。请求失败不会自动重试；超时不意味着服务端未处理或未计费，未返回用量时不能判断 Token 消耗。

默认输出到 `data/generated/<skill名称>-<随机编号>/`，不会覆盖已有 Skill。可使用 `--output-dir skills/drafts` 更换父目录；指定目录会保存含演示值的文件，提交前请检查内容。

生成目录包含：

- `SKILL.md`：兼容现有加载器的 YAML 配置及中文正文，包含参数、脚本动作与 LLM 阶段。
- `example_params.json`：录制中的非敏感演示参数，供用户参考，不是 runtime 自动加载的默认值。
- `generation.json`：录制来源、状态、假设、事件证据映射、待解决问题及服务端报告的 Token 用量。`validated: false` 表示未进行真实执行验证。

## 流程与边界

程序使用合并动作，补充原始流中的导航、页面、文件及异常事件。每个动作选取首尾两份已保存观察，长字符串在 1600 字符处标记截断。超过 140000 字符的摘要直接提示任务过大，不静默丢弃后续操作。

通用 Prompt 依据值的业务作用选择参数，区分任务输入、流程常量、运行时数据、环境前提与偶然内容，不针对特定网站。模型输出 JSON，程序检查基本结构、参数引用和工具签名后转换为 Markdown。检查通过不代表定位唯一、网站状态符合预期或任务已成功。

状态含义：

若模型的证据映射引用不存在的录制动作，程序剔除无效引用并记录待解决问题，草稿不能标为 `draft`；不会将虚构引用当成真实证据。

格式修正至多一次，原因写入 `format_corrections`，两次请求用量累计。修正后仍无效时，在 `invalid-<编号>/generation.json` 保存模型输出及诊断，不生成 `SKILL.md`。网络失败不触发自动重试。

| 状态 | 含义 |
| --- | --- |
| `draft` | 已形成草稿，尚未执行验证 |
| `needs_evidence` | 缺少影响执行或结果判断的证据 |
| `unsupported` | 必要流程超出现有 runtime 的表达能力 |

当前脚本模式不支持通用条件分支、循环、读取结果变量绑定及跨运行的录制标签页编号映射。生成器会向模型明确这些限制，不新增执行语法。缺少文件路径或敏感值时不编造示例，生成报告列出缺口。

生成会将整理后的录制资料发送到配置的模型服务。录制器已识别的敏感字段会遮蔽，但普通页面正文和普通输入可能包含个人信息；生成阶段不保证通用脱敏。

生成完成后查看报告，按照 `example_params.json` 手动传入参数，使用原有命令测试。例如：

```powershell
.\.venv\Scripts\python -m browser_skill_agent data/generated/<名称>/SKILL.md --param "query=示例"
.\.venv\Scripts\python -m browser_skill_agent data/generated/<名称>/SKILL.md --param "query=示例" --llm
```

参数名取决于实际生成结果。需要证据补充或缺少 runtime 能力的草稿应先修正，不能因为文件已生成就认为两种模式可运行。上传、发送等操作仍使用现有授权策略。

## 开发与验证

`generation/prompt.py` 保存固定生成规则与 runtime 约束；`generation/generator.py` 负责摘要、格式校验、落盘和 CLI；`generation/model.py` 继承现有模型配置与用量结构，处理长草稿流式传输。现有任务执行模型调用不变，不新增依赖。

```powershell
.\.venv\Scripts\python tests/generation.py
```

测试使用模拟 HTTP 模型响应，验证参数替换、生成后加载、文件隔离、截断提示、敏感字段、无效工具及不完整录制处理，不消耗真实 Token。不等同于生成 Skill 的真实网站验收。

## 录制后的可选指导

工作台在录制保存后提供三个选填字段：中文流程名称、流程描述、参数建议。用户可以全部留空直接生成，不要求列举或确认每个参数。

生成器通过独立的 `user_guidance` 字段传给模型，并在 `generation.json` 中保留指导。指定名称作为显示名称；描述用于澄清目标，参数建议用于区分可变输入和固定设置。默认值仍依据真实录制，不将用户愿望当作已执行证据；超出录制范围的要求应写入待解决问题。一次格式修正及工作台生成重试也会保留指导。CLI 的原有无指导生成命令保持不变。
