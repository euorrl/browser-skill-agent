# 架构与模型交互

## 模块职责

| 文件 | 职责 |
| --- | --- |
| `cli.py` | 解析参数、加载模型配置、启动并关闭 Edge、汇总输出 |
| `browser_display.py` | 通过 CDP 控制本任务窗口位置，结束后显示同一会话 |
| `skill.py` | 解析 YAML 和 Markdown 正文，绑定字符串参数 |
| `runtime.py` | 顺序脚本或模型循环；模型 API 调用和 Token 累计 |
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
                   └─ --llm：start → observe → 模型决策 → 工具 → 下一轮
                                      ↑                 │
                                      └─ 最近六次结果 ──┘
                   → 输出状态、耗时、Token → 可选显示/保留窗口 → 关闭
```

自动创建的临时用户目录由 Playwright 管理。`--profile-dir` 显式选择固定目录时跨次保存状态，但不能同时被两个浏览器进程占用。`--result-only` 使用有界面 Edge，将窗口暂放屏幕外，最终移回，不通过重新加载页面重建结果。

## 每轮 LLM 输入

调用兼容 Chat Completions 的 HTTP 接口，非流式请求，不使用模型 SDK 或原生 tools/function calling 字段。请求体包含 model、messages 和 `response_format: {"type":"json_object"}`。

messages 每轮只有两条：

1. system：中文执行规则 + 22 个工具的说明。
2. user：当前 state 的 JSON 字符串，包括完整 skill、page、recent_actions 和 turns_left。

skill 含绑定后的元信息（目前也包含完整 actions）、params 和正文 instructions。page 含 URL、最多 24,000 字符的文字快照、truncated、标签页和框架编号、最近弹窗记录及 readiness。recent_actions 只保留最近六次操作与工具结果，最早的一条可能是入口导航。

这是每轮重新构造的上下文，不会把所有历史聊天消息累计发送。旧资料退出六次操作窗口后可能需要重新读取。终端结果摘录长度不限制自动页面快照长度。

## 模型输出与工具返回

模型 message.content 是 JSON 字符串，例如：

```json
{"tool":"fill","args":{"target":{"label":"关键词"},"value_ref":"query"}}
```

Runtime 解析后绑定 value_ref 并调用 BrowserTools.execute。工具成功返回 `{"ok":true,"data":...}`，失败返回 `{"ok":false,"error":"..."}`。动作已执行但后续等待失败时保留 `ok=true`，增加 `after_wait.ok=false`；脚本停止，模型模式下一轮读取该信息，不自动重放。

模型结束指令：

```json
{"tool":"finish","args":{"status":"succeeded","message":"中文结果说明"}}
```

finish 不属于工具库的 22 个工具。错误返回不保证此前动作没有产生副作用。JSON 格式错误、接口异常等会终止运行；没有通用的模型重试和业务恢复层。

## Token、耗时与数据边界

API usage 中的 prompt_tokens、completion_tokens、total_tokens 按请求累计。requests 为尝试请求数，reported_requests 为完整用量报告数；缺失或请求失败时显示统计不完整，不估算遗漏用量。服务端如返回独立推理字段，当前不单独展示或处理，最终以其 usage 报告为准。

总耗时包含加载、浏览器启动和任务执行，到输出结果时停止计时，不包含用户查看窗口的时间。当前没有逐轮模型耗时、请求缓存、持久任务记忆或自动日志落盘。

密钥仅用于 HTTP Authorization，不写入模型消息或正常日志。LLM 模式会将选中页面文字与工具读取结果发送给所配置的模型服务。默认脚本模式不发送模型请求，但仍会访问 Skill 指定的网站。

## 等待的边界

控件准备的多个检查各有超时，不能把“默认 10 秒”理解为整个动作的总耗时上限。wait_for 最多 30 秒；wait 最多 5 秒。LLM HTTP 客户端配置 120 秒网络超时，不是整个任务的总时限。

readiness 在模型观察前最多等待 2 秒，尝试找到 200 毫秒 DOM 安静期和非 busy 状态；它不能判断延迟业务请求是否全部完成。wait_response 最多等待 30 秒收到匹配响应，再读取响应体并执行 wait_after；响应体读取不是同一个 30 秒总预算。等待业务结果应优先使用可区分新旧状态的明确条件。
