"""工具白名单与统一调用入口；工具说明与实现分开存放。"""

from inspect import signature

from .actions import Actions
from .files import Files, FileOptions
from .navigation import Navigation
from .observe import Observation
from .session import Session
from .waiting import Waiting
from .help import TOOL_HELP


class BrowserTools:
    def __init__(self, page, approval=None, file_options=None):
        self.approval = approval
        self.session = Session(page)
        self.observation = Observation(self.session)
        self.files = Files(self.session, file_options if file_options is not None else FileOptions())
        self._tools = {}
        groups = [
            (Actions(self.session), ("click", "double_click", "hover", "fill", "type_text",
                                     "press", "select", "set_checked", "scroll", "drag")),
            (Navigation(self.session), ("goto", "back", "reload", "tabs", "dialog")),
            (self.observation, ("read", "snapshot", "locate")),
            (Waiting(self.session), ("wait", "wait_for")),
            (self.files, ("upload", "download")),
        ]
        for group, names in groups:
            self._tools.update({name: getattr(group, name) for name in names})

    @property
    def page(self):
        return self.session.current()

    def target(self, target):
        return self.session.target(target)

    def observe(self):
        observation = self.observation.observe()
        observation["upload_files"] = self.files.options.available()
        return observation

    def read(self, target, kind="text", attribute=None):
        return self.observation.read(target, kind, attribute)

    def execute(self, name, args):
        try:
            if name not in self._tools:
                raise ValueError(f"未知工具：{name}")
            args = dict(args)
            required = args.pop("requires_approval", False)
            if not isinstance(required, bool):
                raise ValueError("requires_approval 必须为布尔值")
            wait_after = args.pop("wait_after", None)
            wait_response = args.pop("wait_response", None)
            if wait_after is not None:
                if not isinstance(wait_after, dict):
                    raise ValueError("wait_after 必须是 wait_for 参数对象")
                # 在动作执行前确认参数形式，防止拼写错误导致先提交再报错。
                signature(self._tools["wait_for"]).bind(**wait_after)
            args = self.files.prepare(name, args)
            signature(self._tools[name]).bind(**args)
            if wait_response is not None and not isinstance(wait_response, str):
                raise ValueError("wait_response 必须是响应 URL 的匹配模式")
            authorization = None
            if self.approval is not None:
                authorization = self.approval.authorize(self, name, args, required)
                if not authorization["approved"]:
                    return {"ok": False, "error": authorization["reason"],
                            "approval_denied": True, "executed": False, "approval": authorization}
            if wait_response is not None:
                # 先监听再操作，避免快速响应丢失；动作成功后的超时不重放动作。
                result = None
                try:
                    with self.page.expect_response(wait_response, timeout=30000) as pending:
                        result = {"ok": True, "data": self._tools[name](**args)}
                    response = pending.value
                    response.body()
                    if not response.ok:
                        raise ValueError(f"页面请求返回 HTTP {response.status}")
                except Exception as exc:
                    if result is None:
                        raise
                    result["after_wait"] = {"ok": False, "error": str(exc)}
                    if authorization:
                        result["approval"] = authorization
                    return result
            else:
                result = {"ok": True, "data": self._tools[name](**args)}
            if wait_after is not None:
                try:
                    self._tools["wait_for"](**wait_after)
                    result["after_wait"] = {"ok": True}
                except Exception as exc:
                    # 已执行的动作不因后续等待超时而标记为未执行，更不会自动重放。
                    result["after_wait"] = {"ok": False, "error": str(exc),
                                            "hint": "动作已执行，请重新观察，不要盲目重复提交"}
            if authorization:
                result["approval"] = authorization
            return result
        except Exception as exc:
            # 操作超时不代表没有生效，交回 Runtime 重新观察。
            return {"ok": False, "error": str(exc)}
