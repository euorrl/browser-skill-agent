---
name: element_cn_pagination
description: 操作第一个 When you have few pages 五页分页器：精确点击第3页，下一页到4，上一页回3，再回第1页；每次读取目标页 aria-current=true，最后读取上一页按钮 disabled 属性确认回到边界。
start: https://element-plus.org/zh-CN/component/pagination.html
goal: 操作第一个 When you have few pages 五页分页器：精确点击第3页，下一页到4，上一页回3，再回第1页；每次读取目标页 aria-current=true，最后读取上一页按钮 disabled 属性确认回到边界。
actions:
- tool: click
  args:
    target:
      role: listitem
      nth: 0
      name: page 3
- tool: read
  args:
    target:
      role: listitem
      nth: 0
      name: page 3
    kind: attribute
    attribute: aria-current
- tool: click
  args:
    target:
      role: button
      nth: 0
      name: Go to next page
- tool: read
  args:
    target:
      role: listitem
      nth: 0
      name: page 4
    kind: attribute
    attribute: aria-current
- tool: click
  args:
    target: &id001
      role: button
      nth: 0
      name: Go to previous page
- tool: read
  args:
    target:
      role: listitem
      nth: 0
      name: page 3
    kind: attribute
    attribute: aria-current
- tool: click
  args:
    target:
      role: listitem
      nth: 0
      name: page 1
- tool: read
  args:
    target:
      role: listitem
      nth: 0
      name: page 1
    kind: attribute
    attribute: aria-current
- tool: read
  args:
    target: *id001
    kind: attribute
    attribute: disabled
stages:
- goal: 跳到3并向后翻页
  path: '按照以下已观察定位执行连续操作，到 read 再观察：[{"tool": "click", "args": {"target": {"role": "listitem", "nth": 0, "name": "page 3"}}},
    {"tool": "read", "args": {"target": {"role": "listitem", "nth": 0, "name": "page 3"}, "kind": "attribute", "attribute":
    "aria-current"}}, {"tool": "click", "args": {"target": {"role": "button", "nth": 0, "name": "Go to next page"}}}, {"tool":
    "read", "args": {"target": {"role": "listitem", "nth": 0, "name": "page 4"}, "kind": "attribute", "attribute": "aria-current"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
- goal: 向前翻页并回到边界
  path: '按照以下已观察定位执行连续操作，到 read 再观察：[{"tool": "click", "args": {"target": {"role": "button", "nth": 0, "name": "Go to previous
    page"}}}, {"tool": "read", "args": {"target": {"role": "listitem", "nth": 0, "name": "page 3"}, "kind": "attribute", "attribute":
    "aria-current"}}, {"tool": "click", "args": {"target": {"role": "listitem", "nth": 0, "name": "page 1"}}}, {"tool": "read",
    "args": {"target": {"role": "listitem", "nth": 0, "name": "page 1"}, "kind": "attribute", "attribute": "aria-current"}},
    {"tool": "read", "args": {"target": {"role": "button", "nth": 0, "name": "Go to previous page"}, "kind": "attribute",
    "attribute": "disabled"}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
---

## 定位与完成条件

文档重复多个分页器，page N 和翻页按钮均 nth:0，明确为第一个五页示例。读取 disabled 属性返回空字符串表示 HTML 布尔属性存在，null 表示不存在。此示例只验证分页控件状态，不声称加载了后端业务列表。

这些是中文官方文档内的交互演示，部分控件文字为英文。只操作指定示例，不打开广告或外链。已完成的阶段不要重复；全部证据读取后 finish。页面改版时报告定位失败，不用其他示例代替。
