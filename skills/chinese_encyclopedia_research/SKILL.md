---
name: chinese_encyclopedia_research
description: 在中文维基百科通过高级搜索查询两个主题并收集条目资料。当用户需要中文主题调研、来源核对或双主题比较时使用；涵盖折叠条件、自定义下拉、复选框、容器定位和多标签页。
params:
- topic_a
- topic_b
start: https://zh.wikipedia.org/w/index.php?title=Special:Search&uselang=zh-cn
goal: 在中文维基百科高级搜索中分别查询 {{topic_a}} 和 {{topic_b}}，以标题关键词和默认条目范围搜索，按相关性排序，进入准确条目并读取正文和来源。脚本模式输出两份原始资料；LLM
  模式根据实际资料给出中文比较。
actions:
- title: 第一个主题：展开高级搜索
  tool: click
  args:
    target:
      role: button
      name: 高级搜索：
    wait_after:
      target:
        role: textbox
        name: 页面标题含有
      timeout: 30
- title: 第一个主题：填写标题关键词
  tool: fill
  args:
    target:
      role: textbox
      name: 页面标题含有
    value_ref: topic_a
- title: 第一个主题：展开自定义排序下拉
  tool: click
  args:
    target:
      role: combobox
      name: 排序方式 按相关性排序
    wait_after:
      target:
        role: option
        name: 按相关性排序
- title: 第一个主题：选择相关性排序
  tool: click
  args:
    target:
      role: option
      name: 按相关性排序
- title: 第一个主题：展开搜索范围
  tool: click
  args:
    target:
      role: button
      name: 搜索：
    wait_after:
      target:
        role: checkbox
        name: 默认
- title: 第一个主题：使用默认条目范围
  tool: set_checked
  args:
    target:
      role: checkbox
      name: 默认
    checked: true
- title: 第一个主题：提交搜索并等待新结果
  tool: click
  args:
    target:
      role: button
      name: 搜索
      within:
        role: main
    wait_after:
      target:
        role: heading
        name: 搜索结果
      timeout: 30
- title: 第一个主题：进入指定条目
  tool: click
  args:
    target:
      role: link
      name: '{{topic_a}}'
      within:
        role: listitem
        has_text: 字）
        within:
          id: mw-content-text
    wait_after:
      target:
        id: firstHeading
      state: text
      value: '{{topic_a}}'
      timeout: 30
- title: 第一个主题：已读取条目标题
  tool: read
  args:
    target:
      id: firstHeading
    kind: text
    max_chars: 100
- title: 第一个主题：正文摘录（最多 600 字符）
  tool: read
  args:
    target:
      id: mw-content-text
    kind: text
    max_chars: 600
- title: 在新标签页查询第二个主题
  tool: tabs
  args:
    action: new
    url: https://zh.wikipedia.org/w/index.php?title=Special:Search&uselang=zh-cn
- title: 第二个主题：展开高级搜索
  tool: click
  args:
    target:
      role: button
      name: 高级搜索：
    wait_after:
      target:
        role: textbox
        name: 页面标题含有
      timeout: 30
- title: 第二个主题：填写标题关键词
  tool: fill
  args:
    target:
      role: textbox
      name: 页面标题含有
    value_ref: topic_b
- title: 第二个主题：展开自定义排序下拉
  tool: click
  args:
    target:
      role: combobox
      name: 排序方式 按相关性排序
    wait_after:
      target:
        role: option
        name: 按相关性排序
- title: 第二个主题：选择相关性排序
  tool: click
  args:
    target:
      role: option
      name: 按相关性排序
- title: 第二个主题：展开搜索范围
  tool: click
  args:
    target:
      role: button
      name: 搜索：
    wait_after:
      target:
        role: checkbox
        name: 默认
- title: 第二个主题：使用默认条目范围
  tool: set_checked
  args:
    target:
      role: checkbox
      name: 默认
    checked: true
