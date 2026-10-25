# 验证与修复闭环测评

日期：2026-10-25（Asia/Shanghai）。Windows / Microsoft Edge / Python 3.12；真实模型使用项目配置的 GLM-5.3-Flash。测试未提交、登录或操作用户的真实业务数据。

## 结果

| 验证范围 | 结果 | 证据 |
| --- | --- | --- |
| 17 组本地回归测试 | 全部通过 | `.cache/sandbox-regression/index.json` 和分项日志 |
| 真实录制 → 模型生成 → 修复 → 双模式执行 | 通过，修复 1 次 | `.cache/sandbox-live/latest.json` |
| 中文 Element Plus 远程下拉，脚本与 LLM | 两种模式通过 | `data/validations/20261025-022029-fb9f492b/report.json` |
| 创建、默认参数修改、聊天修改后自动验证 | 通过 | `tests/studio_validation.py` |
| 安装包构建 | 成功 | `.cache/sandbox-wheel/` |

17 组测试：generation、studio_editing、studio、studio_layout、approval、script_mode、llm_batches、stage_navigation、dynamic_page、browser_tools、file_paths、browser_lifecycle、browser_display、recording、smoke、sandbox、studio_validation。除下面两项真实模型测试外，模型响应使用测试替身，浏览器交互为真实 Edge。

## 真实录制与修复

本地中文测试页面包含关键词、分类下拉和延迟显示的搜索结果。实际录制填写“人工智能”、选择“教程”、点击搜索并等待完成，再使用模型生成流程。固定验收要求页面最终显示“查询完成：人工智能 / 教程”。

首次生成的流程将“查询完成”作为精确文字定位，实际页面还有关键词与分类，导致等待失败。修复模型使用现场可见且唯一的 status 角色替换错误定位。原目标、参数和验收条件未改变；修复后的同一版流程在脚本与 LLM 的两个独立会话中均通过。

生成用量 5,788 Token；验证与修复用量 11,914 Token（3 次请求），验证与修复耗时 30.8 秒。合计 17,702 Token。此例的本地网页服务只在测试期间存在，生成文件是测试产物，不是可长期访问的线上流程。

## 真实中文网站

使用 `element_cn_remote_select`，参数 query=al、choice=Alabama。脚本实际触发异步候选、选择完整名称，LLM 通过真实模型规划操作。两种模式都读取目标 option 的 `aria-selected` 属性，实际值为字符串 `true`。

验证用量 25,925 Token（4 次请求），耗时 35.73 秒，无需修复流程。

首次试验暴露了验收表达不足：模型把属性值当元素文字，并额外要求搜索框值等于选中项。该轮正确保留为失败，未标记通过。完善属性读取验收及提示后，重新发起独立验证，形成上面的通过报告；旧失败报告仍保留在本地。

## 边界

全部授权只用于后台验证，不改变普通执行的授权设置。模型 finish/succeeded 不能绕过固定条件；测试覆盖模型提前声称完成时仍判失败。文件测试使用人工样本，真实复制、选择和下载，达到重复预算时停止，未使用假上传结果或缓存冒充完整重放。

这些结果覆盖上述环境和参数，不能证明任意网站、任意参数或未来网页版本都可运行。自动制定的验收条件也可能遗漏业务要求；重要流程应提供明确 checks。原始日志、模型用量与页面观察保存在忽略版本控制的本地目录。
