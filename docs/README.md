# 文档索引

安装与启动见 [项目 README](../README.md)。以下文档描述当前实现；历史验证记录只适用于记录中的版本、参数和网站状态。

## 使用指南

| 文档 | 内容 |
| --- | --- |
| [工作台](studio.md) | 流程管理、录制生成、对话修改、运行日志和单次定时 |
| [命令行](cli.md) | 运行参数、模型配置、输出字段和故障排查 |
| [操作录制](recording.md) | 录制控制、记录格式与覆盖范围 |
| [流程生成](generation.md) | 参数提取、草稿格式、证据缺口与失败诊断 |
| [验证与修复](sandbox.md) | 固定验收、脚本试运行、修复限制和报告 |
| [操作授权](authorization.md) | 人工、AI 与全部允许三种模式 |
| [登录接管](login.md) | 账号密码、人工登录与会话内凭据 |
| [文件管理](files.md) | 上传范围、下载路径与同名文件处理 |

## 开发参考

- [架构与模型交互](architecture.md)
- [Skill 格式](skills.md)
- [浏览器工具](tools.md)
- [开发、测试与提交](development.md)

## 验证记录

这些文档保留测试当时的流程和结果，可能引用已从工作台删除的示例，不应作为当前安装或运行步骤。

- [中文网站测试](chinese-skills-validation.md)
- [阶段执行评测](stage-evaluation.md)及[数据](stage-evaluation-results.json)
- [验证修复测试](sandbox-validation.md)
- [巨潮公告生成修复记录](cninfo-generation-fix.md)

B 站分享示例的手工修正说明位于其 [Skill 文件](../skills/bilibili_search_copy_share_link-608c4127/SKILL.md)。该示例不代表录制生成器已自动生成同等可执行流程。
