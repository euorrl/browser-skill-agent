# 阶段连续执行评测

评测日期：2026-10-24（Asia/Shanghai）。本报告对应取消“每次读取自动中断”的修正，以下结果来自本轮实际执行记录。

## 本次修正

- read / snapshot / locate 默认继续当前阶段，阶段计划执行结束后统一交回模型。
- 动作顶层可选 `observe_after: true`，需要新读取结果才能决定下一步时显式暂停；该标记必须是布尔值。
- 授权拒绝直接结束任务；关键授权操作、操作或等待失败、未验证的导航、意外标签页仍提前中断。
- 未执行的尾部动作不会自动重放，下一次规划可查看 last_stage；成功读取仍保留在有界 evidence 中。
- 更新 Skill 的阶段说明，文件顺序读取仍要求显式观察后再决定下载目标，没有引入业务检查模块或视觉模型。

## 方法与口径

全部 10 个 Skill 分别运行 script 和 llm；修正后的评测配置为真实 Microsoft Edge、真实公开网站、独立 Context、无界面、30 步预算、allow 授权。模型为 glm-5.3-flash。真实模型读取现有 .env 配置，API 密钥不会写入报告。每种模式最多两个任务并行；个别修正重测与主矩阵并行，耗时受网络、并发和模型服务影响。

每项通过需 Runtime 报告 succeeded，并通过测试端对页面、读取记录或下载内容的独立核验，不能仅凭模型 finish。无 LLM 不请求模型。LLM 操作预算包括 finish 和无效计划；报告的模型调用数与网页操作步数分开。测试不验证摘要全部事实正确，也不代表任意网站可运行。

历史对比使用上一轮对应 Skill 最后一次完成的真实记录，包括时间戳的已保留复核结论。它是历史单次测量，不是同一时刻的随机对照实验。中文百科没有对应的上一轮结构化报告，不纳入历史对比；本轮失败的文件 LLM 也不纳入两轮成功场景的性能汇总。因此性能对比只含八项，而全量结果始终包含十项。模型调用和 Token 变化可作为优化线索，耗时变化不能全部归因于代码。

## 本地回归

阶段批次、预期导航、授权策略、模型适配冒烟和默认脚本模式测试通过。包括同阶段 read/snapshot/locate 多份证据、读取失败中止、显式观察丢弃尾部、非法 observe_after 类型、预算限制、证据保留、意外弹窗及授权拒绝无副作用。

## 评测入口发现的问题

1. 中文百科首次脚本和同时启动的 LLM 使用了 Playwright 便捷单页上下文，tabs new 报 Please use browser.new_context()。已改为显式 browser.new_context() 后创建页面。产品 CLI 原有会话方式不受影响。
2. 百科脚本完成后，标题容器会动态加入“编辑”文字，原核验误把它当作条目标题。实际 DOM 显示标题位于 .mw-page-title-main，核验已限定此节点；原报告保留，重新运行验证。
3. 百科首次 LLM 把 DOM id 写成 test_id，并尝试点击全页重名链接。Skill 已补充实际 JSON 定位格式，明确 id 与 test_id 的区别、结果容器与完整标题匹配。旧 LLM 随后改用同页和 main 读取，未满足评测规定的正文容器与双标签页流程；下面原始断言按日志保留，不应据此理解为它从未读过任何条目内容。

4. 文件流水线的 17 个实际工具步骤已完成，包括三个文件选择批次和四次下载，但第 5 次模型调用（最终总结）ReadTimeout。单独核验四份 PNG 文件头、尺寸及顺序通过，保存在 artifact-verification.json；这不改变整轮失败结论。未为取得成功结果自动重跑上传下载，超时请求用量未知。

## 运行与证据

```powershell
.\.venv\Scripts\python examples/prepare_sample_files.py
.\.venv\Scripts\python tests/evaluate_skills.py
```

本次原始文件保存在 `.cache/stage-evaluation-20261024/`：每次运行独立目录含 report.json、trace.json、stages.json、progress.log。index.json 是最初矩阵运行记录；后续重测另存，本文和 JSON 汇总已包含所有尝试，不覆盖首次失败。报告保存 Runtime 和 Skill 文件 SHA-256、模型名称、实际 usage、模型请求耗时；stages.json 记录模型计划和上个阶段的执行情况，不保存密钥或完整请求上下文。

## 结果

最终结果 **19/20** 通过；最初矩阵 **17/20** 通过（含评测入口问题），不能据重测结果声称首次全部成功。共保存 25 次运行记录。

| Skill | 无 LLM：步数 / 秒 | LLM：预算步数 / 秒 | LLM 调用 | Token |
| --- | --- | --- | --- | --- |
| chinese_encyclopedia_research | 通过，22 / 18.4 | 通过，15 / 133.2 | 6 | 82,503 |
| element_cn_tabs | 通过，9 / 9.1 | 通过，10 / 43.0 | 4 | 34,201 |
| element_cn_collapse | 通过，7 / 6.3 | 通过，8 / 60.5 | 3 | 25,922 |
| element_cn_dialog | 通过，8 / 6.9 | 通过，9 / 43.8 | 3 | 25,935 |
| element_cn_tree | 通过，7 / 7.8 | 通过，8 / 77.2 | 3 | 29,423 |
| element_cn_pagination | 通过，9 / 5.8 | 通过，10 / 51.3 | 3 | 26,760 |
| vue_cn_navigation | 通过，13 / 8.3 | 通过，13 / 103.4 | 4 | 38,622 |
| bejson_timestamp_precision | 通过，17 / 7.8 | 通过，18 / 163.7 | 4 | 58,726 |
| element_cn_remote_select | 通过，5 / 9.2 | 通过，6 / 205.1 | 3 | 35,383 |
| chinese_image_file_pipeline | 通过，16 / 7.9 | 失败，17 / 344.3 | 5 | 41,532 |

