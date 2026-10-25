---
name: huya_search_open_live_room
description: 在虎牙直播按关键词搜索游戏分区，确认目标主播在播后进入其直播间并切换到指定画质。使用条件：调用者需提供搜索关键词和主播名，房间号固定为 312410；未登录状态仅能选择免费画质（超清/流畅），蓝光需登录。
params:
- search_keyword
- streamer_name
- quality
start: https://www.huya.com/search?hsk={{search_keyword}}
goal: 进入主播 {{streamer_name}} 的直播间 312410 并切换至 {{quality}} 画质
actions:
- title: 打开搜索结果页（按关键词）
  tool: goto
  args:
    url: https://www.huya.com/search?hsk={{search_keyword}}
    wait_after:
      target:
        role: link
        has_text: '{{streamer_name}}'
      state: visible
      timeout: 15
- title: 确认目标主播在搜索结果中
  tool: read
  args:
    target:
      role: link
      has_text: '{{streamer_name}}'
    kind: text
    max_chars: 300
- title: 进入直播间页面（房间号 312410）
  tool: goto
  args:
    url: https://www.huya.com/312410
    wait_after:
      target:
        text: 关注
      state: visible
      timeout: 15
- title: 如出现广告浮层则点击跳过
  tool: click
  args:
    target:
      text: 跳过
      visible: true
- title: 点击播放器全屏按钮（同时唤出设置面板）
  tool: click
  args:
    target:
      test_id: player-fullscreen-btn
    wait_after:
      target:
        text: 画质
      state: visible
      timeout: 10
- title: 点击目标画质选项
  tool: click
  args:
    target:
      text: '{{quality}}'
    wait_after:
      target:
        role: status
      state: text
      value: 成功为你切换至{{quality}}
      timeout: 15
- title: 读取切换成功提示作为完成证据
  tool: read
  args:
    target:
      role: status
    kind: text
    max_chars: 200
stages:
- goal: 按 {{search_keyword}} 打开搜索结果页并确认 {{streamer_name}} 的直播间在播
  path:
  - goto https://www.huya.com/search?hsk={{search_keyword}}
  - 等待包含 {{streamer_name}} 的主播链接可见
  - 读取该链接短摘录确认主播信息
  evidence: 结果页标题为『{{search_keyword}}-搜索-专找直播-虎牙直播』，且出现含 {{streamer_name}} 的主播链接
  observe_when: 搜索页加载后、点击任何主播前；搜索结果每次刷新可能变化
  interrupt_when: 结果页未出现 {{streamer_name}} 的主播链接，说明该主播当前未在播或关键词无结果
- goal: 进入 312410 直播间并等待播放器就绪
  path:
  - goto https://www.huya.com/312410
  - 等待直播间标题/关注区域可见
  - 若出现广告浮层（内容为『跳过 内容质量差…』）点击『跳过』
  evidence: 页面标题包含主播直播间名称，正文出现房间号 312410 和播放器区域
  observe_when: 进入房间后先 snapshot 确认广告浮层是否存在，避免盲目点击『跳过』
  interrupt_when: 房间不存在或未在播（无播放器/提示下架）
- goal: 点击全屏并切换至 {{quality}} 画质
  path:
  - click player-fullscreen-btn
  - 等待画质菜单出现
  - 点击画质选项 {{quality}}
  - 等待并读取『成功为你切换至{{quality}}』提示
  evidence: 出现『成功为你切换至 {{quality}}』提示文字；此前播放器显示的是旧画质
  observe_when: 全屏点击后画质菜单；提示文字为一次性状态提示，需在切换后短时间内读取
  interrupt_when: 画质项显示『请先登录』（蓝光类画质未登录不可选）或切换提示未出现
---

## 使用范围
按关键词搜索虎牙直播分区，确认指定主播在播后进入其直播间，点击播放器全屏并切换到目标画质。

## 参数
- `search_keyword`：搜索的游戏/分区关键词，如 `炉石传说`。
- `streamer_name`：目标主播名称，用于在搜索结果中确认在播，如 `炉石春哥`。
- `quality`：目标画质名称，演示值 `超清`；未登录仅 `超清`/`流畅` 可选，蓝光需登录账号。

## 固定值
- 房间号固定为 `312410`，直接用该房间号进入房间，避免录制中『点击主播链接后新标签页无法可靠切换』的问题。

## 前提与边界
- 未登录状态执行，不做登录、关注、发弹幕、送礼等操作。
- 房间内可能出现广告浮层，存在时点击『跳过』；脚本模式为固定顺序，若浮层不存在该点击可能失败，由 LLM 按阶段观察后处理。
- 完成标准：出现『成功为你切换至{{quality}}』提示。该提示是一次性状态，需切换后立即读取。
- 全屏按钮在部分无头环境可能不生效；全屏失败不影响画质切换目标。
- 主播搜索结果中显示的粉丝数等动态文字不可作为定位依据，仅用主播名 has_text 匹配。
