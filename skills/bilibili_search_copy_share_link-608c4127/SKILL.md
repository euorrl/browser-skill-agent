---
name: bilibili_search_copy_share_link
description: 在哔哩哔哩按视频 BV 号搜索指定视频，打开视频页并复制其分享链接。适用于调用者提供完整 BV 号（如 BV1Vbnn6iEfG）的场景。
params:
- video_id
- video_title
start: https://www.bilibili.com
goal: 找到视频 {{video_id}} 对应的视频页，并复制该视频的分享链接
actions:
- title: 填写 BV 号
  tool: fill
  args:
    target: &id001
      role: textbox
      within:
        id: nav-searchform
    value_ref: video_id
- title: 回车搜索并切换新标签页
  tool: press
  args:
    target: *id001
    key: Enter
    expect_popup: true
    wait_after:
      url: '**/search.bilibili.com/all**'
      timeout: 30
- title: 打开 BV 号对应的视频
  tool: click
  args:
    target:
      role: link
      has_text: '{{video_id}}'
    expect_popup: true
    wait_after:
      url: '**/video/{{video_id}}/**'
      timeout: 30
- title: 确认目标视频标题
  tool: wait_for
  args:
    target:
      role: heading
      name: '{{video_title}}'
    state: visible
    timeout: 30
- title: 展开分享面板
  tool: hover
  args:
    target:
      id: share-btn-outer
    wait_after:
      target:
        id: share-btn-inner
      state: visible
      timeout: 15
- title: 复制视频分享链接
  tool: click
  args:
    target:
      id: share-btn-inner
- title: 读取目标视频标题
  tool: read
  args:
    target:
      role: heading
      name: '{{video_title}}'
    kind: text
    max_chars: 200
stages:
- goal: 搜索并打开指定 BV 号的视频
  path:
  - 在 nav-searchform 内 textbox 填写 video_id
  - press Enter 使用 expect_popup=true
  - 点击包含 video_id 的链接，expect_popup=true
  evidence: 视频 URL 包含目标 BV 号，heading 与 video_title 一致
  observe_when: 打开视频后
  interrupt_when: 结果不唯一、页面受限或标题不符
- goal: 复制分享链接
  path:
  - hover share-btn-outer
  - 等待 share-btn-inner 可见并 click
  - 读取标题
  evidence: 复制按钮已执行；当前工具不能独立核验剪贴板，不能将标题读取当作复制成功证据
  observe_when: 复制后
  interrupt_when: 面板或复制按钮不可用
login: null
---

按 BV 号搜索、打开目标视频并点击复制分享链接。搜索推荐词会变化，使用 nav-searchform 容器内 textbox。搜索和打开视频均产生新标签页，必须 expect_popup=true。搜索结果链接包含 BV 号和标题，以 video_id 过滤并保持严格唯一匹配。video_title 用于进入后的身份确认。分享控件用录制及现场确认的 id；不依赖播放量或暂停状态。步骤完成不等于剪贴板已核验，不能将读取标题当作业务验收。

## 验证来源

本版本由开发调试手工修正，已使用项目 runtime 实测固定参数的 7 步脚本执行及复制结果。该结果不代表录制生成器可以自动产出本版本，自动生成闭环仍需独立验证。
