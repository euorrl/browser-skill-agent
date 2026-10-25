---
name: cninfo_search_download_announcement
description: 在巨潮资讯网按代码/简称搜索公司，进入公告列表，打开指定公告并下载 PDF。适用于公开公告检索与下载。
params:
- search_keyword
- company_option_text
- announcement_title
start: https://www.cninfo.com.cn/
goal: 在巨潮资讯网搜索 {{search_keyword}} 对应的公司，打开公告《{{announcement_title}}》并下载其 PDF 文件。
actions:
- title: 在首页搜索框输入关键词 {{search_keyword}}，等待自动补全下拉出现 {{company_option_text}}
  tool: fill
  args:
    target:
      placeholder: 代码/简称/拼音/关键字
    value: '{{search_keyword}}'
    wait_after:
      target:
        role: option
        has_text: '{{company_option_text}}'
        has_text_exact: true
      state: visible
      timeout: 10
- title: 点击补全列表中的选项 {{company_option_text}}，等待跳转到公司公告页
  tool: click
  args:
    target:
      role: option
      has_text: '{{company_option_text}}'
      has_text_exact: true
    wait_after:
      url: '**/new/disclosure/stock**'
      timeout: 15
- title: 点击公告链接《{{announcement_title}}》，在新标签页打开公告详情页
  tool: click
  args:
    target:
      role: link
      has_text: '{{announcement_title}}'
      has_text_exact: true
    expect_popup: true
    wait_after:
      target:
        role: button
        has_text: 公告下载
        has_text_exact: true
      state: visible
      timeout: 20
- title: 点击详情页的“公告下载”按钮，保存 PDF 文件
  tool: download
  args:
    target:
      role: button
      has_text: 公告下载
      has_text_exact: true
    filename: '{{announcement_title}}.pdf'
stages:
- goal: 在巨潮资讯网首页搜索 {{search_keyword}}，并从自动补全中精确选择公司 {{company_option_text}}
  path:
  - 打开 https://www.cninfo.com.cn/
  - 在 placeholder 为“代码/简称/拼音/关键字”的搜索框输入 {{search_keyword}}
  - 等待下拉出现选项 {{company_option_text}}（含代码与市场，如“600519 A股 贵州茅台”）后点击
  evidence: 下拉中可见完整公司选项；页面跳转到 /new/disclosure/stock 公司公告页
  observe_when: 补全下拉未出现或选项文字与 {{company_option_text}} 不一致时，用 locate 查看候选再点击
  interrupt_when: 搜索后未出现任何补全选项，或选项均与目标公司不符
- goal: 在公司公告列表中打开公告《{{announcement_title}}》
  path:
  - 在公司公告页定位完整标题为 {{announcement_title}} 的链接（has_text_exact 匹配）
  - 点击链接，新标签页打开公告详情页
  evidence: 新标签页 URL 为 /new/disclosure/detail，且可见“公告下载”按钮
  observe_when: 链接需滚动到视口才能点击时先执行 scroll
  interrupt_when: 公告列表中找不到《{{announcement_title}}》
- goal: 下载公告 PDF 文件
  path:
  - 在详情页点击“公告下载”按钮
  evidence: download 工具返回成功且文件已保存（工具内部等待保存完成，PDF 会核验文件头）
  observe_when: 按钮显示“下载中”为瞬态，不作为等待条件
  interrupt_when: 下载失败或保存的文件不是有效 PDF
---

## 使用范围
在巨潮资讯网公开页面按关键词搜索公司，打开指定公告并下载 PDF。

## 参数
- `search_keyword`：搜索框输入的关键词（代码/简称/拼音/关键字），录制示例为“茅台”。
- `company_option_text`：自动补全下拉中目标公司的完整选项文字，含代码、市场和简称，录制示例为“600519 A股 贵州茅台”。用于精确定位目标公司，不能由关键词推导。
- `announcement_title`：目标公告的完整标题，录制示例为“贵州茅台：贵州茅台2026年半年度报告”。必须包含完整身份（公司前缀、报告类型、年份等），用于链接定位和下载文件名。

## 前提
- 目标公告需存在于公司公告页“最新公告”列表中；若需按日期/分类筛选，本流程未覆盖。
- 未涉及登录，无需账号。

## 结果与边界
- 成功证据为 download 返回成功且文件保存到用户下载目录；文件保存成功即本流程终点，不做后续验证。
- 其他公告或公司取值未经验证，仅录制路径已演示。

## 录制定位约束
以下定位以完整 DOM 文字为依据；LLM 执行同样使用，不改为精确 name 或子串匹配：
- {"role": "option", "has_text": "{{company_option_text}}", "has_text_exact": true}
- {"role": "link", "has_text": "{{announcement_title}}", "has_text_exact": true}
- {"role": "button", "has_text": "公告下载", "has_text_exact": true}
