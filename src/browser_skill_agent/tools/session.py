"""管理当前标签页、框架及语义定位，不包含网站专属逻辑。"""

import json
import re
from time import monotonic

from playwright.sync_api import Page, expect


class Session:
    def __init__(self, page: Page):
        self.page = page
        self.context = page.context
        self.context.set_default_timeout(10_000)
        self.pages = {}
        self.frames = {}
        self.dialog_action = "dismiss"
        self.dialog_text = ""
        self.last_dialog = None
        self.context.on("page", self.register_page)
        for existing in self.context.pages:
            self.register_page(existing)

    def register_page(self, page):
        if page not in self.pages.values():
            self.pages[f"p{len(self.pages) + 1}"] = page
            page.on("dialog", self.handle_dialog)

    def handle_dialog(self, dialog):
        self.last_dialog = {"type": dialog.type, "message": dialog.message,
                            "action": self.dialog_action}
        if self.dialog_action == "accept":
            dialog.accept(self.dialog_text if dialog.type == "prompt" else None)
        else:
            dialog.dismiss()
        # 接受只对下一次弹窗有效，之后恢复默认取消。
        self.dialog_action, self.dialog_text = "dismiss", ""

    def current(self):
        if self.page.is_closed():
            available = [p for p in self.context.pages if not p.is_closed()]
            if not available:
                raise ValueError("所有标签页已关闭")
            self.page = available[-1]
        return self.page

    def tab_list(self):
        current = self.current()
        for page in self.context.pages:
            self.register_page(page)
        return [{"id": key, "url": page.url, "active": page == current}
                for key, page in self.pages.items() if not page.is_closed()]

    def frame_list(self):
        page = self.current()
        for frame in page.frames:
            if frame not in self.frames.values():
                self.frames[f"f{len(self.frames) + 1}"] = frame
        return [{"id": key, "name": frame.name, "url": frame.url,
                 "main": frame == page.main_frame}
                for key, frame in self.frames.items() if frame in page.frames]

    def frame(self, frame_id=None):
        page = self.current()
        if frame_id is None:
            return page.main_frame
        self.frame_list()
        frame = self.frames.get(frame_id)
        if frame is None or frame not in page.frames:
            raise ValueError("框架不存在或已失效，请使用当前观察中的框架编号")
        return frame

    def target(self, target: dict):
        if "has_text_exact" in target and "has_text" not in target:
            raise ValueError("has_text_exact 必须与 has_text 一起使用")
        scope = self.frame(target.get("frame"))
        if "within" in target:
            parent = dict(target["within"])
            if "frame" in target:
                parent.setdefault("frame", target["frame"])
            scope = self.target(parent)
        exact = target.get("exact", True)
        if "role" in target:
            kwargs = {"exact": exact}
            if "name" in target:
                kwargs["name"] = target["name"]
            locator = scope.get_by_role(target["role"], **kwargs)
        elif "id" in target:
            locator = scope.locator(f'[id={json.dumps(target["id"], ensure_ascii=False)}]')
        else:
            for key in ("label", "placeholder", "text", "test_id", "title"):
                if key in target:
                    method = getattr(scope, f"get_by_{key}")
                    locator = method(target[key]) if key == "test_id" else method(target[key], exact=exact)
                    break
            else:
                raise ValueError("目标需要提供 role、label、placeholder、text、test_id 或实际观察到的 id")
        if "has_text" in target:
            text = target["has_text"]
            if target.get("has_text_exact"):
                text = re.compile(r"^\s*" + r"\s+".join(re.escape(word) for word in text.split()) + r"\s*$")
            locator = locator.filter(has_text=text)
        if "visible" in target:
            locator = locator.filter(visible=target["visible"])
        if "nth" in target:
            if not isinstance(target["nth"], int) or target["nth"] < 0:
                raise ValueError("nth 必须为从 0 开始的非负整数")
            locator = locator.nth(target["nth"])
        return locator

    def prepare(self, target, editable=False):
        # 每次重新解析语义定位，不缓存易失效的 DOM 节点，也不默认选第一个。
        locator = self.target({"visible": True, **target})
        expect(locator).to_have_count(1, timeout=10_000)
        expect(locator).to_be_visible(timeout=10_000)
        expect(locator).to_be_enabled(timeout=10_000)
        if editable:
            expect(locator).to_be_editable(timeout=10_000)
        deadline = monotonic() + 10
        while locator.evaluate("el => !!el.closest('[aria-busy=\"true\"]')"):
            if monotonic() >= deadline:
                raise TimeoutError("目标所在区域仍在加载，请重新观察或使用 wait_for")
            self.current().wait_for_timeout(100)
        return locator
