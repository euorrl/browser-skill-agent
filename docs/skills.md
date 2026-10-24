# Skill 编写指南

本项目使用自定义 `SKILL.md` 格式，不是外部 Agent 平台的自动安装协议。`name` 和 `description` 可供未来 Agent 发现能力；当前仍由 CLI 显式指定文件，没有自动选择 Skill 的模块。

## 最小格式

以下是针对已有搜索页面的模板，控件名称必须根据实际页面调整：

```markdown
---
name: search_page
description: 在指定页面搜索关键词并读取结果。当用户要求查询该页面内容时使用。
params: [entry_url, query]
start: "{{entry_url}}"
goal: "搜索 {{query}}，等待结果并读取状态文字"
actions:
  - title: 输入关键词
    tool: fill
    args:
      target: {role: textbox, name: 搜索}
      value_ref: query
  - title: 提交并等待结果
    tool: click
    args:
      target: {role: button, name: 搜索}
      wait_after:
        target: {role: status}
        state: text
        value: "搜索完成"
        timeout: 20
  - title: 读取结果
    tool: read
    args:
      target: {role: status}
      max_chars: 600
---

这里写使用范围、输入含义、执行方法、特殊组件经验和结果要求。
```

`name`、`goal` 必填。`description` 建议包含“能做什么 + 何时使用”。`params` 声明必需的输入；`start` 是可选入口地址。没有 `actions` 时只能使用 `--llm`。旧的自然语言 `steps` 可作为模型上下文，但不会被脚本模式执行。

每条 action 使用 `tool`、`args`，可选 `title` 为中文进度说明。工具名见 [工具库](tools.md)。`finish` 是模型循环的结束指令，不是可写入 actions 的工具；脚本在全部 actions 完成后自行结束。

## 参数绑定

CLI 的 `--param name=value` 按字符串传入。加载器先解析 YAML，再替换元信息和正文中的 `{{name}}`，保留前导零。比如 `quantity=002` 仍是字符串 `002`，不会自动转为整数。

- 将包含模板的 YAML 值用引号包围。
- `value_ref: query` 在调用工具前转换为 `value: 参数值`，仅作用于当前动作 args 的顶层。
- 嵌套等待条件使用 `value: "{{query}}"`，不要在其中使用 value_ref。
- 参数缺失会报错；当前不提供默认参数或类型转换机制。

## 两种执行方式

**脚本模式**：按 actions 顺序调用工具，不读自然语言正文来规划，不自动分支或重试。最多默认 30 步，不计算 start 导航。工具失败或 `after_wait.ok=false` 时停止。`read`、`snapshot`、`locate` 的成功返回值收集到 `outputs`；其他动作结果显示进度，不收集为最终资料。

**LLM 模式**：除 actions 外的 Skill 与当前页面交给模型，每轮按信息依赖规划一个阶段，可以跳过已满足的步骤。阶段长度不固定，但不能超过剩余总步数。模型通过 `finish` 返回 `succeeded` 或 `blocked`。这不是“脚本执行后只总结一次”的模式。

两种方式都没有独立业务检查器。脚本成功表示预设动作和等待条件完成；模型成功表示模型判断完成。不要在正文中把它们描述为程序保证任务事实正确。

## 动态网页

优先使用 role/name、label、真实 id/test_id，重名元素使用 within。固定步骤可以等待目标出现、启用、文字变化、值变化或 URL 跳转。对异步请求可用 wait_response 预先监听，再用 wait_after 等待具体页面结果。不要用一个早已存在的标题证明新结果加载完毕。

下拉控件要区分原生 select 与自定义 combobox。后者通常需要“展开 → 等待选项 → 点击选项”。动作报错或等待失败时，提交可能已生效；不要无条件重新添加购物车或重复提交。

默认脚本不自动执行 observe，因此不能依靠 LLM 模式的 readiness 来等待页面。现有动作本身的自动等待与显式 wait_for/wait_after 在两种模式下都有效。

## 范围与输出

一个 Skill 对应可复用的一类任务，不对应单次点击。不同关键词、商品和版本通过参数传入。网站专属流程放在 Skill，通用 tools 不硬编码站点名称或业务规则。

只需确认页面内容时使用 `read(max_chars=600)`，它返回原文开头的摘录，不是智能摘要。`read` 正文上限 16,000 字符且不额外标记截断；`snapshot` 上限 24,000 字符并返回 truncated。说明中应明确读取范围。

