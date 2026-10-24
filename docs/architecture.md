# 架构与模型交互

## 模块职责

| 文件 | 职责 |
| --- | --- |
| `cli.py` | 解析参数、加载模型配置、启动并关闭 Edge、汇总输出 |
| `browser_display.py` | 通过 CDP 控制本任务窗口位置，结束后显示同一会话 |
| `skill.py` | 解析 YAML 和 Markdown 正文，绑定字符串参数 |
| `runtime.py` | 顺序脚本或阶段批次循环；模型 API 调用、读取证据和 Token 累计 |
| `approval.py` | 工具执行前的规则判断、人工/AI 授权与拒绝记录 |
| `output.py` | 中文进度、结果显示及 JSON 输出 |
| `tools/registry.py` | 工具白名单、统一结果、动作后的条件/响应等待 |
| `tools/session.py` | 当前页、框架、语义定位、控件可操作等待、原生弹窗策略 |
| `tools/observe.py` | 页面文字快照、候选元素与精确读取 |
| `tools/readiness.py` | 有界 DOM 稳定性提示，不判断业务成功 |
| `tools/actions.py` | 点击、输入、选择、勾选、滚动、拖动 |
| `tools/waiting.py` | 定时等待与条件等待 |
| `tools/navigation.py` | 导航、标签页、弹窗策略设置 |
| `tools/files.py` | 文件输入控件上传与下载保存 |
| `tools/help.py` | 给模型的中文工具说明 |

## 调用链

```text
CLI → load_skill → 创建独立浏览器上下文
                   ├─ 默认：start → actions → 工具/条件等待 → 收集读取结果
                   └─ --llm：start → observe → 模型规划 → 一批工具 → 下一轮
                                      ↑                 │
                                      └─ 最近六次结果 ──┘
                   → 输出状态、耗时、Token → 可选显示/保留窗口 → 关闭
```

自动创建的临时用户目录由 Playwright 管理。`--profile-dir` 显式选择固定目录时跨次保存状态，但不能同时被两个浏览器进程占用。`--result-only` 使用有界面 Edge，将窗口暂放屏幕外，最终移回，不通过重新加载页面重建结果。

## 每轮 LLM 输入

CLI 在工具入口安装授权策略，先审核再执行；拒绝后 Runtime 直接结束任务。批准的关键操作执行后也结束 LLM 批次，重新观察。策略与模型规划独立，详见 [操作授权](authorization.md)。这里描述的每轮输入是执行规划；AI 授权使用独立审核提示与请求。

调用兼容 Chat Completions 的 HTTP 接口，非流式请求，不使用模型 SDK 或原生 tools/function calling 字段。请求体包含 model、messages 和 `response_format: {"type":"json_object"}`。

messages 每轮只有两条：

1. system：中文执行规则 + 22 个工具的说明。
2. user：当前 state 的 JSON 字符串，包括 skill、page、recent_actions、evidence、last_stage、steps_left 和兼容字段 turns_left。

skill 含绑定后的元信息、stages、params 和正文 instructions，不发送脚本 actions。page 含 URL、最多 10,000 字符的自动文字快照、truncated、标签页和框架编号、最近弹窗记录及 readiness。recent_actions 只保留最近六次操作与工具结果，长 data 以最多 800 字符预览发送并标记 data_truncated，最早的一条可能是入口导航。

这是每轮重新构造的上下文，不会把所有历史聊天消息累计发送。成功的 read/snapshot/locate 另外写入 evidence，最多八份，每份最多 1,600 字符，附 URL、调用参数和截断标记；相同 URL、工具及参数的读取更新原记录。资料退出近期动作窗口后仍可复用，超出证据容量或需要当前状态时才重新读取。这些是读取时的历史证据，不表示页面此刻未变化。终端结果摘录长度不限制自动页面快照长度。

## 模型输出与工具返回

模型 message.content 是 JSON 字符串，例如：

```json
{"tool":"fill","args":{"target":{"label":"关键词"},"value_ref":"query"}}
```

单步格式兼容，同时支持阶段批次：

```json
{"stage":"查询资料","success_criteria":"结果已刷新，读取到目标条目","actions":[{"tool":"fill","args":{"target":{"label":"关键词"},"value_ref":"query"}},{"tool":"click","args":{"target":{"role":"button","name":"搜索"},"wait_after":{"target":{"role":"status"},"state":"text","value":"查询完成"}}},{"tool":"read","args":{"target":{"role":"main"}}}]}
```

