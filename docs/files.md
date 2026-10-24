# Skill 文件参数与本地仓库

上传下载统一使用已有的 --param，不再提供专用的 --upload-dir、--upload-file、--download-dir、--download-name CLI 参数。

```text
data/profile/       # 原有浏览器会话，保持原位
files/uploads/      # 默认上传文件查找目录
files/downloads/    # 默认下载保存目录
```

files/ 是本地文件仓库，与 data/ 一样不提交 Git。不会扫描整个仓库或自动上传其中的文件；旧 data/downloads 不迁移。上传文件不复制、移动或删除，下载目录在使用时创建。

## Skill 声明

在 SKILL.md 的 YAML 中明确声明文件参数映射。值写参数名，不写 {{模板}} 或实际路径：

```yaml
name: upload_document
goal: 上传用户选择的文档
params: [file]
file_params:
  uploads: [file]
  upload_dir: source_dir
  download_dir: save_dir
  download_name: save_as
actions:
  - tool: upload
    args:
      target: {label: 附件}
      file_ids: [u1]
```

这是格式示例，实际 Skill 还应配置目标网页 start、准确控件定位和上传完成等待条件。

| file_params 字段 | 值的含义 | 参数未传入时 |
| --- | --- | --- |
| uploads | 上传文件参数名列表 | 不选择对应文件 |
| upload_dir | 上传查找目录的参数名 | files/uploads |
| download_dir | 下载目录的参数名 | files/downloads |
| download_name | 下载名称的参数名 | 工具 filename 或网站建议名称 |

params 列表仍表示必填参数：上例 file 必填，source_dir、save_dir、save_as 可选。只需下载的 Skill 可只声明 download_dir 和 download_name，不声明 uploads。普通参数如 topic 不参与文件配置；没有 file_params 时上传清单为空，下载使用默认目录。

## 用户命令

在对应 Skill 命令后添加需要的 --param：

```powershell
# 选择 files/uploads/报告.pdf（参数片段）
--param "file=报告.pdf"

# 使用其他目录并自定义下载位置和名称
--param "file=报告.pdf" --param "source_dir=D:/资料" --param "save_dir=D:/下载结果" --param "save_as=月度报告.csv"
```

参数名由 Skill 的映射决定，不是全局保留字。目录相对路径以当前工作目录为基准，上传文件相对路径以 source_dir 对应目录为基准，也可指定绝对路径。文件不存在、不是文件或传入空值时，在浏览器启动前报错。提供参数本身不会触发上传/下载，仍需任务调用相应工具。

多个文件使用多个具名参数，如 params: [document, attachment] 和 uploads: [document, attachment]，然后传入 --param document=报告.pdf --param attachment=附件.xlsx；不使用重复同名参数拼成列表。文件按 uploads 列表中实际传入的顺序分配 u1、u2，重复文件去重；可选文件省略后编号可能变化，LLM 应以观察中的 upload_files 为准。固定脚本需要稳定编号时将对应参数列为必填。

## 工具与授权

upload 使用 file_ids: [u1]，模型观察 upload_files 列出本次已选文件编号和名称。原 paths 参数兼容，但必须匹配已选文件，不能与 file_ids 同时使用。即使 --approval allow 也不能上传未选文件。

download 使用 target 和可选 filename；下载命名优先级：Skill 文件参数指定的名称 > 工具 filename > 网站建议名称。文件名不得包含目录、Windows 保留字符或设备名。同名下载自动加 -1、-2 等编号，不覆盖；多文件任务通常省略统一下载名称。

上传下载继续受授权策略控制。提示包含实际上传路径或下载目录；网站建议名称可能在点击前未知。文件选择结果和下载保存路径写入 stderr，不影响 --json 的 stdout。上传成功只表示设置了网页文件控件，服务器是否接收需等待页面结果。

## 工具库

CLI 在启动时调用 FileOptions.from_skill(skill) 解析配置，之后模型不能改变该文件清单。独立库使用者仍可直接构造 FileOptions(upload_files=[...], download_dir=...) 并传入 BrowserTools(page, file_options=options)。不传配置时使用默认目录和空上传清单。
