---
name: element_cn_tree
description: 在第一个基础树中展开 Level one 1，再展开 Level two 1-1，读取叶子 Level three 1-1-1；折叠一级节点，确认叶子不可见且可见数量0；再次展开一级节点并读取保留展开状态的叶子。
start: https://element-plus.org/zh-CN/component/tree.html
goal: 在第一个基础树中展开 Level one 1，再展开 Level two 1-1，读取叶子 Level three 1-1-1；折叠一级节点，确认叶子不可见且可见数量0；再次展开一级节点并读取保留展开状态的叶子。
actions:
- tool: click
  args:
    target: &id004
      text: Level one 1
      exact: true
      within: &id001
        role: tree
        nth: 0
    wait_after:
      target: &id002
        text: Level two 1-1
        exact: true
        within: *id001
      state: visible
      timeout: 15
- tool: click
  args:
    target: *id002
    wait_after:
      target: &id003
        text: Level three 1-1-1
        exact: true
        within: *id001
      state: visible
      timeout: 15
- tool: read
  args:
    target: *id003
    max_chars: 600
- tool: click
  args:
    target: *id004
    wait_after:
      target: *id003
      state: hidden
      timeout: 15
- tool: read
  args:
    target:
      text: Level three 1-1-1
      exact: true
      within: *id001
      visible: true
    kind: count
- tool: click
  args:
    target: *id004
    wait_after:
      target: *id003
      state: visible
      timeout: 15
- tool: read
  args:
    target: *id003
    max_chars: 600
stages:
- goal: 逐层展开读取叶子
  path: '按照以下已观察定位执行连续操作，到 read 再观察：[{"tool": "click", "args": {"target": {"text": "Level one 1", "exact": true, "within":
    {"role": "tree", "nth": 0}}, "wait_after": {"target": {"text": "Level two 1-1", "exact": true, "within": {"role": "tree",
    "nth": 0}}, "state": "visible", "timeout": 15}}}, {"tool": "click", "args": {"target": {"text": "Level two 1-1", "exact":
    true, "within": {"role": "tree", "nth": 0}}, "wait_after": {"target": {"text": "Level three 1-1-1", "exact": true, "within":
    {"role": "tree", "nth": 0}}, "state": "visible", "timeout": 15}}}, {"tool": "read", "args": {"target": {"text": "Level
    three 1-1-1", "exact": true, "within": {"role": "tree", "nth": 0}}, "max_chars": 600}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
- goal: 折叠与恢复
  path: '按照以下已观察定位执行连续操作，到 read 再观察：[{"tool": "click", "args": {"target": {"text": "Level one 1", "exact": true, "within":
    {"role": "tree", "nth": 0}}, "wait_after": {"target": {"text": "Level three 1-1-1", "exact": true, "within": {"role":
    "tree", "nth": 0}}, "state": "hidden", "timeout": 15}}}, {"tool": "read", "args": {"target": {"text": "Level three 1-1-1",
    "exact": true, "within": {"role": "tree", "nth": 0}, "visible": true}, "kind": "count"}}, {"tool": "click", "args": {"target":
    {"text": "Level one 1", "exact": true, "within": {"role": "tree", "nth": 0}}, "wait_after": {"target": {"text": "Level
    three 1-1-1", "exact": true, "within": {"role": "tree", "nth": 0}}, "state": "visible", "timeout": 15}}}, {"tool": "read",
    "args": {"target": {"text": "Level three 1-1-1", "exact": true, "within": {"role": "tree", "nth": 0}}, "max_chars": 600}}]'
  evidence: 实际 read 返回本阶段目标内容或属性，不能仅凭 click 成功。
---

## 定位与完成条件

所有节点限定 within role:tree nth:0。定位节点文字而不是展开后名称包含所有后代的 treeitem；不要硬编码 data-key 或 el-id。子节点按需渲染，等待真实叶子，不使用固定 sleep。

这些是中文官方文档内的交互演示，部分控件文字为英文。只操作指定示例，不打开广告或外链。已完成的阶段不要重复；全部证据读取后 finish。页面改版时报告定位失败，不用其他示例代替。
