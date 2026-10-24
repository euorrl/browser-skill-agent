---
name: bejson_timestamp_precision
description: 在 BeJSON 中文工具中验证秒/毫秒精度切换、动态字段显示、数值表单和双向转换完成状态；使用固定非敏感基准值，不涉及账户或外部提交。
start: https://www.bejson.com/convert/unix/
goal: 先选10位秒级并将时间戳0转换，等待并读取1970-01-01 08:00:00；再选13位毫秒级，等待毫秒字段出现，填写2024年1月1日08:00:00及123毫秒，转换并读取1704067200123；最后反向转换此时间戳，等待并读取2024-01-01
  08:00:00 123。必须实际完成全部三项，不仅口算。
actions:
- tool: set_checked
  args:
    target:
      role: radio
      name: 10位时间戳(秒级)
    checked: true
- tool: fill
  args:
    target:
      id: unixtime
    value: '0'
- tool: click
  args:
    target:
      role: button
      name: 转换日期→
    wait_after:
      target:
        id: result_GMT
      state: value
      value: '1970-01-01 08:00:00'
      timeout: 15
- tool: read
  args:
    target:
      id: result_GMT
    kind: value
- tool: set_checked
  args:
    target:
      role: radio
      name: 13位时间戳(豪秒级)
    checked: true
    wait_after:
      target:
        id: msecond
      state: visible
- tool: fill
  args:
    target:
      id: year
    value: '2024'
- tool: fill
  args:
    target:
      id: month
    value: '1'
- tool: fill
  args:
    target:
      id: day
    value: '1'
- tool: fill
  args:
    target:
      id: hour
    value: '8'
- tool: fill
  args:
    target:
      id: minute
    value: '0'
- tool: fill
  args:
    target:
      id: second
    value: '0'
- tool: fill
  args:
    target:
      id: msecond
    value: '123'
- tool: click
  args:
    target:
      role: button
      name: 转换时间戳→
    wait_after:
      target:
        id: result_unix
      state: value
      value: '1704067200123'
      timeout: 15
- tool: read
  args:
    target:
      id: result_unix
    kind: value
- tool: fill
  args:
    target:
      id: unixtime
    value: '1704067200123'
- tool: click
  args:
    target:
      role: button
      name: 转换日期→
    wait_after:
      target:
        id: result_GMT
      state: value
      value: 2024-01-01 08:00:00 123
      timeout: 15
- tool: read
  args:
    target:
      id: result_GMT
    kind: value
stages:
- goal: 秒级转换
  path: set_checked role:radio name:10位时间戳(秒级) checked:true；fill id:unixtime value:0；click button 转换日期→，wait_after
    id:result_GMT state:value value:1970-01-01 08:00:00；read 同一输入框 kind:value。
  evidence: 实际输出1970-01-01 08:00:00
- goal: 毫秒字段与日期转时间戳
  path: set_checked radio 名称13位时间戳(豪秒级)（网页原文就是豪），checked:true，wait_after id:msecond visible；连续 fill id year=2024、month=1、day=1、hour=8、minute=0、second=0、msecond=123；click
    button 转换时间戳→，wait_after id:result_unix state:value value:1704067200123；read id:result_unix kind:value。
  evidence: 动态毫秒字段出现且结果为1704067200123
- goal: 反向转换并总结
  path: fill id:unixtime value:1704067200123；click 转换日期→；wait_after id:result_GMT state:value value:2024-01-01 08:00:00
    123；read kind:value，全部三项读取成功后 finish。
  evidence: 实际反向结果与输入日期精度一致
---

## 环境与定位

按网页标示的北京时间运行，测试环境时区 Asia/Shanghai。若结果时区不同，应报告 blocked 而不是修改期待值伪装通过。使用实际 id 定位数值字段，避免多个同名 spinbutton。不要改页面顶部自动更新的 now_timestamp，它不是转换输入；应填 unixtime。read 输入框必须 kind:value。网站广告、外链和功能搜索均与本任务无关，不点击。
