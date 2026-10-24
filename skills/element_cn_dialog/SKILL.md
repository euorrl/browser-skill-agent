---
name: element_cn_dialog
description: 打开基础 Tips 模态弹窗并读取 This is a message，点击 Cancel 等待消失并读取可见 dialog 数量0；再次打开读取消息，点击 Confirm 等待消失并读取数量0。两种关闭路径都必须执行。
start: https://element-plus.org/zh-CN/component/dialog.html
goal: 打开基础 Tips 模态弹窗并读取 This is a message，点击 Cancel 等待消失并读取可见 dialog 数量0；再次打开读取消息，点击 Confirm 等待消失并读取数量0。两种关闭路径都必须执行。
actions:
- tool: click
  args:
    target: &id002
      role: button
      nth: 0
      name: Click to open the Dialog
    wait_after:
      target: &id001
        role: dialog
        name: Tips
      state: visible
      timeout: 15
- tool: read
  args:
    target: *id001
    max_chars: 600
- tool: click
  args:
    target:
      role: button
      within: *id001
      name: Cancel
    wait_after:
      target: *id001
      state: hidden
      timeout: 15
- tool: read
  args:
    target:
      role: dialog
      name: Tips
      visible: true
    kind: count
- tool: click
  args:
    target: *id002
    wait_after:
      target: *id001
      state: visible
      timeout: 15
- tool: read
  args:
    target: *id001
    max_chars: 600
- tool: click
  args:
    target:
      role: button
      within: *id001
      name: Confirm
    wait_after:
      target: *id001
      state: hidden
      timeout: 15
- tool: read
  args:
    target:
      role: dialog
      name: Tips
      visible: true
    kind: count
stages:
- goal: 打开后取消
  path: '按照以下已观察定位完整执行本阶段，包含多次 read；阶段结束后统一观察：[{"tool": "click", "args": {"target": {"role": "button", "nth": 0, "name": "Click to open
    the Dialog"}, "wait_after": {"target": {"role": "dialog", "name": "Tips"}, "state": "visible", "timeout": 15}}}, {"tool":
    "read", "args": {"target": {"role": "dialog", "name": "Tips"}, "max_chars": 600}}, {"tool": "click", "args": {"target":
    {"role": "button", "within": {"role": "dialog", "name": "Tips"}, "name": "Cancel"}, "wait_after": {"target": {"role":
    "dialog", "name": "Tips"}, "state": "hidden", "timeout": 15}}}, {"tool": "read", "args": {"target": {"role": "dialog",
    "name": "Tips", "visible": true}, "kind": "count"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
- goal: 重新打开后确认
  path: '按照以下已观察定位完整执行本阶段，包含多次 read；阶段结束后统一观察：[{"tool": "click", "args": {"target": {"role": "button", "nth": 0, "name": "Click to open
    the Dialog"}, "wait_after": {"target": {"role": "dialog", "name": "Tips"}, "state": "visible", "timeout": 15}}}, {"tool":
    "read", "args": {"target": {"role": "dialog", "name": "Tips"}, "max_chars": 600}}, {"tool": "click", "args": {"target":
    {"role": "button", "within": {"role": "dialog", "name": "Tips"}, "name": "Confirm"}, "wait_after": {"target": {"role":
    "dialog", "name": "Tips"}, "state": "hidden", "timeout": 15}}}, {"tool": "read", "args": {"target": {"role": "dialog",
    "name": "Tips", "visible": true}, "kind": "count"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
---

## 定位与完成条件

弹窗挂载在页面浮层，不在触发按钮容器内。Cancel 和 Confirm 必须限定 within role:dialog name:Tips。这里是网页组件弹窗，不是浏览器原生 dialog 工具；不要点击右上角关闭按钮，它会触发额外确认流程。

这些是中文官方文档内的交互演示，部分控件文字为英文。只操作指定示例，不打开广告或外链。已完成的阶段不要重复；全部证据读取后 finish。页面改版时报告定位失败，不用其他示例代替。
