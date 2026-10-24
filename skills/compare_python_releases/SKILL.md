---
name: compare_python_releases
description: 比较 Python 官网两个指定版本的发布日期和同类安装包信息。当用户需要核对版本发布信息、比较安装包大小并获取官方来源时使用；不用于下载或安装软件。
params: [version_a, version_b, package_name]
start: "https://www.python.org/downloads/"
goal: "实际访问 Python {{version_a}} 和 Python {{version_b}} 的官方发布页，分别读取发布日期及 {{package_name}} 的文件信息，最后用中文给出对比结果和两个发布页地址。"
actions:
- title: 打开第一个版本
  tool: click
  args:
    target:
      role: link
      name: Python {{version_a}}
    wait_after:
      target:
        role: heading
        name: Python {{version_a}}
      timeout: 30
- title: 第一个版本发布日期和文件信息
  tool: read
  args:
    target:
      role: main
    kind: text
- title: 第一个版本目标安装包
  tool: read
  args:
    target:
      role: row
      has_text: '{{package_name}}'
    kind: text
- title: 返回官方下载列表
  tool: goto
  args:
    url: https://www.python.org/downloads/
- title: 打开第二个版本
  tool: click
  args:
    target:
      role: link
      name: Python {{version_b}}
    wait_after:
      target:
        role: heading
        name: Python {{version_b}}
      timeout: 30
- title: 第二个版本发布日期和文件信息
  tool: read
  args:
    target:
      role: main
    kind: text
- title: 第二个版本目标安装包
  tool: read
  args:
    target:
      role: row
      has_text: '{{package_name}}'
    kind: text
---

## 默认脚本模式

默认按 actions 读取两个版本的发布页正文及指定文件行，分别输出供对照；不调用模型生成日期或大小的比较结论。需要自动中文比较总结时加 --llm。


## 使用范围与输入

用于 Python 官方发布信息的跨页查询和比较。具体版本与安装包由调用方提供，不预设版本、平台或比较结果。只读取页面，不下载安装包，不安装软件。

| 参数 | 含义 |
| --- | --- |
| version_a | 第一个完整版本号 |
| version_b | 第二个完整版本号 |
| package_name | 官网文件表中的准确名称，两个版本使用同一名称 |

## 执行方法

1. 从官方下载列表找到指定版本的链接，进入发布页并确认标题中的完整版本号。
2. 读取发布日期、目标安装包所在文件行及发布页 URL。离开前通过 read 保留这些证据。
3. 对另一个指定版本重复查询。若近期工具结果已不包含第一份证据，返回对应页面补读，不凭记忆补全。
4. 根据本次读取的内容比较发布日期与安装包大小，并给出来源。

按当前页面状态执行，已完成的查询不必重复。参数缺失时由调用方补齐，不能自行选择其他版本或安装包。

## 页面操作提示

- 下载列表里的多个链接都叫 Download。优先选择名称为 Python 加完整版本号的链接，避免同名链接歧义。
- 不要点击“已被新版本取代”提示中的其他版本。即使目标版本较旧，也必须查询传入的确切版本。
- 链接名称以实际页面为准，不翻译页面上的英文名称，不猜测发布页 URL。
- 发布页的 Release date 是发布日期；Files 区域包含文件表格。目标是名称严格对应 {{package_name}} 的文件行，不要混淆 32-bit、64-bit、ARM64 或 embeddable package。
- 离开第一个发布页前，使用 read 读取包含发布日期和文件表格的正文，令证据保留在工具结果中；只看一眼页面然后返回，会丢失上一页的观察内容。
- 如果页面存在 main 区域，可用 read 读取该区域的文字；区域没有无障碍名称时，name 使用空字符串。否则根据当前文字快照选择实际存在的正文区域或表格。
- 只需读取文字，不要点击安装包链接。短暂加载可使用 wait；当前文字足够时不必额外滚动。
- 查不到版本、缺少目标安装包或网络不可用时，如实说明，不能编造文件信息。未取得两个版本的所需信息时以 blocked 结束。

## 完成时的输出

finish 的 message 使用中文，逐项列出：

1. 两个确切版本号及各自的官方发布页 URL。
2. 各自的发布日期。
3. 目标安装包名称、操作系统、文件大小，以及该行有无 Recommended 标记。
4. 哪个版本发布日期更晚、哪个安装包更大；文件大小保留网页单位，不把发布日期更晚解释为更适合安装。

所有事实来自本次实际访问的页面与 read 结果，不使用模型记忆补全。
