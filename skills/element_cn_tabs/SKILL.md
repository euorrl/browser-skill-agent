---
name: element_cn_tabs
description: 在第一个基本标签页示例中依次切换 Config、Task，最后返回 User；每次等待对应 tabpanel 出现并读取内容及 tab 的 aria-selected=true。
start: https://element-plus.org/zh-CN/component/tabs.html
goal: 在第一个基本标签页示例中依次切换 Config、Task，最后返回 User；每次等待对应 tabpanel 出现并读取内容及 tab 的 aria-selected=true。
actions:
- tool: click
  args:
    target: &id002
      role: tab
      nth: 0
      name: Config
    wait_after:
      target: &id001
        role: tabpanel
        nth: 0
        name: Config
      state: visible
      timeout: 15
- tool: read
  args:
    target: *id001
    max_chars: 600
- tool: read
  args:
    target: *id002
    kind: attribute
    attribute: aria-selected
- tool: click
  args:
    target: &id004
      role: tab
      nth: 0
      name: Task
    wait_after:
      target: &id003
        role: tabpanel
        nth: 0
        name: Task
      state: visible
      timeout: 15
- tool: read
  args:
    target: *id003
    max_chars: 600
- tool: read
  args:
    target: *id004
    kind: attribute
    attribute: aria-selected
- tool: click
  args:
    target: &id006
      role: tab
      nth: 0
      name: User
    wait_after:
      target: &id005
        role: tabpanel
        nth: 0
        name: User
      state: visible
      timeout: 15
- tool: read
  args:
    target: *id005
    max_chars: 600
- tool: read
  args:
    target: *id006
    kind: attribute
    attribute: aria-selected
stages:
- goal: 切换并读取 Config
  path: '按照以下已观察定位完整执行本阶段，包含多次 read；阶段结束后统一观察：[{"tool": "click", "args": {"target": {"role": "tab", "nth": 0, "name": "Config"}, "wait_after":
    {"target": {"role": "tabpanel", "nth": 0, "name": "Config"}, "state": "visible", "timeout": 15}}}, {"tool": "read", "args":
    {"target": {"role": "tabpanel", "nth": 0, "name": "Config"}, "max_chars": 600}}, {"tool": "read", "args": {"target": {"role":
    "tab", "nth": 0, "name": "Config"}, "kind": "attribute", "attribute": "aria-selected"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
- goal: 切换并读取 Task
  path: '按照以下已观察定位完整执行本阶段，包含多次 read；阶段结束后统一观察：[{"tool": "click", "args": {"target": {"role": "tab", "nth": 0, "name": "Task"}, "wait_after":
    {"target": {"role": "tabpanel", "nth": 0, "name": "Task"}, "state": "visible", "timeout": 15}}}, {"tool": "read", "args":
    {"target": {"role": "tabpanel", "nth": 0, "name": "Task"}, "max_chars": 600}}, {"tool": "read", "args": {"target": {"role":
    "tab", "nth": 0, "name": "Task"}, "kind": "attribute", "attribute": "aria-selected"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
- goal: 切换并读取 User
  path: '按照以下已观察定位完整执行本阶段，包含多次 read；阶段结束后统一观察：[{"tool": "click", "args": {"target": {"role": "tab", "nth": 0, "name": "User"}, "wait_after":
    {"target": {"role": "tabpanel", "nth": 0, "name": "User"}, "state": "visible", "timeout": 15}}}, {"tool": "read", "args":
    {"target": {"role": "tabpanel", "nth": 0, "name": "User"}, "max_chars": 600}}, {"tool": "read", "args": {"target": {"role":
    "tab", "nth": 0, "name": "User"}, "kind": "attribute", "attribute": "aria-selected"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
---

## 定位与完成条件

同名 tab 在多个演示重复，nth:0 明确选择文档第一个基础演示，不使用重复的 tab-first 等 ID。最终第一个演示必须回到 User。

这些是中文官方文档内的交互演示，部分控件文字为英文。只操作指定示例，不打开广告或外链。已完成的阶段不要重复；全部证据读取后 finish。页面改版时报告定位失败，不用其他示例代替。