- title: 第二个主题：提交搜索并等待新结果
  tool: click
  args:
    target:
      role: button
      name: 搜索
      within:
        role: main
    wait_after:
      target:
        role: heading
        name: 搜索结果
      timeout: 30
- title: 第二个主题：进入指定条目
  tool: click
  args:
    target:
      role: link
      name: '{{topic_b}}'
      within:
        role: listitem
        has_text: 字）
        within:
          id: mw-content-text
    wait_after:
      target:
        id: firstHeading
      state: text
      value: '{{topic_b}}'
      timeout: 30
- title: 第二个主题：已读取条目标题
  tool: read
  args:
    target:
      id: firstHeading
    kind: text
    max_chars: 100
- title: 第二个主题：正文摘录（最多 600 字符）
  tool: read
  args:
    target:
      id: mw-content-text
    kind: text
    max_chars: 600
- title: 列出保留的资料标签页
  tool: tabs
  args:
    action: list
stages:
- goal: 搜索 {{topic_a}} 并取得条目候选
  path:
  - 若标题输入框尚不可见，点击 button 高级搜索：，wait_after 等待 role textbox、name 页面标题含有；不要用同名 text 等待。
  - fill 标题输入框，value_ref 为 topic_a；检查当前排序和范围，已为相关性及默认范围时不重复操作。
  - 若需调整排序或范围，使用下文已知定位；未知选项先观察，不猜测。
  - 点击 main 内的 button 搜索，wait_after 等待 heading 搜索结果；expected_url 为 https://zh.wikipedia.org/w/index.php*。
  - 紧接着 read 结果区域 id mw-content-text，max_chars 为 1600，读取候选后交回模型选择条目。
  evidence: 搜索结果已出现，读取到 {{topic_a}} 的百科候选与可区分的列表上下文。
  observe_when: 结果列表读取后；已知面板展开、填写和搜索无需各调用一次模型。
  interrupt_when: 已知定位不唯一、选项不符合经验、等待失败或出现意外页面时提前观察。
- goal: 进入并读取 {{topic_a}} 条目
  path:
  - 根据刚读取的结果选择准确链接；优先限定 mw-content-text 内含“字）”的 listitem，不硬编码会变化的具体字数。
  - click 后 wait_after 等待 heading 名称准确匹配 {{topic_a}}；动作顶层 expected_url 为 https://zh.wikipedia.org/wiki/*。
  - 同一阶段继续 read id mw-content-text，max_chars 为 600；来源使用读取结果的 URL。
  evidence: 目标标题等待成功，已读取正文摘录和来源 URL。
  observe_when: 正文读取后；不要仅进入条目便结束计划。
  interrupt_when: 标题不符、重定向到消歧义页、无法唯一定位或要求登录。
- goal: 搜索 {{topic_b}} 并取得条目候选
  path:
  - tabs new 打开任务 start；expected_url 为 https://zh.wikipedia.org/w/index.php*，wait_after 等待 button 高级搜索：。
  - 同一阶段继续执行第一个主题的已知搜索路径，填写时 value_ref 改为 topic_b，末尾 read 搜索结果。
  evidence: 第二个主题的候选已读取，第一份正文证据仍保留。
  observe_when: 第二次结果列表读取后；预期新标签页加载成功可继续设置已知表单。
  interrupt_when: 意外弹窗、等待失败或搜索界面结构改变。
- goal: 进入并读取 {{topic_b}} 条目
  path:
  - 复用第一个条目的进入与读取路径，标题等待改为 {{topic_b}}，同一阶段点击、等待和读取正文。
  evidence: 第二个主题准确标题、正文摘录及来源已取得。
  observe_when: 正文读取后，不为找回第一份资料反复切页。
  interrupt_when: 与第一个主题相同；缺少准确条目时不替换成其他主题。
- goal: 比较资料并结束
  evidence: 中文比较依据两份实际正文摘录，并列出两个来源，不声称阅读全文。
  observe_when: 资料缺失时补读，否则使用 evidence 单独返回 finish。
