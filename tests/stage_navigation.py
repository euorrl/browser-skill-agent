"""验证预期导航可以连续读取，意外跳转、缺少等待及弹窗不能继续。"""

from playwright.sync_api import sync_playwright

from browser_skill_agent.runtime import run
from browser_skill_agent.tools import BrowserTools


class Planner:
    def __init__(self, actions):
        self.actions = actions
        self.states = []

    def decide(self, state):
        self.states.append(state)
        if len(self.states) == 1:
            return {"stage": "进入并读取条目", "actions": self.actions}
        return {"tool": "finish", "args": {"status": "succeeded", "message": "本地测试"}}


skill = {"name": "导航测试", "goal": "读取条目", "params": {}}
read = {"tool": "read", "args": {"target": {"id": "body"}}}
destination = "https://stage.test/article"
wait = {"target": {"role": "heading", "name": "目标条目"}}

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    try:
        context = browser.new_context()
        context.route("https://stage.test/**", lambda route: route.fulfill(
            content_type="text/html; charset=utf-8",
            body='<h1>目标条目</h1><p id="body">正文证据</p>' if route.request.url.endswith('/article')
            else '<a href="/article">进入条目</a>'))
        for mode in ("click", "goto", "new", "switch", "wrong_url", "no_wait", "wait_failed", "popup"):
            page = context.new_page()
            page.goto("https://stage.test/search")
            tools = BrowserTools(page)
            operation = {"tool": "click", "expected_url": destination,
                         "args": {"target": {"role": "link", "name": "进入条目"}, "wait_after": wait}}
            if mode == "goto":
                operation.update(tool="goto", args={"url": destination, "wait_after": wait})
            elif mode == "new":
                operation.update(tool="tabs", args={"action": "new", "url": destination, "wait_after": wait})
            elif mode == "switch":
                other = context.new_page()
                other.goto(destination)
                target_id = next(item["id"] for item in tools.session.tab_list() if item["url"] == destination)
                operation.update(tool="tabs", args={"action": "switch", "page_id": target_id, "wait_after": wait})
            elif mode == "wrong_url":
                operation["expected_url"] = "https://stage.test/other"
            elif mode == "no_wait":
                operation["args"].pop("wait_after")
            elif mode == "wait_failed":
                operation["args"]["wait_after"] = {"target": {"text": "不存在"}, "timeout": 0.1}
            elif mode == "popup":
                page.locator("a").evaluate("el=>el.onclick=()=>window.open('/article')")
            planner = Planner([operation, read])
            result = run(skill, tools, planner)
            assert result["turns"] == 2
            continued = mode in ("click", "goto", "new", "switch")
            assert planner.states[-1]["last_stage"]["executed"] == (2 if continued else 1), mode
            if continued:
                assert planner.states[-1]["evidence"][0]["data"] == "正文证据", mode
            else:
                assert planner.states[-1]["last_stage"]["skipped"] == 1, mode
            for tab in list(context.pages):
                tab.close()
    finally:
        browser.close()

print("通过：预期点击导航、goto、新建和切换标签页连续读取；URL 不符、缺少/失败等待及意外弹窗均停止。")
