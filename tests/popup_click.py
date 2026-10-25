"""预期弹出页必须先监听、切换后等待；不沿用录制页号。"""
from tempfile import TemporaryDirectory
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_skill_agent.tools import BrowserTools

with TemporaryDirectory() as folder, sync_playwright() as pw:
    root=Path(folder)
    (root/'detail.html').write_text('<h1>目标报告</h1>',encoding='utf-8')
    (root/'index.html').write_text('<meta charset="utf-8"><a target="_blank" href="detail.html">公司：2026年半年度报告</a><a href="#">公司：其他公告</a>',encoding='utf-8')
    browser=pw.chromium.launch(channel='msedge',headless=True)
    context=browser.new_context()
    page=context.new_page();page.goto((root/'index.html').as_uri())
    tools=BrowserTools(page)
    context.new_page()  # 新页编号不应假定为 p2。
    result=tools.execute('click',{'target':{'role':'link','name':'公司：2026年半年度报告'},'expect_popup':True,'wait_after':{'url':'**/detail.html','timeout':3}})
    assert result['ok'] and result['after_wait']['ok'],result
    assert tools.page.url.endswith('/detail.html') and tools.page!=page
    assert len(context.pages)==3
    result=tools.execute('click',{'target':{'role':'heading','name':'目标报告'},'expect_popup':'yes'})
    assert not result['ok']
    browser.close()
print('通过：完整标题精确定位、弹出页切换、等待顺序及参数校验。')