---

## 使用范围与参数

只读查询中文维基百科，不登录、不编辑条目、不下载、不捐款。网站需能从本机正常访问。

- `topic_a`：第一个主题，也是预期条目的准确中文标题。
- `topic_b`：第二个主题，也是预期条目的准确中文标题。

可用“人工智能”和“机器学习”演示。不要把主题写成一整段提问。标题应与网站显示文字一致；简繁体、重定向和消歧义可能导致准确标题不匹配。

## 执行方法

1. 打开简体中文界面的高级搜索，展开“高级搜索：”，在“页面标题含有”中填写主题。
2. 展开“排序方式”自定义下拉并选择“按相关性排序”；展开“搜索：”，勾选“默认”，仅使用默认条目范围。
3. 在 main 容器内点击“搜索”，等待“搜索结果”标题出现。顶部另有同名搜索按钮，不要混用。
4. 从正文搜索结果中定位准确标题的条目链接，进入对应条目，等待标题与输入相符，再读取正文。
5. 新建标签页查询第二个主题，保留第一份资料页面，任务完成后默认保留浏览器，可查看两个标签页；在终端按回车后关闭。

默认 actions 共 22 步，在 30 步上限内完成。每次重新打开搜索入口，避免上次的筛选条件混入新查询。此流程不保存账号偏好。

## 定位与加载经验

- 高级搜索界面由脚本加载。使用目标可操作等待与 wait_after，不靠固定休眠判断页面完成。
- 排序控件可见部分是自定义 combobox（名称“排序方式 按相关性排序”），选项 role option、name 按相关性排序；仅在需要修改时展开。不要等待选中选项一定隐藏，改为确认 combobox 的显示状态。范围面板 button 搜索：，范围 checkbox 默认；已正确时跳过。不对隐藏原生 select 强制操作。
- 搜索结果可能同时出现同名百科和维基词典链接。actions 使用正文内带“字）”字数摘要的 listitem 限定百科结果，不选择跨站词典链接，也不默认点击第一个同名元素。
- `mw-content-text` 和 `firstHeading` 来自实际页面。若站点改版、摘要格式变化、目标不在当前结果页、网络失败或要求登录，脚本会停止。不要自动改选其他条目。
- 默认模式不输出候选元素元数据；点击时仍要求目标唯一。LLM 模式遇到歧义时可以使用 locate。

## 结果与完成条件

脚本模式：只输出每个主题的实际条目标题、来源 URL 和最多 600 字符的正文摘录，不输出全文与候选元素元数据。标题等待条件通过且正文读取成功，可据此确认进入了目标页面并取得内容；不代表阅读全文或验证文章事实。succeeded 仅表示预设步骤及等待条件完成。

LLM 模式：不必机械复现所有示范步骤。完成两个准确主题的查询，依据实际读到的正文，用中文简短列出两个实际标题、各一句概括、关系或差异，以及两个来源 URL。最终说明控制在约 300 字以内，不粘贴长篇正文。不得把搜索摘要当成已经核对的全文。第一份资料离开近期动作上下文后优先使用 evidence；只有证据缺失或不足时才补读，不凭记忆补全。只要求局部内容时优先 snapshot/read 局部范围。

未找到准确条目或未能读取任一份资料时，报告 blocked，说明停在哪个主题和步骤，列出已取得的来源，不编造比较结论。

## LLM 分阶段执行

stages 提供已知路径、证据和中断条件，不是必须从头重放的脚本。优先一次规划完整阶段，按当前页面跳过已完成部分。预期导航在动作顶层声明 expected_url，且 args.wait_after 验证目标页面后，可以继续已知操作；读取结果、关键授权操作或异常仍提前交回模型。成功读取暂存于 evidence，优先复用来源和摘录。通常按两个搜索阶段、两个正文阶段和最后总结推进，但错误、授权或未知选项可能增加模型调用，不保证固定次数。
