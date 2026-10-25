---
name: cninfo_download_announcement
description: 在巨潮资讯网按关键字搜索公司并从自动补全中选择目标公司，进入该公司公告列表后打开指定标题的公告详情页，点击“公告下载”保存 PDF 文件。适用于公司已在巨潮网登记且目标公告标题完全已知的场景。
params:
- search_keyword
- stock_option
- announcement_title
- download_name
start: https://www.cninfo.com.cn/
goal: 下载公告《{{announcement_title}}》的 PDF 文件并保存为 {{download_name}}
actions:
- title: 打开巨潮资讯网首页
  tool: goto
  args:
    url: https://www.cninfo.com.cn/
- title: 在搜索框输入公司关键字
  tool: type_text
  args:
    target:
      placeholder: 代码/简称/拼音/关键字
    value: '{{search_keyword}}'
- title: 等待自动补全出现目标公司选项
  tool: wait_for
  args:
    target:
      role: option
      has_text: '{{stock_option}}'
      has_text_exact: true
    state: visible
    timeout: 10
- title: 点击目标公司选项进入公告页
  tool: click
  args:
    target:
      role: option
      has_text: '{{stock_option}}'
      has_text_exact: true
    wait_after:
      url: '**/new/disclosure/stock**'
      timeout: 15
- title: 等待目标公告出现在公告列表
  tool: wait_for
  args:
    target:
      text: '{{announcement_title}}'
      has_text: '{{announcement_title}}'
      has_text_exact: true
    state: visible
    timeout: 15
- title: 点击目标公告，新标签打开详情页
  tool: click
  args:
    target:
      text: '{{announcement_title}}'
      has_text: '{{announcement_title}}'
      has_text_exact: true
    expect_popup: true
    wait_after:
      target:
        role: button
        has_text: 公告下载
        has_text_exact: true
      state: visible
      timeout: 15
- title: 点击公告下载并保存文件
  tool: download
  args:
    target:
      role: button
      has_text_exact: true
      has_text: 公告下载
    filename: '{{download_name}}'
stages:
- goal: 进入巨潮资讯网并搜索公司
  path:
  - goto https://www.cninfo.com.cn/
  - 在 placeholder 为 代码/简称/拼音/关键字 的搜索框逐键输入 {{search_keyword}}
  evidence: 自动补全下拉出现 {{stock_option}} 选项
  observe_when: 输入后下拉未出现时重新观察输入框与候选列表
  interrupt_when: 输入后无任何自动补全候选出现
- goal: 选择目标公司并进入其公告列表
  path:
  - click role=option 且完整文字为 {{stock_option}}（has_text_exact）
  - 等待 URL 进入 /new/disclosure/stock
  evidence: 页面导航到该公司公告列表页
  observe_when: 候选多于一条时必须按完整文字精确选择，不得用 nth:0
  interrupt_when: 点击后未跳转到公告列表页
- goal: 打开目标公告详情页
  path:
  - 等待列表中出现完整标题 {{announcement_title}}，目标为 {"text":"{{announcement_title}}","has_text":"{{announcement_title}}","has_text_exact":true}（text
    定位的精确匹配须同时提供 has_text 与 has_text_exact）
  - click 该标题，expect_popup=true 自动切换到新标签页
  - 在新页等待“公告下载”按钮可见
  evidence: 新标签页 URL 为 /new/disclosure/detail 且公告下载按钮可见
  observe_when: 列表中未找到该标题时先读取列表区域确认公告是否存在
  interrupt_when: 目标公告标题不在列表中或详情页未打开
- goal: 下载公告 PDF
  path:
  - download 按钮：role=button name=公告下载，filename={{download_name}}
  evidence: download 工具返回成功，文件已保存为 {{download_name}}（PDF 已核验文件头）
  observe_when: 下载失败时读取详情页状态按钮提示
  interrupt_when: download 返回失败或保存的不是 PDF 文件
---

## 使用范围
在巨潮资讯网按公司关键字搜索、选中目标公司，进入其公告列表并下载指定标题公告的 PDF。

## 参数
- `search_keyword`：搜索框输入的关键字（录制演示为“茅台”）。
- `stock_option`：自动补全中目标公司选项的完整文字（录制演示为“600519 A股 贵州茅台”），需与候选精确匹配。
- `announcement_title`：目标公告完整标题（录制演示为“贵州茅台：贵州茅台2026年半年度报告”），含年份/类型等区分信息，须与列表中 DOM 文字精确匹配。
- `download_name`：保存的文件名。

## 前提与边界
- 无需登录。
- 公司详情页 URL 中 stockCode 为掩码形式，属站点行为，不影响流程。
- 公告列表默认“最新公告”排序；若目标公告不在当前列表中，需补充翻页或筛选证据后扩展本 Skill。
- 搜索关键字到公告列表的映射依赖站点行为，`stock_option` 与 `announcement_title` 必须由调用者预先确定，不能由关键字推导。
- 下载成功以 download 工具返回（文件已保存且核验为 PDF）为准；不以页面按钮文字恢复作为完成条件。

## 录制定位约束
以下定位以完整 DOM 文字为依据；LLM 执行同样使用，不改为精确 name 或子串匹配。注意：text 目标的 has_text_exact 必须与 has_text 同时提供：
- {"role": "option", "has_text": "{{stock_option}}", "has_text_exact": true}
- {"text": "{{announcement_title}}", "has_text": "{{announcement_title}}", "has_text_exact": true}
- {"role": "button", "has_text": "公告下载", "has_text_exact": true}
- {"role": "button", "has_text_exact": true, "has_text": "公告下载"}
