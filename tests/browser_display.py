"""验证结束后显示窗口，且保留 DOM、表单和多个标签页。"""

from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

from browser_skill_agent.browser_display import RESULT_ONLY_ARGS, ResultOnlyDisplay
from browser_skill_agent.tools import BrowserTools


with TemporaryDirectory() as directory, sync_playwright() as pw:
    context = pw.chromium.launch_persistent_context(directory, channel="msedge", headless=False,
                                                   args=RESULT_ONLY_ARGS)
    try:
        display = ResultOnlyDisplay(context)
        page = context.pages[0]

        def bounds(page):
            session = context.new_cdp_session(page)
            try:
                return session.send("Browser.getWindowForTarget")["bounds"]
            finally:
                session.detach()

        assert bounds(page)["windowState"] == "minimized", bounds(page)
        page.set_content('<label>内容<input></label><p role="status">完成</p>')
        page.get_by_label("内容").fill("保留填写值")
        page.evaluate("window.resultMarker = 42")
        tools = BrowserTools(page)
        first_id = tools.session.tab_list()[0]["id"]
        assert tools.execute("tabs", {"action": "new"})["ok"]
        second = tools.page
        second.set_content('<p>第二个标签页</p>')
        assert bounds(second)["left"] >= 0, bounds(second)
        assert tools.execute("tabs", {"action": "switch", "page_id": first_id})["ok"]
        assert bounds(page)["windowState"] == "minimized", bounds(page)
        # 模拟用户从任务栏恢复窗口：位于屏幕内，新标签页不会再次挪走窗口。
        display.reveal(page)
        assert bounds(page)['windowState'] == 'normal'
        assert bounds(page)['left'] >= 0
        display.conceal()
        assert bounds(page)['windowState'] == 'minimized'
        page.set_content("<button onclick=\"window.open('about:blank')\">打开</button><label>内容<input value='保留填写值'></label>")
        assert tools.execute('click',{'target':{'role':'button','name':'打开'},'expect_popup':True})['ok']
        assert bounds(tools.page)['windowState']=='minimized'
        tools.page.close()
        tools.session.page=page
        display.bounds(page,80,60)
        third=context.new_page()
        assert bounds(page)['windowState']=='normal'
        third.close()
        display.show(page)
        assert bounds(page)["left"] >= 0, bounds(page)
        assert page.get_by_label("内容").input_value() == "保留填写值"
        assert page.evaluate("window.resultMarker") == 42
        assert len(context.pages) == 2
        assert second.locator('body').inner_text() == '第二个标签页'
    finally:
        context.close()

print("通过：执行期最小化、手动恢复不再挪出屏幕、结束后恢复窗口、DOM/输入值/多标签页保留。")
