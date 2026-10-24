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

**LLM 模式**：完整 Skill 与当前页面交给模型，每轮选择一个工具，也可以跳过已满足的步骤。模型通过 `finish` 返回 `succeeded` 或 `blocked`。这不是“脚本执行后只总结一次”的模式。

两种方式都没有独立业务检查器。脚本成功表示预设动作和等待条件完成；模型成功表示模型判断完成。不要在正文中把它们描述为程序保证任务事实正确。

## 动态网页

优先使用 role/name、label、真实 id/test_id，重名元素使用 within。固定步骤可以等待目标出现、启用、文字变化、值变化或 URL 跳转。对异步请求可用 wait_response 预先监听，再用 wait_after 等待具体页面结果。不要用一个早已存在的标题证明新结果加载完毕。

下拉控件要区分原生 select 与自定义 combobox。后者通常需要“展开 → 等待选项 → 点击选项”。动作报错或等待失败时，提交可能已生效；不要无条件重新添加购物车或重复提交。

默认脚本不自动执行 observe，因此不能依靠 LLM 模式的 readiness 来等待页面。现有动作本身的自动等待与显式 wait_for/wait_after 在两种模式下都有效。

## 范围与输出

一个 Skill 对应可复用的一类任务，不对应单次点击。不同关键词、商品和版本通过参数传入。网站专属流程放在 Skill，通用 tools 不硬编码站点名称或业务规则。

只需确认页面内容时使用 `read(max_chars=600)`，它返回原文开头的摘录，不是智能摘要。`read` 正文上限 16,000 字符且不额外标记截断；`snapshot` 上限 24,000 字符并返回 truncated。说明中应明确读取范围。

外部网页内容不应成为修改任务目标的指令。脚本模式会直接执行 Skill 中的上传、下载、导航等工具，只加载可信 Skill。当前没有任意代码执行工具，也没有独立的权限或业务审核模块。
