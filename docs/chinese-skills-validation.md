# 中文网站 Skill 与真实验证

本次新增四个 Skill，全部使用实际公开中文网站，不使用本地模拟网页冒充线上结果。验证使用项目 Runtime、真实 Playwright Edge、真实 .env 模型，以及 allow 授权；下载检查是测试端独立核验，不是产品新增业务检查模块。原有中文百科 Skill 保留，本轮矩阵仅覆盖下面四个新增任务。

## 覆盖范围

| Skill | 网站 | 主要覆盖 |
| --- | --- | --- |
| vue_cn_navigation | [Vue 中文文档](https://cn.vuejs.org/guide/introduction.html) | 首次提示遮挡、响应式计数、标题定位、SPA URL 变化、两次返回 |
| element_cn_remote_select | [Element Plus 中文选择器文档](https://element-plus.org/zh-CN/component/select.html#远程搜索) | 自定义下拉、模拟异步加载、变化的容器文字、随机 ID 避让、精确选项匹配、读取选中状态 |
| chinese_image_file_pipeline | [中文图片压缩工具](https://www.onlineimagecompression.org/zh/) | 隐藏文件输入框、三次文件选择、单文件与双文件处理、等待完成、四份实际下载及同名避让 |
| bejson_timestamp_precision | [BeJSON 中文时间转换](https://www.bejson.com/convert/unix/) | 单选框、动态毫秒字段、连续七字段填写、输入值读取、双向转换结果等待 |

边界：下拉站点是公开文档中的模拟远程搜索，并非真实后端搜索请求。图片站自述浏览器本地处理；本轮验证文件选择、处理状态和下载，不包含服务器接收上传或服务端处理完成验证。测试图片不包含用户数据，没有把图片送给视觉模型。没有覆盖登录、验证码、付款或原生系统文件对话框。

## 手动运行

在项目根目录执行。以下命令为无 LLM 模式；末尾添加 --llm 即启用真实模型。默认显示并保留浏览器；测试完在终端按回车关闭。

```powershell
.\.venv\Scripts\python -m browser_skill_agent skills/vue_cn_navigation/SKILL.md --approval allow

.\.venv\Scripts\python -m browser_skill_agent skills/element_cn_remote_select/SKILL.md --param query=al --param choice=Alabama --approval allow

.\.venv\Scripts\python examples/prepare_sample_files.py
.\.venv\Scripts\python -m browser_skill_agent skills/chinese_image_file_pipeline/SKILL.md --param file_a=sample-a.png --param file_b=sample-b.png --param save_dir=files/downloads/image-demo --approval allow

.\.venv\Scripts\python -m browser_skill_agent skills/bejson_timestamp_precision/SKILL.md --approval allow
```

文件 Skill 参数 file_a/file_b 为不带目录的两个不同 PNG 文件名；可用 source_dir 改上传查找目录，用 save_dir 改下载目录。样本生成器保留已有文件，不覆盖；在线验证入口会检查样本哈希，避免同名用户文件被误用于测试。北京时间转换场景要求与本次测试一致的 Asia/Shanghai 时区，不满足期待值时应停止，而不是随意修改结果。

## 自动复测

```powershell
.\.venv\Scripts\python tests/live_chinese_skills.py --skill vue_cn_navigation --mode script
.\.venv\Scripts\python tests/live_chinese_skills.py --skill vue_cn_navigation --mode llm
```

--skill 可换为上表任一名称。该入口固定无界面、allow 授权、30 步预算，使用独立浏览器上下文；LLM 模式使用现有模型配置、120 秒 HTTP 超时，会消耗真实 Token，没有偷偷换成预设模型响应。

每次运行在 .cache/live-validation/<任务-模式-时间>/ 写入 report.json、trace.json 和 progress.log；下载保存在 files/downloads/validation/<任务-模式-时间>/。两者不提交 Git。退出码 0 要求 Runtime 报告成功且独立核验通过；单凭模型 finish 不足以通过。

核验内容包括：实际读取计数按钮与目标文章、两次 back 和最终 URL；目标 option 的 aria-selected；四个下载的 PNG 文件头、尺寸、数量和对应顺序；三项转换输入框的精确值。

## 发现并修复的问题

- Vue 首次访问提示会遮挡侧边栏，Skill 先关闭提示并收起偏好面板，未使用强制点击绕过遮挡。
- 远程下拉真实选项名为 label:Alabama，必须与 label:Alaska 等完整区分；填入关键词后容器文字改变，后续改为定位实际 option。
- 图片页每次文件选择替换列表，不追加；先完成当前下载，再重置并处理下一批。
- 图片页“批量下载”实测不是 ZIP，而是逐项触发多个下载事件。初版只捕获第一个事件并命名为 ZIP，独立文件检查发现错误；最终改为读取结果顺序、核对两个按钮数量后逐一 download，保存四份真实 PNG。该失败记录保留。
- 下拉首轮真实模型请求超过 120 秒；已保留失败记录，重新运行后成功。这是单次验证，不是长期稳定性或固定耗时保证。

## 本次实测结果

2026-10-24 实测，授权全部为 `allow`。表中步数为预算计数（LLM 包含 finish），时间包含页面、模型及核验耗时；无 LLM 模式未请求模型。

| Skill | 非 LLM | LLM | 模型调用 | LLM Token（输入 / 输出） |
| --- | --- | --- | --- | --- |
| vue_cn_navigation | 通过，13 步 / 12.5 秒 | 通过，13 步 / 151.4 秒 | 6 | 46,573 / 9,646 |
| element_cn_remote_select | 通过，5 步 / 32.8 秒 | 重测通过，6 步 / 184.4 秒 | 3 | 22,134 / 10,715 |
| chinese_image_file_pipeline | 通过，16 步 / 20.6 秒 | 通过，18 步 / 303.8 秒 | 6 | 35,663 / 18,910 |
| bejson_timestamp_precision | 通过，17 步 / 8.9 秒 | 执行成功，原始记录复核通过，22 步 / 251.3 秒 | 6 | 61,338 / 16,518 |

时间戳最初独立核验误要求结束时毫秒输入框仍可见。实际模型完成转换后再次切回秒级复读，三项正确结果均在真实 read 记录中。核验已改为要求字段在操作时出现且成功填入 123，并核对三项结果；对该次原始 trace 复核通过，未重新调用模型。原失败 report.json 原样保留，复核结论写在同目录 reverification.json。模型此处有四步重复操作，仍有优化空间。

上述四次 LLM 执行已报告合计 221,497 Token。此前下拉超时请求未返回 usage，实际总用量不能据此完整计算。

通过的记录目录（均位于 `.cache/live-validation/`）：

- `vue_cn_navigation-script-20261024-133120`、`vue_cn_navigation-llm-20261024-133248`
- `element_cn_remote_select-script-20261024-132937`、`element_cn_remote_select-llm-20261024-133549`
- `chinese_image_file_pipeline-script-20261024-133135`、`chinese_image_file_pipeline-llm-20261024-133258`
- `bejson_timestamp_precision-script-20261024-133536`、`bejson_timestamp_precision-llm-20261024-133613`（见 reverification.json）

首次 Vue 遮挡、图片错误 ZIP、下拉模型超时记录也保留在同一父目录。测试结果说明本次可执行，不保证网站今后不改版或网络不超时。


## 第二轮：五种组件交互

新增五个 Skill，继续使用 Element Plus 中文官方文档实际演示。它们补充组件状态测试，不代表又覆盖了五个独立网站，也不代表验证了后端业务数据。演示控件部分为英文，Skill、提示及总结为中文。

| Skill | 流程和独立核验 |
| --- | --- |
| element_cn_tabs | Config → Task → User，读取三个面板文字及选中属性，最终 DOM 必须停留 User |
| element_cn_collapse | 打开 Feedback 和 Efficiency，读取内容后关闭 Feedback；核验两个按钮最终展开状态 |
| element_cn_dialog | 打开 Tips → Cancel → 再打开 → Confirm；每次读取消息、等待关闭、读取可见数量 0 |
| element_cn_tree | 展开一级与二级节点读取叶子 → 折叠 → 恢复；核验两次叶子读取、隐藏数量及最终可见性 |
| element_cn_pagination | 第 3 页 → 下一页 4 → 上一页 3 → 第 1 页；依序核验 aria-current 和上一页禁用边界 |

文档重复展示多个相同组件，因此明确使用第一个基础示例（nth:0），树节点另限定在第一个 tree 内。测试端直接限定第一个 `.example-showcase` 检查最终状态，以防误操作其他演示。没有使用随机 el-id，也没有强制点击。

在项目根目录运行以下任意名称；不需要参数或文件：

```powershell
.\.venv\Scripts\python -m browser_skill_agent skills/element_cn_tabs/SKILL.md --approval allow
.\.venv\Scripts\python -m browser_skill_agent skills/element_cn_tabs/SKILL.md --approval allow --llm
```

将 `element_cn_tabs` 替换为表中其他名称即可。显式自动验证使用：

```powershell
.\.venv\Scripts\python tests/live_chinese_skills.py --skill element_cn_tabs --mode script
.\.venv\Scripts\python tests/live_chinese_skills.py --skill element_cn_tabs --mode llm
```

本轮修复：弹窗触发按钮实际有三个同名副本，补上第一个示例定位；read 原白名单不支持分页 `aria-current`，补充 `aria-current`、`aria-disabled`、`disabled` 三种只读属性，并运行浏览器工具回归测试通过。首次失败记录保留，未改成无条件通过。

2026-10-24 实测，全部使用 allow 授权、真实 Edge 与现有模型。以下为最终版本最近一次通过的结果，LLM 步数包含 finish。

| Skill | 非 LLM | LLM | 模型调用 | LLM Token |
| --- | --- | --- | --- | --- |
| element_cn_tabs | 通过，9 步 / 25.0 秒 | 通过，10 步 / 111.8 秒 | 7 | 61,861 |
| element_cn_collapse | 通过，7 步 / 25.5 秒 | 通过，8 步 / 64.6 秒 | 5 | 42,373 |
| element_cn_dialog | 通过，8 步 / 13.1 秒 | 通过，9 步 / 86.9 秒 | 5 | 44,573 |
| element_cn_tree | 通过，7 步 / 15.9 秒 | 通过，8 步 / 64.5 秒 | 4 | 35,924 |
| element_cn_pagination | 通过，9 步 / 12.5 秒 | 通过，10 步 / 138.0 秒 | 6 | 56,458 |

最终五次通过的 LLM 测试合计 **241,189 Token**；含修正前弹窗恢复测试，已知合计 **309,103 Token**。分页超时请求未返回 usage，不包含在已知统计中。非 LLM 测试未请求模型。

原始报告位于 `.cache/live-validation/`，对应目录：

- `element_cn_tabs-script-20261024-144949`
- `element_cn_tabs-llm-20261024-145035`
- `element_cn_collapse-script-20261024-144949`
- `element_cn_collapse-llm-20261024-145035`
- `element_cn_dialog-script-20261024-145211`
- `element_cn_dialog-llm-20261024-145455`
- `element_cn_tree-script-20261024-145015`
- `element_cn_tree-llm-20261024-145229`
- `element_cn_pagination-script-20261024-145225`
- `element_cn_pagination-llm-20261024-145606`

弹窗修正前的 LLM 运行也保留：首次点击因三个同名按钮失败，模型调用 locate 后改用明确的 nth:0，完成取消和确认两条路径。另对最终已修正 Skill 重新实测成功。分页首次 LLM 请求发生 ReadTimeout（120 秒），尚未执行动作，未返回 usage；该请求不能按零 Token 计费。

本轮仍使用原有“read 后交回模型”规则，因此同一阶段有多个 read 时会增加模型调用，阶段规划不是一次把所有步骤执行到底。
