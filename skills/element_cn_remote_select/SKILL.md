---
name: element_cn_remote_select
description: 在 Element Plus 中文官方文档的远程搜索示例中输入关键词，等待异步候选并精确选择完整选项；覆盖动态生成ID、重名输入框、弹出层和选择状态读取。示例模拟远程延迟，不声称真实后端查询。
params:
- query
- choice
start: https://element-plus.org/zh-CN/component/select.html#远程搜索
goal: 在远程搜索 default 示例中输入 {{query}}，等待异步候选出现，读取可见列表，精确选择 label:{{choice}} 并读取该 option 的 aria-selected=true。不得操作其他示例或选择名字相似的其他项。
actions:
- tool: click
  title: 限定远程搜索 default 示例并展开
  args:
    target:
      text: Please enter a keyword
      exact: true
      within: &id001
        text: defaultPlease enter a keyword
        exact: true
- tool: fill
  title: 输入过滤词，等待异步候选
  args:
    target:
      role: combobox
      within: *id001
    value_ref: query
    wait_after:
      target: &id002
        role: option
        name: label:{{choice}}
        exact: true
      state: visible
      timeout: 30
- tool: read
  title: 读取当前可见候选
  args:
    target:
      role: listbox
      visible: true
    max_chars: 1000
- tool: click
  title: 精确选择完整选项名称
  args:
    target: *id002
- tool: read
  title: 读取实际选中标记
  args:
    target: *id002
    kind: attribute
    attribute: aria-selected
stages:
- goal: 触发异步过滤并读取候选
  path: 容器 target={text:defaultPlease enter a keyword,exact:true} 是远程搜索 default 示例，文字之间没有空格。先 click 其内 text:Please
    enter a keyword，再 fill 其内 role:combobox，value_ref=query，wait_after 等待 role:option name:label:{{choice}} exact:true。随后
    read role:listbox visible:true。
  evidence: 实际出现匹配的异步候选列表
- goal: 精确选择并核对状态
  path: click role:option name:label:{{choice}} exact:true，随后 read 同一个 option kind:attribute attribute:aria-selected。读取返回
    true 才可 finish。
  evidence: 该选项的 aria-selected 为 true
---

## 定位与边界

这是中文官方文档中的交互示例，选项内容为英文州名。已实测 query=al，choice=Alabama，同一候选中还含 label:Alaska 和 label:California。必须精确完整匹配，不用子串选第一个。

该示例会异步生成选项，生成的 el-id 每次页面加载可能变化，不硬编码动态 ID，也不使用页面全局 nth。使用唯一容器 text:defaultPlease enter a keyword（无空格）区分另一个 remote-show-suffix 示例；先展开可见占位文字再填写，否则可能无法触发列表。填入文字后容器文本会改变，因此后续动作改用 option 的精确名称和唯一可见 listbox，不继续依赖旧容器文本。

无需读取整页（页面很长，自动快照可能截断）；Skill 已给出实际验证过的定位经验。若页面改版导致容器不存在，报告 blocked，不改选其他演示。这里只验证官方演示的模拟远程加载，不声称发生真实远端数据检索。
