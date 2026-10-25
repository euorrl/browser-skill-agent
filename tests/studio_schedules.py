"""定时计划持久化、到期触发、重复保护及真实工作台交互测试。"""
import asyncio
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.async_api import async_playwright
from browser_skill_agent.studio.app import Studio, ASSETS
from browser_skill_agent.studio.schedules import Schedules, utcnow
from studio import fixture, wait_for

async def main():
    with TemporaryDirectory() as tmp:
        root=Path(tmp);fixture(root);app=Studio(root)
        flow=app.store.items[0]
        config=dict(flow_id=flow['id'],params={'query':'定时测试'},at=(utcnow()+timedelta(hours=1)).isoformat(),approval='allow',llm=False,background=True,close_after=True,enabled=True)
        item=app.schedules.put(config)
        assert Schedules(root,app.store).get(item['id'])['params']==config['params']
        try: app.schedules.put({**config,'params':{}})
        except ValueError: pass
        else: raise AssertionError('必须先配置完整参数')
        # 模拟到期，直接执行实际本地流程，不调用模型。
        item['at']=(utcnow()-timedelta(seconds=1)).isoformat()
        await app.tick_schedules()
        worker=app.worker
        assert item['status']=='running'
        await app.tick_schedules()
        assert app.worker is worker
        await worker
        await app.tick_schedules()
        assert item['status']=='completed',item
        assert app.job['result']['outputs'][-1]['data']=='定时测试',app.job
        await app.tick_schedules();assert app.worker is worker
        # 任务占用时等待，随后超过容忍窗口不补跑。
        waiting=app.schedules.put(config);waiting['at']=(utcnow()-timedelta(seconds=1)).isoformat()
        busy=asyncio.create_task(asyncio.sleep(30));app.worker=busy
        await app.tick_schedules();assert waiting['status']=='waiting'
        waiting['at']=(utcnow()-timedelta(minutes=6)).isoformat()
        await app.tick_schedules();assert waiting['status']=='missed'
        busy.cancel();await asyncio.gather(busy,return_exceptions=True)
        # 变更定义后拒绝沿用旧计划。
        changed=app.schedules.put(config);changed['at']=(utcnow()-timedelta(seconds=1)).isoformat()
        path=app.store.path(flow['id']);path.write_text(path.read_text(encoding='utf-8')+'\n修改说明\n',encoding='utf-8')
        await app.tick_schedules();assert changed['status']=='failed' and '修改' in changed['message']
        # 重启后不重试已触发或已经过期的任务。
        interrupted=app.schedules.put(config);interrupted['status']='running'
        overdue=app.schedules.put(config);overdue['at']=(utcnow()-timedelta(minutes=1)).isoformat()
        app.schedules.save();loaded=Schedules(root,app.store)
        assert loaded.get(interrupted['id'])['status']=='interrupted'
        assert loaded.get(overdue['id'])['status']=='missed'
        app.schedules=loaded
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='msedge',headless=True)
            page=await browser.new_page(viewport={'width':1440,'height':1000})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            app.page=page
            await page.expose_binding('__flowStudio',app.command)
            await page.goto((ASSETS/'index.html').as_uri())
            await page.get_by_role('button',name='计划与定时').click()
            await page.get_by_role('button',name='新建计划').click()
            await page.locator('#scheduleParams input').fill('界面配置参数')
            await page.locator('#scheduleApproval').select_option('allow')
            await page.locator('#scheduleBackground').check()
            await page.locator('#scheduleEnabled').uncheck()
            await page.get_by_role('button',name='保存计划',exact=True).click()
            await wait_for(lambda:any(p['params'].get('query')=='界面配置参数' for p in app.schedules.items))
            saved=next(p for p in app.schedules.items if p['params'].get('query')=='界面配置参数')
            assert saved['status']=='paused' and saved['background'] and not saved['llm']
            await page.locator('#scheduleDialog').wait_for(state='hidden')
            await page.screenshot(path='.cache/studio-schedules.png')
            await page.get_by_role('button',name='我的流程').click()
            assert await page.locator('.layout').is_visible()
            assert not errors,errors
            await browser.close()
    print('通过：参数与选项保存、实际到期执行、单次触发、忙碌排队、过期处理、定义变更保护、重启恢复和工作台界面。')

if __name__=='__main__':asyncio.run(main())
