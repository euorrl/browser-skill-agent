# 流程登录与人工接管

仅需要登录的流程生成登录参数。录制出现账号密码表单时，模型可添加账号、密码参数及 login 配置；只出现扫码或验证码时保留人工登录节点，不强行增加密码参数。录制已遮蔽密码，生成后需要重新填写。

## 工作台

账号为普通参数，可保存默认值；密码使用密码输入框，仅保留在本次工作台进程内存，不写入 Skill、example_params.json、索引、日志或模型上下文。关闭工作台后重新填写；留空沿用本次已填密码。请通过参数框填写密码，不要发送到聊天框。

创建流程后如缺少密码，自动验证显示“等待补充登录参数”，不请求模型或判定流程执行失败。在编辑面板补齐密码并保存即可启动验证。

运行面板新增“后台运行，遇到人工登录时显示浏览器”。后台验证也支持接管：显示同一个浏览器，人工完成后点击“登录完成，继续”，检查成功条件后再隐藏。实现使用可最小化的有窗口 Edge，不通过重启浏览器转换 headless 模式。

## 行为与边界

工具执行前后、模型观察前检查登录需要，支持中途跳转或弹层。账号密码自动填写必须具备明确的来源、唯一定位器及成功条件，各控件所属页面/框架的来源都必须匹配。每个来源每次执行最多自动提交一次；失败、验证码、缺少凭据或不可靠定位转人工。

人工登录完成后不重放上一笔点击、上传或提交，只重新检查 wait_after；原操作本身失败时仍停止，不猜测它已经完成。停止任务或关闭工作台会解除等待。

优先使用流程的 detect，另有常见密码/验证码框、登录页的识别。不是所有二维码、自定义组件或跨窗口 SSO 都能自动识别；复杂场景需要录制提供明确登录节点与成功条件。无明确成功条件时只检查用户确认及登录界面消失。

## Skill 格式

```yaml
params: [username, password]
login:
  origins: [https://example.com]
  username_param: username
  password_param: password
  username_target: {label: 账号}
  password_target: {label: 密码}
  submit_target: {role: button, name: 登录}
  detect: {label: 密码}
  success:
    target: {text: 我的工作台}
    state: visible
actions:
  - tool: login
    args: {}
```

密码不允许出现在普通 fill、value_ref、文件参数或模板里。login 工具不接受凭据，运行时直接使用用户填写的值。密码参数示例必须为空。

## CLI

```powershell
.\.venv\Scripts\python -m browser_skill_agent skills/<流程>/SKILL.md --param username=你的账号
```

缺少密码时通过终端隐藏输入读取，不要将密码写入 shell 命令。`--headless` 兼容参数现在表示可接管的后台运行：需要人工登录时显示，完成后隐藏，任务结束关闭。`--result-only` 仍在结束时显示并保留。非交互终端遇到人工登录会停止。

## 本地测试

- `tests/login.py`：中途账号密码登录、MFA 窗口恢复、来源限制、失败不重试、模型及存储无密码。
- `tests/studio_login.py`：密码框、缺密码等待、后台真实登录、人工确认界面。
- `tests/login_validation.py`：脚本与 LLM 独立验证会话登录，报告及候选文件不含密码。

测试使用本地网站和测试凭据，模型响应使用替身，不使用真实用户账号。
