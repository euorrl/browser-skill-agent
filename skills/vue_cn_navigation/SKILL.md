---
name: vue_cn_navigation
description: 操作 Vue 中文官方文档中的响应式计数器，访问两篇文档并返回，验证 SPA URL 跳转、返回及动态元素重新定位。不登录、不改远端数据。
start: https://cn.vuejs.org/guide/introduction.html
goal: '点击简介页 Count is: 0 一次，等待并读取 Count is: 1；经侧边栏访问快速上手并读取标题，返回简介；再访问响应式基础读取正文，最后返回简介并读取标题和实际 URL。所有三项均需完成，不用演练场或外站。'
actions:
- tool: wait_for
  args:
    target:
      role: button
      name: 'Count is: 0'
    state: visible
    timeout: 30
  title: 等待动态计数器加载
- title: 关闭首次访问偏好提示，避免遮挡导航
  tool: click
  args:
    target:
      role: button
      name: 知道了
    wait_after:
      target:
        role: button
        name: 知道了
      state: hidden
- title: 收起 API 风格面板
  tool: click
  args:
    target:
      role: button
      name: 偏好切换开关
    wait_after:
      target:
        role: switch
        name: 偏好组合式 API
      state: hidden
- tool: click
  args:
    target:
      role: button
      name: 'Count is: 0'
    wait_after:
      target:
        role: button
        name: 'Count is: 1'
      state: visible
      timeout: 30
  title: 触发响应式 DOM 更新
- tool: read
  args:
    target:
      role: button
      name: 'Count is: 1'
  title: 读取点击后的计数
- tool: click
  args:
    target:
      role: link
      name: 快速上手
      within: &id003
        role: navigation
        name: 侧边栏导航
    wait_after:
      target: &id001
        role: heading
        name: 快速上手
        exact: false
      state: visible
      timeout: 30
  title: 访问快速上手
- tool: read
  args:
    target: *id001
    max_chars: 200
  title: 读取快速上手标题
- tool: back
  args:
    wait_after:
      target: &id002
        role: heading
        name: 简介
        exact: false
      state: visible
      timeout: 30
  title: 返回简介
- tool: read
  args:
    target: *id002
    max_chars: 200
  title: 确认返回简介
- tool: click
  args:
    target:
      role: link
      name: 响应式基础
      within: *id003
    wait_after:
      target:
        role: heading
        name: 响应式基础
        exact: false
      state: visible
      timeout: 30
  title: 访问响应式基础
- tool: read
  args:
    target:
      role: main
    max_chars: 800
  title: 读取响应式基础正文
- tool: back
  args:
    wait_after:
      target: *id002
      state: visible
      timeout: 30
  title: 再次返回简介
- tool: read
  args:
    target: *id002
    max_chars: 200
  title: 确认最终简介页面
stages:
- goal: 验证动态计数器
  path: '首次临时会话先点击 button 知道了，等待其隐藏；如果 button 偏好切换开关 的 aria-expanded 为 true，点击它收起面板并等待 switch 偏好组合式 API hidden，防止遮挡侧边栏。等待
    role button 名称 Count is: 0，click 一次并 wait_after 等待 Count is: 1，然后 read 该按钮。'
  evidence: '实际按钮文本为 Count is: 1'
- goal: 快速上手往返
  path: click role link 快速上手，within 为 role navigation 名称 侧边栏导航；wait_after 等待 role heading 名称 快速上手 exact:false；动作
    expected_url=https://cn.vuejs.org/guide/quick-start*，随后 read 标题。再 back，wait_after 简介 heading exact:false，并 read
    标题。
  evidence: 已经读取快速上手和返回的简介标题
- goal: 响应式基础往返
  path: 同样从侧边栏进入响应式基础；expected_url=https://cn.vuejs.org/guide/essentials/reactivity-fundamentals*；wait_after 等待相应
    heading exact:false，read main 最多800字符；back 后等待简介 heading，read 简介标题后 finish。
  evidence: 实际读到响应式基础正文，最终在简介URL
---

## 定位经验

标题含锚点链接，heading 名称使用 exact:false；侧边栏链接使用 exact:true 和具名 navigation 容器。网站可能移除 .html 后缀，以实际 URL 为准。不要把链接的文章标题当成已读取正文。Count is: 1 必须来自实际按钮，不是代码片段。返回后 DOM 可能重新创建，不复用旧元素句柄。最终报告三个验证点和最终 URL。
