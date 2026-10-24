"""页面导航、标签页切换与网页原生弹窗策略。"""


class Navigation:
    def __init__(self, session):
        self.s = session

    def goto(self, url):
        self.s.current().goto(url, wait_until="domcontentloaded")

    def back(self):
        self.s.current().go_back(wait_until="domcontentloaded")

    def reload(self):
        self.s.current().reload(wait_until="domcontentloaded")

    def tabs(self, action="list", page_id=None, url=None):
        if action == "new":
            page = self.s.context.new_page()
            self.s.page = page
            if url:
                self.goto(url)
        elif action in ("switch", "close"):
            page = self.s.pages.get(page_id)
            if page is None or page.is_closed():
                raise ValueError("标签页不存在，请使用观察中的 page_id")
            if action == "switch":
                self.s.page = page
                page.bring_to_front()
            else:
                if len(self.s.context.pages) == 1:
                    raise ValueError("请保留至少一个标签页")
                page.close()
        elif action != "list":
            raise ValueError("tabs action 必须为 list、new、switch 或 close")
        return self.s.tab_list()

    def dialog(self, action="dismiss", text=""):
        if action not in ("accept", "dismiss"):
            raise ValueError("dialog action 必须为 accept 或 dismiss")
        self.s.dialog_action, self.s.dialog_text = action, text
        return {"next_dialog": action}
