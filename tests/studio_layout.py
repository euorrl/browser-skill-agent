"""工作台窗口适配回归：长列表不能挤走顶部按钮或聊天输入框。"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        flows = [{"id": str(i), "name": f"中文资料查询 {i}", "description": "查询并读取指定资料。",
                  "defaults": {}, "status": "unverified", "issues": [], "last_result": None} for i in range(15)]
        state = {"flows": flows, "job": None, "pending": None}
        await page.expose_binding("__flowStudio", lambda source, command, data:
                                 state)
        await page.goto((Path("src/browser_skill_agent/studio/index.html").resolve()).as_uri())
        for width, height in ((1920, 900), (1380, 780), (1100, 600), (850, 550), (390, 844)):
            await page.set_viewport_size({"width": width, "height": height})
            await page.locator(".card").first.wait_for()
            assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            if width > 800:
                await page.locator(".cards").evaluate("el => el.scrollTop = el.scrollHeight")
                geometry = await page.evaluate("""() => ({
                    top: document.querySelector('#newFlow').getBoundingClientRect().top,
                    bottom: document.querySelector('#chatForm').getBoundingClientRect().bottom,
                    height: document.documentElement.scrollHeight,
                    scroll: document.querySelector('.cards').scrollTop
                })""")
                assert geometry["top"] >= 0 and geometry["bottom"] <= height
                assert geometry["height"] <= height + 1 and geometry["scroll"] > 0
        await page.set_viewport_size({"width": 1100, "height": 650})
        state['job'] = {'id':'test-run','kind':'run','state':'done','name':'查询中文资料',
                        'message':'已完成查询，并读取到两份资料。','browser_open':True,
                        'logs':[{'time':'2026-10-25T00:00:00Z','text':f'步骤 {i}：执行成功'} for i in range(30)],
                        'result':{'outputs':[{'title':'查询结果','data':'已读取的资料内容'}]}}
        await page.evaluate('refresh()')
        await page.get_by_text('展开运行日志', exact=True).click()
        await page.evaluate('refresh()')
        assert await page.locator('#jobLogs').evaluate('el=>el.open')
        assert await page.evaluate('document.documentElement.scrollHeight <= innerHeight + 1')
        assert await page.locator('#messages .message').count() == 2
        await page.screenshot(path='.cache/studio-logs-expanded.png')
        await browser.close()
    print("通过：5 种窗口尺寸、独立列表滚动、顶部入口和聊天输入框可见。")


if __name__ == "__main__":
    asyncio.run(main())
