---
name: chinese_image_file_pipeline
description: 在中文图片压缩网站分别选择并处理两张 PNG，再批量处理并分别下载两份结果；覆盖多次文件选择、动态结果重建、明确完成等待和多个下载。文件在浏览器本地处理，不声称服务器上传。
params:
- file_a
- file_b
file_params:
  uploads:
  - file_a
  - file_b
  upload_dir: source_dir
  download_dir: save_dir
start: https://www.onlineimagecompression.org/zh/
goal: 依次选择 {{file_a}} 和 {{file_b}} 两个不同PNG文件，分别开始压缩并等待完成，各下载一次；重置后一次选择两文件，等待两项处理完成并逐张下载两份结果。总计四个PNG下载结果。只使用本次上传清单；报告文件名、处理完成证据和下载工具实际返回的路径。不把文件选择当作服务器上传。
actions:
- tool: upload
  args:
    target:
      id: file-input
    file_ids:
    - u1
    wait_after:
      target:
        id: selected-files-list
      state: text
      value: '{{file_a}}'
      timeout: 20
  title: 选择第1个文件
- tool: click
  args:
    target:
      role: button
      name: 开始压缩
    wait_after:
      target:
        id: error-message
      state: text
      value: 压缩完成！共处理1张图片
      timeout: 30
  title: 处理第1个文件并等待完成
- tool: read
  args:
    target:
      id: file-list
    max_chars: 500
  title: 读取第1个处理结果
- tool: download
  args:
    target:
      role: button
      name: 下载
      within:
        id: file-list
    filename: result-1.png
  title: 保存第1个结果
- tool: click
  args:
    target:
      role: button
      name: 重置
    wait_after:
      target:
        id: result-section
      state: hidden
      timeout: 10
  title: 重置第一批结果
- tool: upload
  args:
    target:
      id: file-input
    file_ids:
    - u2
    wait_after:
      target:
        id: selected-files-list
      state: text
      value: '{{file_b}}'
      timeout: 20
  title: 选择第2个文件
- tool: click
  args:
    target:
      role: button
      name: 开始压缩
    wait_after:
      target:
        id: error-message
      state: text
      value: 压缩完成！共处理1张图片
      timeout: 30
  title: 处理第2个文件并等待完成
- tool: read
  args:
    target:
      id: file-list
    max_chars: 500
  title: 读取第2个处理结果
- tool: download
  args:
    target:
      role: button
      name: 下载
      within:
        id: file-list
    filename: result-2.png
  title: 保存第2个结果
- tool: click
  args:
    target:
      role: button
      name: 重置
    wait_after:
      target:
        id: result-section
      state: hidden
  title: 重置后开始双文件批处理
- tool: upload
  args:
    target:
      id: file-input
    file_ids:
    - u1
    - u2
    wait_after:
      target:
        id: selected-count
      state: text
      value: 已选择2张图片
  title: 一次选择两个不同文件
- tool: click
  args:
    target:
      role: button
      name: 开始压缩
    wait_after:
      target:
        id: error-message
      state: text
      value: 压缩完成！共处理2张图片
      timeout: 30
  title: 批量处理并等待两项完成
- tool: read
  args:
    target:
      id: file-list
    max_chars: 1000
  title: 读取两项批处理结果
- title: 确认批处理存在两个下载按钮
  tool: wait_for
  args:
    target:
      role: button
      name: 下载
      within:
        id: file-list
    state: count
    value: 2
- title: 保存批处理第一份PNG
  tool: download
  args:
    target:
      role: button
      name: 下载
      within:
        id: file-list
      nth: 0
    filename: batch-1.png
- title: 保存批处理第二份PNG
  tool: download
  args:
    target:
      role: button
      name: 下载
      within:
        id: file-list
      nth: 1
    filename: batch-2.png
stages:
- goal: 第一个文件处理与下载
  path: upload target id:file-input，file_ids:[u1]，wait_after 等待 id:selected-files-list 包含 {{file_a}}；click button
    开始压缩，wait_after 等待 id:error-message text=压缩完成！共处理1张图片；read id:file-list；下一轮 download button 下载 within id:file-list，filename=result-1.png。
  evidence: 处理完成文字和下载工具返回保存路径
- goal: 第二个文件处理与下载
  path: 第一项下载成功后 click button 重置，等待 id:result-section hidden；同样使用 u2 和 {{file_b}}，等待完成后读取结果并 download 为 result-2.png。
  evidence: 第二项对应文件已处理并保存
- goal: 双文件批量处理与两份下载
  path: 第二项下载成功后重置；upload file_ids:[u1,u2] 到 id:file-input；等待 id:selected-count text=已选择2张图片；click 开始压缩并等待 id:error-message
    text=压缩完成！共处理2张图片；read id:file-list。读取证明顺序为 {{file_a}}、{{file_b}} 后，wait_for role:button name:下载 within id:file-list
    state:count value:2；分别 download 同一容器内第0/1个下载按钮，filename=batch-1.png/batch-2.png。全部四个文件下载成功后 finish，不点击批量下载。
  evidence: 两项完成，四个下载工具均成功返回保存路径
---

## 文件与完成条件

网站“批量下载”按钮实测是多次触发下载而非ZIP，当前单次 download 工具只接收一个事件，因此不要点击它。批处理 read 确认文件顺序和两个按钮数量后，允许在 id:file-list 容器内用 nth:0 和 nth:1 分别保存，这里序号对应刚确认的固定输入顺序；顺序或数量不符就停止。

file_a/file_b 必须为不同的 PNG 文件名（不带目录），放在 files/uploads 或 source_dir。重复选择文件会替换整个列表，不会追加。重置会删除网页当前结果，必须先下载再重置。所有 ID 来自实际页面，使用 id 字段而非 test_id。PNG 不一定变小，不把压缩率为负误判成工具失败；目标是处理并保存，不保证缩小体积。下载工具已等待下载保存成功，无需额外固定 sleep；不得用 click 代替 download。无服务器文件上传请求，本 Skill 验证本地文件选择/处理和真实下载。