不设置固定阶段步数，模型根据当前信息划分阶段，整个计划不得超过剩余总预算 steps_left。Runtime 解析后绑定 value_ref 并调用 BrowserTools.execute。工具成功返回 `{"ok":true,"data":...}`，失败返回 `{"ok":false,"error":"..."}`。动作已执行但后续等待失败时保留 `ok=true`，增加 `after_wait.ok=false`；脚本停止，模型模式下一轮读取该信息，不自动重放。

Skill stages 的 goal/evidence/observe_when 提供阶段建议；模型返回的 stage/success_criteria 说明本次目标和所需证据，具体等待复用 wait_after/wait_for，不新增业务检查器。阶段最后通常是 read/snapshot/locate；缺少显式读取时，正常循环也会重新 observe。last_stage 包含 goal、success_criteria、executed、skipped、stop_reason，独立于六条近期历史，避免长阶段丢失目标。计划执行完只表示动作已执行，是否达成由模型依据新证据判断。

模型结束指令：

```json
{"tool":"finish","args":{"status":"succeeded","message":"中文结果说明"}}
```

finish 不属于工具库的 22 个工具，必须单独返回，不能混入批次。整个批次在开始前检查格式与步数；超出剩余预算的计划不执行并计一次无效计划，防止无限请求。每个实际工具调用计一步，finish 也计一步，未执行的批次尾部不计步。最终 turns/llm_calls 表示模型调用数，steps 表示已用预算。

read/snapshot/locate、获准的关键操作及操作/等待失败后结束阶段。导航或标签页变化默认也结束阶段，但预期导航可以继续：动作顶层声明 expected_url（fnmatch 风格的 * 通配 URL，区分大小写），实际 URL 匹配且 args.wait_after 成功，并且没有意外标签页变化。仅同一页导航和显式 tabs new/switch 可采用此例外，意外弹窗仍中断。该声明是模型规划信息，不是权限授权，也不能绕过授权闸门；宽泛 URL 和通用等待不能证明业务目标达成。

例如 click 声明 expected_url 为 https://zh.wikipedia.org/wiki/*，wait_after 等待准确条目 heading 后，同阶段继续 read 正文。URL 不匹配或等待缺失时不会执行后续读取。中断的尾部不自动补跑，batch_skipped/batch_stop_reason 和 last_stage 说明执行情况。未知组件判断仍依赖模型遵循提示，没有通用语义检查器。错误返回不保证此前动作没有副作用；接口异常仍终止运行，没有自动业务恢复层。

终端在每次执行规划开始和响应返回时显示醒目的 LLM 分隔块，返回块标注模型请求等待秒数（不含页面观察和工具执行）。AI 授权请求单独标注。提示写入 stderr，不影响 --json 的 stdout。

## Token、耗时与数据边界

终端分别显示 LLM 执行规划调用次数和操作预算用量。JSON 保留原有 turns/steps，并增加 max_steps、action_steps（工具操作尝试，含失败或被拒绝步骤）、finish_steps、invalid_plans；后三项之和等于 steps。入口导航不占该预算。finish 会单独提示，不应将预算步数理解为模型调用次数。人工模式未触发审核时会明确显示“本次没有操作触发授权提示”。

API usage 中的 prompt_tokens、completion_tokens、total_tokens 按请求累计。requests 为尝试请求数，reported_requests 为完整用量报告数；缺失或请求失败时显示统计不完整，不估算遗漏用量。服务端如返回独立推理字段，当前不单独展示或处理，最终以其 usage 报告为准。

总耗时包含加载、浏览器启动和任务执行，到输出结果时停止计时，不包含用户查看窗口的时间。当前没有逐轮模型耗时、请求缓存、持久任务记忆或自动日志落盘。

密钥仅用于 HTTP Authorization，不写入模型消息或正常日志。LLM 模式会将选中页面文字与工具读取结果发送给所配置的模型服务。默认脚本 + human 不发送模型请求；脚本 + ai 会发送关键操作审核请求。两种模式仍会访问 Skill 指定的网站。usage 包含执行规划和 AI 审核的请求与 Token；turns/llm_calls 仅统计执行规划。

## 等待的边界

控件准备的多个检查各有超时，不能把“默认 10 秒”理解为整个动作的总耗时上限。wait_for 最多 30 秒；wait 最多 5 秒。LLM HTTP 客户端配置 120 秒网络超时，不是整个任务的总时限。

readiness 在模型观察前最多等待 2 秒，尝试找到 200 毫秒 DOM 安静期和非 busy 状态；它不能判断延迟业务请求是否全部完成。wait_response 最多等待 30 秒收到匹配响应，再读取响应体并执行 wait_after；响应体读取不是同一个 30 秒总预算。等待业务结果应优先使用可区分新旧状态的明确条件。
