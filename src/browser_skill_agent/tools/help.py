"""提供给模型的中文工具使用说明。"""

TOOL_HELP = """
工具及参数：
所有工具 args 可附加 requires_approval:true，强制请求当前授权策略审核；false 不能绕过程序规则。
关键操作获准并执行后会结束当前批次重新观察；授权被拒绝时整个任务停止，不得尝试绕过。
goto {"url":"页面地址"}；back {}；reload {}。
click {"target":TARGET}；double_click {"target":TARGET}；hover {"target":TARGET}。
fill {"target":TARGET,"value":"内容"} 替换输入，空字符串清空。
type_text {"target":TARGET,"value":"内容"} 逐键追加，适用于键盘驱动的自动补全。
press {"target":TARGET,"key":"Enter"} 向目标发送按键。
select {"target":TARGET,"label":"显示名称"} 或 {"target":TARGET,"value":"实际值"}。
select 仅用于原生 select；多选时 label/value 可为列表。
自定义下拉/筛选：先 click 展开，重新观察，再填写搜索框或点击 option/checkbox。
不要给自定义组件调用 select；不使用一串未经观察的盲目点击。
set_checked {"target":TARGET,"checked":true} 设置复选框/单选框状态。
scroll {"dy":600} 向下滚动（负数向上）；或 {"target":TARGET} 将目标滚动到视口。
drag {"source":TARGET,"target":TARGET} 将源控件拖到目标。
read {"target":TARGET,"kind":"text","max_chars":600} 读取正文；max_chars 可选，默认及上限为 16000 字符。只需确认内容时读取短摘录。
kind 还支持 value（输入值）、checked、state、count、options（原生下拉选项）。
分页状态可读取 attribute:aria-current，禁用状态可读取 aria-disabled 或 disabled；disabled 返回空字符串表示属性存在，null 表示不存在。
读取链接用 {"target":TARGET,"kind":"attribute","attribute":"href"}。
snapshot {} 重新读当前页；{"target":TARGET} 读指定区域；{"frame":"f2"} 读 iframe。
snapshot 的 truncated=true 时应读取更小区域；滚动不会改变整页文字快照的截断位置。
locate {"target":TARGET,"limit":10} 查看真实候选的标签、文字、可见性和唯一定位建议。
可使用 locate 实际返回的 id 或 test_id，不得编造。列表序号可能随刷新变化。
wait {"seconds":1} 定时等待，最多 5 秒。
wait_for {"target":TARGET,"state":"visible","timeout":10} 等待真实状态，最多 30 秒。
state 可为 visible/hidden/attached/detached/enabled；text/value/count 还需要 value。
例如 {"target":{"role":"status"},"state":"text","value":"完成"}。
也可 wait_for {"url":"**/cart","timeout":10} 等待 URL。
动态筛选后先等待结果文字、值或数量变化；不以网络完全空闲作为页面就绪条件。
动作参数可附加 wait_after，例如 click {"target":{"role":"button","name":"搜索"},
"wait_after":{"target":{"role":"heading","name":"搜索结果"},"state":"visible"}}。
wait_after 使用 wait_for 的参数格式，等待失败不重做原动作。条件要能区分新旧结果，
不要仅等待一个操作前就已存在的通用标题。若条件未知，先观察再显式调用 wait_for。
tabs {"action":"list"}；{"action":"switch","page_id":"p2"}；
{"action":"new","url":"地址"}；{"action":"close","page_id":"p2"}。
网页自行打开的新标签页不会自动切换，使用观察中的 tabs 编号选择；tabs new 会切到新建页。
dialog {"action":"accept","text":"提示框输入"} 预先设置下一次原生弹窗处理；
默认 dismiss，接受一次后恢复默认。须在触发弹窗的动作之前设置。
upload {"target":TARGET,"file_ids":["u1"]}，目标为文件输入控件；只能选择观察中 upload_files 已列出的编号。
upload_files 为空时必须报告缺少用户选择的文件，不猜测本机路径，不自动扫描上传目录。
兼容 paths 参数，但路径也必须是本次 Skill 文件参数明确选择的文件；不能同时提供 paths 和 file_ids。
download {"target":TARGET,"filename":"可选文件名"} 点击并保存到用户配置的目录，默认 files/downloads，自动避开同名文件。
用户通过 Skill 文件参数指定的下载名优先于工具 filename，未指定时采用网站建议名称；模型不能修改下载目录。
只按任务要求上传或下载，文件保存成功不等于整个业务任务完成。

TARGET 的基本形式：
{"role":"button","name":"提交"}、{"label":"邮箱"}、{"placeholder":"搜索"}、
{"text":"页面可见文字"}、{"test_id":"实际观察到的测试标识"}。
role 不提供 name 时匹配该角色的所有元素；默认 exact=true。
可附加 exact:false、has_text:"包含文字" 或 nth:0（从 0 开始）。
可附加 visible:true 排除隐藏副本；变更动作默认只匹配可见目标且必须唯一。
重名元素优先限定容器：{"role":"button","name":"加入","within":{"role":"article","has_text":"商品名"}}。
容器可嵌套。iframe 内目标附加 frame:"观察中的框架编号"，不可猜测编号。
不要编造 CSS 或测试标识。观察与目标绑定当前标签页，切页后重新观察。
fill/select/type_text/wait_for 可以用 value_ref:"参数名" 替代 value，由程序绑定实际参数。
"""

TOOL_HELP += "\n工具 args 可选 wait_response：响应 URL 匹配模式。先监听再执行动作，等待该请求返回后再执行 wait_after；仅在已知真实接口时使用。不要猜测接口，超时不能直接重复提交。\n"

TOOL_HELP += "\nlogin()：请求运行时完成登录。无参数，不接收账号密码。普通账号密码由运行时填写，验证码或扫码由用户接管；不要用 fill/read 操作密码字段。\n"

TOOL_HELP += "\nclick(target, button=left, expect_popup=false)：录制确认点击会打开新标签页时设 expect_popup=true；先监听弹出页再点击，自动切换新页，再执行 wait_after。无需硬编码 page_id。\n"

TOOL_HELP += "\nTARGET 的 has_text 默认子串匹配；has_text_exact:true 使 has_text 对整个 DOM 文字精确匹配（忽略空白差异），可排除同名摘要，不受 CSS 图标影响。download 返回成功时已等待文件保存完成，无需再等待下载按钮恢复。PDF 会核验文件头，HTML 错误页不算 PDF 下载成功。\n"

TOOL_HELP += "\nTARGET 支持 title（实际观察到的 HTML title 属性），使用 get_by_title 精确定位图标控件。\n"

TOOL_HELP += "\npress(target, key, expect_popup=False)：回车打开新标签页时设置 expect_popup=true，工具等待并切换新页。\n"
