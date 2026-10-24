# 浏览器工具库

源码位于 `src/browser_skill_agent/tools/`，对外仍使用 `BrowserTools`。每次通过 `execute(工具名, 参数字典)` 调用，返回 `ok`、`data` 或 `error`。`ok` 表示工具完成，不代表业务目标成功。

## 工具清单

| 类别 | 工具 | 用途 |
| --- | --- | --- |
| 导航 | `goto`、`back`、`reload` | 打开、返回、刷新 |
| 点击 | `click`、`double_click`、`hover` | 点击、双击、悬停 |
| 输入 | `fill`、`type_text`、`press` | 替换内容、逐键追加、按键 |
| 表单 | `select`、`set_checked` | 原生下拉、多选、勾选状态 |
| 定位与滚动 | `scroll`、`drag` | 滚动到元素、页面滚动、元素拖放 |
| 观察 | `read`、`snapshot`、`locate` | 精确值、属性、选项、局部文字快照和候选元素 |
| 动态页面 | `wait`、`wait_for` | 定时等待、条件等待 |
| 标签页 | `tabs` | 列表、新建、切换、关闭 |
| 弹窗 | `dialog` | 预设下一次 alert/confirm/prompt 的处理方式 |
| 文件 | `upload`、`download` | 文件输入控件上传、下载保存 |

另有 `observe()` 仅在 LLM 模式下由 Runtime 每轮自动调用；脚本模式不会自动观察。它返回当前 URL、页面文字、标签页列表、框架列表和最近的原生弹窗记录。

## 目标定位

```json
{"role": "button", "name": "加入购物车"}
```

还可使用 `label`、`placeholder`、`text` 或实际观察到的 `test_id`。默认精确匹配；可用 `exact: false`、`has_text` 或 `nth` 缩小范围。`nth` 从 0 开始，不应猜测元素顺序。

动态列表不建议使用固定 `nth`。通过 `locate(target=...)` 获取当前真实候选的文字、标签、可见性、ID 和测试标识；仅当前唯一的 ID/测试标识会作为 `suggested_target` 返回。可以直接使用返回的 `{"id":"..."}` 或 `{"test_id":"..."}`，没有稳定标识时应结合容器缩小范围。候选信息是当次读取的结果，不是永久有效的元素引用。

`visible: true` 可排除隐藏副本。点击、双击、填写、逐键输入、按键、下拉选择和勾选动作默认匹配可见目标，等待唯一性、启用状态和目标所在区域的 `aria-busy` 结束；不会自动改为第一个匹配项。每次动作重新解析定位器，正常 DOM 重绘后可找到新的对应节点。遮挡、动画和事件可达性继续由 Playwright 的动作自动等待处理，不强制点击。

重名按钮优先限定容器：

```json
{"role":"button","name":"加入","within":{"role":"article","name":"商品乙"}}
```

iframe 内目标附加 `frame: "f2"`。编号来自当前观察，不写死在 Skill 中。先用 `snapshot(frame="f2")` 读取框架内容。标签页编号同理，模型使用 `tabs(action="switch", page_id="p2")` 切换，网页自行打开的新标签页不会自动切换；工具 `tabs(action="new")` 会主动切换到新建页。

## 下拉与动态筛选

原生 `<select>` 使用 `select(target=..., label="价格升序")` 或 `value="asc"`。参数可传列表以选择多个原生选项。先用 `read(kind="options")` 获取实际标签和值。

自定义下拉（例如可搜索的组合框、弹出列表）使用多个有观察的动作：

1. `click` 展开组件。
2. 查看新快照，找到搜索框或选项。
3. `fill`/`type_text` 输入筛选词。
4. `wait_for` 等待实际选项出现。
5. `click` 选择选项，再观察结果。

工具不会猜测框架内部结构，也不会把一串网站专属操作封装成万能下拉函数。

`wait_for` 支持 `visible`、`hidden`、`attached`、`detached`、`enabled`，以及带 `value` 的 `text`、`value`、`count`。也可传 `url` 等待匹配地址。单次最多 30 秒；超时后返回错误，脚本模式停止，LLM 模式重新观察。等待是工具执行条件，不是独立业务检查模块。