失败的文件任务没有收到 finish；该行的 17 步由工具 trace 计数，5 次调用包含最终超时请求，41,532 Token 只覆盖已返回 usage 的四次请求。

十项各自最后一次 LLM 运行（含失败）合计 399,007 Token；所有尝试已知合计 516,948 Token，另有 1 次请求未返回完整 usage。无 LLM 的请求数及 Token 为 0。未估算费用。

### 与历史成功记录比较（仅两轮都通过的对应场景）

| Skill | 模型调用：前 → 后 | Token：前 → 后 | 耗时秒：前 → 后 |
| --- | --- | --- | --- |
| element_cn_tabs | 7 → 4 | 61,861 → 34,201 | 111.8 → 43.0 |
| element_cn_collapse | 5 → 3 | 42,373 → 25,922 | 64.6 → 60.5 |
| element_cn_dialog | 5 → 3 | 44,573 → 25,935 | 86.9 → 43.8 |
| element_cn_tree | 4 → 3 | 35,924 → 29,423 | 64.5 → 77.2 |
| element_cn_pagination | 6 → 3 | 56,458 → 26,760 | 138.0 → 51.3 |
| vue_cn_navigation | 6 → 4 | 56,219 → 38,622 | 151.4 → 103.4 |
| bejson_timestamp_precision | 6 → 4 | 77,856 → 58,726 | 251.3 → 163.7 |
| element_cn_remote_select | 3 → 3 | 32,849 → 35,383 | 184.4 → 205.1 |

模型调用：42 → 27，减少 35.7%。

Token：408,113 → 274,972，减少 32.6%。

累计任务耗时（不等于并行总墙钟时间）：1,052.9 → 748.0，减少 29.0%。

### 阶段连续执行证据

- element_cn_tabs：3 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- element_cn_collapse：1 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- element_cn_dialog：2 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- element_cn_tree：1 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- element_cn_pagination：2 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- vue_cn_navigation：2 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- bejson_timestamp_precision：1 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- element_cn_remote_select：1 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。
- chinese_image_file_pipeline：1 个含多次读取的阶段完整执行，下一次模型调用收到 executed=计划长度、skipped=0。

### 失败与重测记录

- `chinese_encyclopedia_research-script-20261024-162705`：运行未成功结束；耗时 12.1 秒，已报告 0 Token。
- `chinese_encyclopedia_research-script-20261024-162846`：AssertionError: 缺少 人工智能 对应条目标签页；耗时 12.4 秒，已报告 0 Token。
- `chinese_encyclopedia_research-script-20261024-163012`：AssertionError: 缺少 人工智能 对应条目标签页：[{'url': 'https://zh.wikipedia.org/wiki/%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD', 'title': '人工智能编辑'}, {'url': 'https://zh.wikipedia.org/wiki/%E6%9C%BA%E5%99%A8%E5%AD%A6%E4%B9%A0?wprov=srpw1_0', 'title': '机器学习'}]；耗时 10.1 秒，已报告 0 Token。
- `chinese_encyclopedia_research-llm-20261024-162750`：AssertionError: 缺少 人工智能 实际条目正文读取，搜索摘要不能替代；耗时 461.2 秒，已报告 117,941 Token。
- `chinese_image_file_pipeline-llm-20261024-163658`：ReadTimeout: The read operation timed out；耗时 344.3 秒，已报告 41,532 Token。
- `element_cn_remote_select` 最终 llm 运行中还有 1 次工具或等待失败后恢复；不能将最终通过解读为全程无错误。详情见 trace.json。

### 最终报告目录

均位于 `.cache/stage-evaluation-20261024/`：

- `chinese_encyclopedia_research-script-20261024-163632`
- `chinese_encyclopedia_research-llm-20261024-163321`
- `element_cn_tabs-script-20261024-162705`
- `element_cn_tabs-llm-20261024-162750`
- `element_cn_collapse-script-20261024-162715`
- `element_cn_collapse-llm-20261024-162833`
- `element_cn_dialog-script-20261024-162717`
- `element_cn_dialog-llm-20261024-162934`
- `element_cn_tree-script-20261024-162722`
- `element_cn_tree-llm-20261024-163019`
- `element_cn_pagination-script-20261024-162725`
- `element_cn_pagination-llm-20261024-163137`
- `vue_cn_navigation-script-20261024-162731`
- `vue_cn_navigation-llm-20261024-163228`
- `bejson_timestamp_precision-script-20261024-162732`
- `bejson_timestamp_precision-llm-20261024-163412`
- `element_cn_remote_select-script-20261024-162740`
- `element_cn_remote_select-llm-20261024-163532`
- `chinese_image_file_pipeline-script-20261024-162740`
- `chinese_image_file_pipeline-llm-20261024-163658`

可机读汇总：[stage-evaluation-results.json](stage-evaluation-results.json)。本报告的独立核验只用于评测，不是产品新增业务检查模块。图片站验证文件选择、本地处理和四份 PNG 下载，不验证服务端接收；下拉演示的异步搜索是模拟延迟。
