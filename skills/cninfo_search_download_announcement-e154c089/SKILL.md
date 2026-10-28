---
name: cninfo_search_download_announcement
description: 在巨潮资讯网按关键词搜索公司，进入该公司公告列表，点击指定标题的公告打开详情页并下载公告 PDF。适用于查询 A 股上市公司公开公告文件。
params:
- search_keyword
- company_option
- announcement_title
start: https://www.cninfo.com.cn/
goal: 下载标题为 {{announcement_title}} 的公告 PDF 文件并保存成功
actions:
- title: 在首页搜索框输入公司关键词
  tool: fill
  args:
    target:
      placeholder: 代码/简称/拼音/关键字
    value: '{{search_keyword}}'
- title: 等待自动补全候选出现
  tool: wait_for
  args:
    target:
      role: option
      has_text: '{{company_option}}'
      has_text_exact: true
    state: visible
    timeout: 10
- title: 点击匹配的公司候选
  tool: click
  args:
    target:
      role: option
      has_text: '{{company_option}}'
      has_text_exact: true
    wait_after:
      url: '**/disclosure/stock**'
- title: 点击指定标题的公告（新标签页打开）
  tool: click
  args:
    target:
      title: '{{announcement_title}}'
    expect_popup: true
    wait_after:
      target:
        role: button
        has_text: 公告下载
        has_text_exact: true
      state: visible
- title: 点击公告下载并等待文件保存完成
  tool: download
  args:
    target:
      role: button
      has_text: 公告下载
      has_text_exact: true
stages:
- goal: 在巨潮资讯网首页搜索并选中目标公司，进入其公告列表页
  path:
  - 打开 https://www.cninfo.com.cn/
  - 在 placeholder 为 代码/简称/拼音/关键字 的搜索框输入 {{search_keyword}}
  - 等待自动补全下拉出现候选
  - 点击与 {{company_option}} 精确匹配的 option，进入 /new/disclosure/stock 公告列表页
  evidence: 页面 URL 变为 /new/disclosure/stock 且出现公告列表
  observe_when: 自动补全候选项不止一个时须核对完整候选文字（如 600519 A股 贵州茅台）后再点击
  interrupt_when: 搜索后无候选出现，或候选中找不到目标公司
- goal: 在公告列表中打开目标公告详情页
  path:
  - 在公告列表中定位 title 与 {{announcement_title}} 一致的公告链接
  - 点击后新标签页打开 /new/disclosure/detail 详情页
  evidence: 新标签页出现详情页及 公告下载 按钮
  observe_when: 列表可能需滚动或翻页查找完整标题；点击确认会打开新标签页，使用 expect_popup
  interrupt_when: 列表中找不到 {{announcement_title}} 对应的公告
- goal: 下载公告 PDF 并确认保存完成
  path:
  - 在详情页点击 公告下载 按钮
  - download 工具等待文件保存完成
  evidence: download 返回成功（录制中文件 贵州茅台：贵州茅台2026年半年度报告.pdf 约 832KB，PDF 头核验通过）
  observe_when: 点击后按钮短暂显示 下载中，download 工具本身已等待保存完成，无需再等待按钮恢复
  interrupt_when: download 失败或保存内容不是有效 PDF
---

## 使用范围
在巨潮资讯网（cninfo.com.cn）搜索指定 A 股公司，打开其某条公告的详情页并下载公告 PDF。

## 参数
- `search_keyword`：首页搜索框输入的关键词（演示值：茅台）。
- `company_option`：自动补全候选的完整文字，须与页面显示一致（演示值：600519 A股 贵州茅台）。搜索关键词不等于公司候选，二者必须分别提供。
- `announcement_title`：要下载的公告完整标题（演示值：贵州茅台：贵州茅台2026年半年度报告）。不得用搜索词或公司名代替完整公告标题。

## 前提
- 无需登录，公开页面可直接访问。
- 目标公告需出现在该公司公告列表中；如公告较旧需翻页/筛选，本 Skill 未覆盖，需人工辅助。

## 结果与边界
- 完成标准：download 返回成功且为有效 PDF（保存至用户配置的下载目录）。
- 下载按钮点击后短暂显示 下载中，属瞬态界面状态，不作为等待条件。
- 若详情页打开的是内嵌 PDF 查看器异常或下载失败，报告中断，不重试提交。

## 录制定位约束
以下定位以完整 DOM 文字为依据；LLM 执行同样使用，不改为精确 name 或子串匹配：
- {"role": "option", "has_text": "{{company_option}}", "has_text_exact": true}
- {"role": "button", "has_text": "公告下载", "has_text_exact": true}
