"""工作台登录参数、待补充状态、后台执行与密码不落盘。"""
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import ThreadingHTTPServer
from playwright.async_api import async_playwright
from login import Handler, SECRET, definition, save
from browser_skill_agent.studio.app import Studio, ASSETS


async def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    try:
        with TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'skills/login';folder.mkdir(parents=True);save(folder/'SKILL.md',definition(origin))
            (folder/'example_params.json').write_text('{"username":"tester","password":""}',encoding='utf-8')
            app=Studio(root);item=app.store.items[0]
            app.model=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('缺密码时不能请求模型'))
            app.launch('validate',app.validate(item['id']),item['id']);await app.worker
            assert '等待补充登录参数' in app.job['message'] and item['status']=='unverified'
            async with async_playwright() as pw:
                browser=await pw.chromium.launch(channel='msedge',headless=True);page=await browser.new_page();app.page=page
                await page.expose_binding('__flowStudio',app.command);await page.goto((ASSETS/'index.html').as_uri())
                await page.get_by_role('button',name='▶ 运行',exact=True).click()
                field=page.locator('#params [data-param=password]');assert await field.get_attribute('type')=='password'
                await field.fill(SECRET);await page.locator('#closeAfter').check();await page.locator('#backgroundRun').check()
                await page.locator('#runFlow').click();await app.worker
                assert app.job['state']=='done',app.job
                assert await field.input_value()==''
                assert SECRET not in json.dumps(app.state(),ensure_ascii=False)
                assert app.credentials[item['id']]['password']==SECRET
                for file in [app.store.index,folder/'SKILL.md',folder/'example_params.json']:
                    assert SECRET not in file.read_text(encoding='utf-8')
                # 人工接管弹窗使用登录语义，而非普通操作授权。
                async def ask():
                    accepted=await app.ask('请完成扫码登录',{'url':origin},'login')
                    app.job.update(state='done',message='已确认' if accepted else '已停止')
                app.launch('run',ask(),item['id'])
                await page.get_by_role('button',name='登录完成，继续',exact=True).click()
                await app.worker
                assert app.job['message']=='已确认'
                await page.screenshot(path='.cache/studio-login.png');await browser.close()
            print('通过：登录参数密码输入框、缺密码暂停验证、后台真实登录、人工确认界面、密码不进状态与文件。')
    finally:server.shutdown();server.server_close()

if __name__=='__main__':asyncio.run(main())
