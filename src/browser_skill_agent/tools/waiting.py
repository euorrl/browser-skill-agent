"""动态页面的有界等待，不负责判断业务任务是否完成。"""

from playwright.sync_api import expect


class Waiting:
    def __init__(self, session):
        self.s = session

    def wait(self, seconds=1):
        self.s.current().wait_for_timeout(min(max(seconds, 0), 5) * 1000)

    def wait_for(self, target=None, state="visible", value=None, url=None, timeout=10):
        milliseconds = min(max(timeout, 0.1), 30) * 1000
        if url is not None:
            self.s.current().wait_for_url(url, timeout=milliseconds, wait_until="domcontentloaded")
            return
        if target is None:
            raise ValueError("wait_for 需要 target 或 url")
        locator = self.s.target(target)
        if state in ("visible", "hidden", "attached", "detached"):
            locator.wait_for(state=state, timeout=milliseconds)
        elif state == "enabled":
            expect(locator).to_be_enabled(timeout=milliseconds)
        elif state == "text":
            expect(locator).to_contain_text(value, timeout=milliseconds)
        elif state == "value":
            expect(locator).to_have_value(value, timeout=milliseconds)
        elif state == "count":
            expect(locator).to_have_count(int(value), timeout=milliseconds)
        else:
            raise ValueError("未知等待状态")
