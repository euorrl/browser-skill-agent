"""将有界面浏览器暂放屏幕外，结束后显示同一会话，避免重新加载丢失状态。"""


RESULT_ONLY_ARGS = ["--window-position=-32000,-32000", "--window-size=1280,900"]


class ResultOnlyDisplay:
    def __init__(self, context):
        self.context = context
        context.on("page", self.hide)
        for page in context.pages:
            self.hide(page)

    def bounds(self, page, left, top):
        session = self.context.new_cdp_session(page)
        try:
            window = session.send("Browser.getWindowForTarget")
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
        if not page.is_closed():
            self.bounds(page, -32000, -32000)

    def show(self, active_page):
        self.context.remove_listener("page", self.hide)
        for page in self.context.pages:
            if not page.is_closed():
                self.bounds(page, 80, 60)
        if active_page is not None and not active_page.is_closed():
            active_page.bring_to_front()
