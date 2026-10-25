"""将有界面浏览器暂放屏幕外，结束后显示同一会话，避免重新加载丢失状态。"""


RESULT_ONLY_ARGS = ["--window-position=-32000,-32000", "--window-size=1280,900"]


class ResultOnlyDisplay:
    def __init__(self, context):
        self.context = context
        self.hidden = True
        context.on("page", self.hide)
        for page in context.pages:
            self.hide(page)

    def bounds(self, page, left, top):
        if page.url.startswith(("edge://", "chrome://", "chrome-extension://")):
            return  # 下载中心等内部目标没有可管理的独立浏览器窗口。
        session = self.context.new_cdp_session(page)
        try:
            try:
                window = session.send("Browser.getWindowForTarget")
            except Exception as exc:
                if "Browser window not found" in str(exc):
                    return
                raise
            session.send("Browser.setWindowBounds", {
                "windowId": window["windowId"], "bounds": {"windowState": "normal"},
            })
            session.send("Browser.setWindowBounds", {
                "windowId": window["windowId"],
                "bounds": {"left": left, "top": top, "width": 1280, "height": 900},
            })
        finally:
            session.detach()

    def hide(self, page):
        if self.hidden and not page.is_closed():
            self.bounds(page, -32000, -32000)

    def reveal(self, active_page):
        self.hidden = False
        for page in self.context.pages:
            if not page.is_closed():self.bounds(page, 80, 60)
        if active_page and not active_page.is_closed():active_page.bring_to_front()

    def conceal(self):
        self.hidden = True
        for page in self.context.pages:self.hide(page)

    def show(self, active_page):
        self.context.remove_listener("page", self.hide)
        for page in self.context.pages:
            if not page.is_closed():
                self.bounds(page, 80, 60)
        if active_page is not None and not active_page.is_closed():
            active_page.bring_to_front()
