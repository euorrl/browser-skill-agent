# 操作授权

CLI 通过 `--approval human|ai|allow` 选择策略，默认 `human`。它与 `--llm` 独立：前者决定谁审核关键操作，后者决定谁规划执行步骤。

| 模式 | 关键操作执行前 |
| --- | --- |
| `human` | 显示 URL、工具参数、实际控件与所属表单；输入 `y`、`yes` 或直接回车允许本次操作（不区分大小写），其他输入拒绝 |
| `ai` | 单独请求模型审核任务范围、操作对象及当前页面文字；必须返回明确批准和理由 |
| `allow` | 跳过授权判断与提示，直接交给工具执行；仍保留参数校验和等待逻辑 |

在原有命令末尾添加参数即可，例如：

```powershell
# 模型规划，人工审核关键操作（默认策略）
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_encyclopedia_research/SKILL.md --param "topic_a=人工智能" --param "topic_b=机器学习" --llm --approval human

# 脚本规划，关键操作交给模型审核；仍需要 .env 模型配置
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_encyclopedia_research/SKILL.md --param "topic_a=人工智能" --param "topic_b=机器学习" --approval ai

# 脚本执行，全部允许，不请求模型
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_encyclopedia_research/SKILL.md --param "topic_a=人工智能" --param "topic_b=机器学习" --approval allow
```

## 触发规则

规则读取真实 DOM 控件信息，不仅依赖模型提供的定位器名称。删除、支付、提交、发送、发布、保存、确认等中英文关键词、非搜索字段修改、文件上传/下载、拖动、按键、接受弹窗、刷新/返回、跨站导航，以及无法识别为普通查看的点击，会请求授权。部分普通筛选也可能触发确认，这是当前保守规则的取舍。

读取、等待、滚动、悬停、已识别的搜索字段/按钮、普通同站链接、选项及标签控件通常直接执行。包含敏感关键词的控件优先触发授权。站点规则比较 scheme 和 netloc，不是完整域名访问白名单。

Skill 可在任一工具的 `args` 中写 `requires_approval: true` 强制请求审核；`false` 不能取消规则识别出的授权要求。`allow` 模式显式跳过所有授权，包括该标记。

```yaml
- tool: click
  args:
    target: {role: button, name: Add to cart}
    requires_approval: true
```

## 拒绝、批次与显示

人工输入除 `y`、`yes`、空行以外的内容（如 `n`）、输入流关闭、AI 拒绝、返回格式错误或审核异常，均不执行当前操作，任务以 `blocked` 停止；模型不会获得继续换工具尝试的机会。直接回车表示批准，但输入流关闭（EOF）不等于回车，仍拒绝。此前已完成的动作不会回滚。

批准只适用于本次操作，不缓存成站点授权。批准后重新核对可观察的 URL、控件信息及表单；变化时拒绝。关键动作执行后结束当前 LLM 批次并重新观察，尚未执行的尾部不自动补跑。脚本继续按顺序执行下一步，并在下一次关键动作前再次审核。

`--result-only` 在人工确认时临时显示浏览器，确认后继续隐藏，任务结束再显示。`--headless` 仅在终端确认。无人值守应明确选择 `ai` 或 `allow`；`human` 在没有输入时拒绝。授权提示写入 stderr，`--json` 的最终 stdout 仍是 JSON。

## 模型输入与统计

AI 审核使用已配置的同一个模型服务，但采用单独的审核提示和独立请求，不复用执行模型的判断。输入包含去掉脚本 actions 的 Skill、绑定后的操作参数、URL、可读取的控件/所属表单信息及最多 6,000 字符页面文字。表单采集中的 password 和 hidden 值被遮盖；这不是所有输入和页面内容的通用脱敏机制。

AI 审核请求的 Token 纳入最终 `usage`，包括脚本模式。`turns/llm_calls` 只表示执行规划调用次数，`usage.requests` 包含规划与审核请求。结果的 `approval` 包含模式及各次审核理由，不自动保存日志。

## 能力边界

这是执行前的规则闸门，不是浏览器权限沙箱，也不保证操作或业务结果正确。网页事件、脚本、重定向可能在看似普通的交互中产生副作用；重新核对也不能消除所有页面竞争变化。AI 审核仍可能误判，不能等同于人工同意。涉及真实付款、删除或对外发送时，建议使用 `human` 并核对现场。

只运行可信 Skill：当前 Skill 定义任务范围，并不是不可信文件的权限声明。CLI 总是安装所选策略；直接调用 `BrowserTools(page)` 的库使用者默认不安装策略，需要显式传入 `approval=ApprovalPolicy(...)`。此设计保留底层工具的独立使用能力。
