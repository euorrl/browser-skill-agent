---
name: element_cn_collapse
description: 在第一个基础折叠面板打开 Feedback 并读取反馈说明，再打开 Efficiency 并读取效率说明；最后关闭 Feedback、保持 Efficiency 展开，读取二者 aria-expanded 分别为 false
  和 true。
start: https://element-plus.org/zh-CN/component/collapse.html
goal: 在第一个基础折叠面板打开 Feedback 并读取反馈说明，再打开 Efficiency 并读取效率说明；最后关闭 Feedback、保持 Efficiency 展开，读取二者 aria-expanded 分别为 false 和 true。
actions:
- tool: click
  args:
    target:
      role: button
      nth: 0
      name: Feedback
    wait_after:
      target:
        role: region
        nth: 0
        name: Feedback
      state: visible
      timeout: 15
- tool: read
  args:
    target:
      role: region
      nth: 0
      name: Feedback
    max_chars: 600
- tool: click
  args:
    target:
      role: button
      nth: 0
      name: Efficiency
    wait_after:
      target:
        role: region
        nth: 0
        name: Efficiency
      state: visible
      timeout: 15
- tool: read
  args:
    target:
      role: region
      nth: 0
      name: Efficiency
    max_chars: 600
- tool: click
  args:
    target:
      role: button
      nth: 0
      name: Feedback
    wait_after:
      target:
        role: region
        nth: 0
        name: Feedback
      state: hidden
      timeout: 15
- tool: read
  args:
    target:
      role: button
      nth: 0
      name: Feedback
    kind: attribute
    attribute: aria-expanded
- tool: read
  args:
    target:
      role: button
      nth: 0
      name: Efficiency
    kind: attribute
    attribute: aria-expanded
stages:
- goal: 打开并读取反馈
  path: '按照以下已观察定位执行连续操作，到 read 再观察：[{"tool": "click", "args": {"target": {"role": "button", "nth": 0, "name": "Feedback"},
    "wait_after": {"target": {"role": "region", "nth": 0, "name": "Feedback"}, "state": "visible", "timeout": 15}}}, {"tool":
    "read", "args": {"target": {"role": "region", "nth": 0, "name": "Feedback"}, "max_chars": 600}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
- goal: 打开效率并关闭反馈
  path: '按照以下已观察定位执行连续操作，到 read 再观察：[{"tool": "click", "args": {"target": {"role": "button", "nth": 0, "name": "Efficiency"},
    "wait_after": {"target": {"role": "region", "nth": 0, "name": "Efficiency"}, "state": "visible", "timeout": 15}}}, {"tool":
    "read", "args": {"target": {"role": "region", "nth": 0, "name": "Efficiency"}, "max_chars": 600}}, {"tool": "click", "args":
    {"target": {"role": "button", "nth": 0, "name": "Feedback"}, "wait_after": {"target": {"role": "region", "nth": 0, "name":
    "Feedback"}, "state": "hidden", "timeout": 15}}}, {"tool": "read", "args": {"target": {"role": "button", "nth": 0, "name":
    "Feedback"}, "kind": "attribute", "attribute": "aria-expanded"}}, {"tool": "read", "args": {"target": {"role": "button",
    "nth": 0, "name": "Efficiency"}, "kind": "attribute", "attribute": "aria-expanded"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
---

## 定位与完成条件

nth:0 选择第一个基础面板。不要操作第二个手风琴示例；本示例允许同时展开多个面板。不要依赖 el-collapse-head 动态编号。

这些是中文官方文档内的交互演示，部分控件文字为英文。只操作指定示例，不打开广告或外链。已完成的阶段不要重复；全部证据读取后 finish。页面改版时报告定位失败，不用其他示例代替。
