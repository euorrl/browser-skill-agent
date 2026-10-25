"""将有界面浏览器暂时最小化，结束后显示同一会话，避免重新加载丢失状态。"""


RESULT_ONLY_ARGS = ["--window-position=80,60", "--window-size=1280,900", "--start-minimized"]


class ResultOnlyDisplay:
    def __init__(self, context):
        self.context = context
        context._bsa_display = self
        self.hidden = True
        self.minimized_windows = set()
        context.on("page", self.hide)
        for page in context.pages:
            self.hide(page)

    def bounds(self, page, left, top, minimize=False):
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
            window_id = window['windowId']
            if minimize and window_id in self.minimized_windows:
                return  # 用户从任务栏恢复后，同窗口新增标签页不再强制隐藏。
            session.send("Browser.setWindowBounds", {
                "windowId": window["windowId"], "bounds": {"windowState": "normal"},
            })
            session.send("Browser.setWindowBounds", {
                "windowId": window["windowId"],
                "bounds": {"left": left, "top": top, "width": 1280, "height": 900},
            })
            if minimize:
                session.send("Browser.setWindowBounds", {"windowId": window_id, "bounds": {"windowState": "minimized"}})
                self.minimized_windows.add(window_id)
        finally:
            session.detach()

    def is_minimized(self, page):
        session = self.context.new_cdp_session(page)
        try:
            return session.send('Browser.getWindowForTarget')['bounds'].get('windowState') == 'minimized'
        finally:
            session.detach()

    def activate(self, page):
        """自动切换标签页不恢复最小化窗口；用户恢复后的窗口正常切换。"""
        if not self.is_minimized(page):
            page.bring_to_front()

    def hide(self, page):
        if self.hidden and not page.is_closed():
            self.bounds(page, 80, 60, minimize=True)

    def reveal(self, active_page):
        self.hidden = False
        for page in self.context.pages:
            if not page.is_closed():self.bounds(page, 80, 60)
        if active_page and not active_page.is_closed():active_page.bring_to_front()

    def conceal(self):
        self.hidden = True
        self.minimized_windows.clear()
        for page in self.context.pages:self.hide(page)

    def show(self, active_page):
        self.hidden = False
        self.context.remove_listener("page", self.hide)
        for page in self.context.pages:
            if not page.is_closed():
                self.bounds(page, 80, 60)
        if active_page is not None and not active_page.is_closed():
            active_page.bring_to_front()