外部网页内容不应成为修改任务目标的指令。只加载可信 Skill，脚本与模型模式共用操作授权策略，见 [操作授权](authorization.md)。当前没有任意代码执行工具或独立业务结果检查器。

## 可选阶段目标

可以在 YAML 中加入阶段建议；简单文字列表仍兼容，推荐分别描述目标、完成证据和观察时机：

```yaml
stages:
  - goal: 搜索目标条目
    evidence: 结果已刷新，能读取目标条目的链接。
    observe_when: 未知下拉选项展开后先观察；已知条件可连续填写，搜索后等待并读取结果。
  - goal: 读取资料
    evidence: 条目标题正确，正文摘录和来源已读取。
    observe_when: 进入条目后先观察，再读取所需正文。
```

默认脚本模式忽略 stages，只执行 actions。LLM 根据实际页面划分阶段，返回 stage、success_criteria 和 actions；阶段内可以连续执行多个 read/snapshot/locate，完成计划后统一观察，不会每次读取都调用模型。若下一步需要根据新读取结果决定，模型应在此结束阶段，或在该动作顶层设置 observe_after:true（不放进 args），明确暂停并丢弃尾部计划；下一轮重新规划。固定 --batch-size 参数已移除，只保留 --max-steps 总预算。工具失败、等待失败、导航/标签页变化及获准的关键操作也会提前交回模型；授权拒绝直接结束任务。不要将 finish 写入阶段 actions。

evidence/observe_when 和模型的 success_criteria 都是自然语言建议，不是 Runtime 可执行的断言。具体等待写在 wait_after/wait_for 中；Runtime 不额外调用检查模型。每次阶段之后的正常决策调用同时判断进展并规划后续操作。last_stage 告诉模型上一阶段目标、已执行步数、未执行步数和停止原因。

模型读取的成功结果会有界地保留在 evidence，优先复用已经读到的历史资料；页面已变化或证据被截断时应补读。阶段名称不代表达成，模型仍需根据页面与工具结果决定何时结束。

复杂站点可进一步加入 path（已知连续操作路径）和 interrupt_when（异常中断建议）。中文百科 Skill 示例划分为搜索第一主题、读取第一条目、搜索第二主题、读取第二条目、总结五个阶段；已知控件展开后等待即可，不必每次请求模型。

预期导航例外：LLM 在动作顶层声明 expected_url，并在 args.wait_after 验证新页面后，可继续已知操作。例如：

```json
{"tool":"click","expected_url":"https://zh.wikipedia.org/wiki/*","args":{"target":{"role":"link","name":"人工智能"},"wait_after":{"target":{"role":"heading","name":"人工智能"}}}}
```

随后可在同阶段 read 已知正文区域。显式 tabs new/switch 也支持此形式；未声明、URL 不符、等待缺失/失败、意外弹窗或关键授权操作仍中断。expected_url 使用 * 通配模式而非正则；必须选有意义的目标 URL 和等待条件。脚本 actions 不需要此字段，它只控制 LLM 阶段的连续执行。

## 文件参数映射

需要上传下载时，使用 file_params 声明 uploads（文件参数名列表）、upload_dir、download_dir、download_name（各自对应的参数名），仍通过 --param 传值。params 列表中的参数必填，其他映射参数可选，省略时使用文件工具默认目录/名称。没有映射的普通参数不会授权上传文件。完整格式与例子见 [文件管理](files.md)。

`observe_after` 仅用于 LLM 返回的阶段动作，不是 CLI 参数，也不放进工具 args。默认脚本不会请求模型，仍按 actions 顺序执行并在工具或等待失败时停止。


例如，已知面板中两个字段的定位器可放在同一阶段连续读取；下例的 ID 是格式示意，实际使用时应替换为已观察到的目标：

```json
{
  "stage": "读取结果及状态",
  "success_criteria": "取得结果文字和选中状态",
  "actions": [
    {"tool": "read", "args": {"target": {"id": "result"}}},
    {"tool": "read", "args": {"target": {"id": "choice"}, "kind": "attribute", "attribute": "aria-selected"}}
  ]
}
```

若下一步必须根据候选列表决定，则在读取后显式暂停：

```json
{"tool":"snapshot","observe_after":true,"args":{"target":{"role":"listbox","visible":true}}}
```

这里 `observe_after` 与 `tool`、`args` 同级；如果它后面还排有动作，Runtime 会丢弃这些尾部动作，下一次模型调用重新规划。