## 避免动作过快

LLM 模式每轮观察前，最多等待 2 秒，寻找 DOM 连续 200 毫秒无相关变更且没有可见 `aria-busy=true` 的窗口。`readiness.settled=false` 表示没有在该窗口内稳定，应结合具体控件继续等待。它不会等待全站网络空闲，因此持续心跳或长连接不会无限阻塞；没有声明忙碌状态的延迟请求也可能尚未完成，所以短时稳定并不保证业务就绪。

已知动作预期结果时，可把等待条件附在动作上：

```json
{
  "tool": "click",
  "args": {
    "target": {"role": "button", "name": "搜索"},
    "wait_after": {
      "target": {"role": "status"},
      "state": "text",
      "value": "搜索完成",
      "timeout": 15
    }
  }
}
```

条件必须能区分新旧结果，不应只等待操作前已存在的通用标题。这个等待仍属于同一工具调用，不额外占一个决策轮次。若动作执行后等待超时，返回 `ok=true`、`after_wait.ok=false` 和错误说明，不会重复点击；脚本模式停止后续步骤，LLM 模式下一轮重新观察。不能确认条件时先观察，再显式 `wait_for`。观察过程中发生 URL 跳转会重读一次，持续跳转时返回未就绪，而不混合不同页面的地址和正文。

## 文件与弹窗

`upload` 只设置用户指定路径的文件输入控件，不操作系统文件选择窗口。`download` 在点击前注册下载事件，保存到当前工作目录下的 `files/downloads`，同名文件自动加编号。上传选择成功、下载保存成功不等于服务器业务成功。

原生弹窗默认自动取消，防止阻塞动作。若任务明确需要接受，先调用 `dialog(action="accept", text="可选文本")`，再执行触发弹窗的点击；处理一次后恢复默认取消。HTML 弹层按普通页面元素操作。

## HTTPS 证书错误

启动参数 `--ignore-https-errors` 仅对本次浏览器上下文生效。默认校验证书；开关启用后可访问自签名、过期等证书异常的页面，但无法据证书确认网站身份，应仅对信任的网站使用。它不关闭模型 API 的 TLS 校验，不修改系统设置，也不解决验证码或访问权限。

## 范围

这是通用基础工具库，不承诺覆盖所有自定义组件。虚拟列表、画布、图像控件及复杂拖拽仍受网页实现限制。没有截图功能、任意脚本执行工具、独立 checker 或网站专属分支。

## 等待异步响应

工具参数可增加 `wait_response`（响应 URL 匹配模式）。执行器在操作前监听，最多等待 30 秒收到匹配响应，读取响应体后再执行 `wait_after`。适用于搜索、分类和排序异步请求；条件应匹配该动作的新请求，不能使用过于宽泛的模式。请求返回错误状态或响应等待失败时保留动作已执行的信息，禁止直接重放提交。无 LLM 的默认模式会停止后续步骤；`--llm` 模式交回模型观察。

正文读取可提供 `max_chars`，例如 `read` 的 `args` 中设置 `max_chars: 600`，只返回开头 600 字符。默认和上限仍为 16000；这是原文摘录，不是模型总结。

文件工具现在支持 upload 的 file_ids 参数（如 u1），原 paths 参数也必须匹配本次 Skill 文件参数选择。--approval allow 不解除文件限制。默认下载目录为 files/downloads，可通过 Skill 的 file_params 映射指定目录和名称，详见 [文件管理](files.md)。

## 读取组件状态

使用 `read(kind="attribute", attribute="aria-current")` 读取分页当前页标记；`aria-expanded` 表示展开，`aria-selected` 表示选中。禁用属性支持 `aria-disabled` 和 `disabled`：后者返回空字符串表示 HTML 布尔属性存在，返回 null 表示不存在，不能用字符串真假值判断。也可用 `read(kind="state")` 读取 enabled。
