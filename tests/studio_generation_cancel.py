"""取消生成的界面及迟到响应回归；不请求真实模型。"""
import asyncio
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch
from playwright.async_api import async_playwright
from browser_skill_agent.studio.app import Studio, ASSETS
from browser_skill_agent.studio.store import Store
from studio import fixture, wait_for

async def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _, skill = fixture(root)
        app = Studio(root)
        app.model = lambda *args: type('FakeModel', (), {})()
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(channel='msedge', headless=True)
            page = await browser.new_page(viewport={'width':1380,'height':900})
            app.page = page
            await page.expose_binding('__flowStudio', app.command)
            await page.goto((ASSETS/'index.html').as_uri())
            source = {'page': page, 'frame': page.main_frame}
            def recording(ident):
                folder = root/'data/recordings'/ident
                folder.mkdir(parents=True)
                (folder/'session.json').write_text('{}')
                return folder
            folder = recording('cancel-guidance')
            app.launch('record', app.collect_guidance('测试'))
            app.job['recording_id'] = folder.name
            await page.locator('#guidanceDialog').wait_for(state='visible')
            await page.locator('#cancelGeneration').click()
            await wait_for(lambda: app.worker.done())
            assert app.job['state']=='cancelled' and not folder.exists()
            assert len(app.store.items)==1
            await page.get_by_text('已取消生成', exact=True).wait_for()
            # 请求仍在执行时取消；迟到响应不能添加流程或触发验证。
            started, release = threading.Event(), threading.Event()
            folder = recording('cancel-running')
            def generate(record, model, output, guidance=None):
                started.set()
                assert release.wait(15)
                target = output/'late'
                target.mkdir()
                (target/'SKILL.md').write_text(skill.read_text(encoding='utf-8'),encoding='utf-8')
                return target, {'usage':{}}
            async def forbidden(*args):
                raise AssertionError('取消后不能启动验证')
            app.validate = forbidden
            with patch('browser_skill_agent.studio.app.generate', generate):
                app.launch('record', app.generate_flow(folder, '迟到流程'))
                app.job.update(recording_id=folder.name,auto_validate=True)
                await wait_for(started.is_set)
                stale = await app.command(source,'cancel_generation',{'job_id':'old'})
                assert stale.get('error') and not app.generation_cancel.is_set()
                await page.get_by_role('button',name='取消生成并删除记录',exact=True).click()
                assert app.job['state']=='cancelling'
                release.set()
                await wait_for(lambda: app.worker.done())
            assert app.job['state']=='cancelled' and not folder.exists()
            assert len(Store(root).items)==1 and len(list((root/'skills').glob('*/SKILL.md')))==1
            await page.get_by_text('已取消生成',exact=True).wait_for()
            # 缺失关键点击证据时保留草稿，但不能自动进入验证。
            folder = recording('missing-control')
            def incomplete(record, model, output, guidance=None):
                target = output/'incomplete'
                target.mkdir()
                (target/'SKILL.md').write_text(skill.read_text(encoding='utf-8'),encoding='utf-8')
                return target, {'usage':{}, 'blocking_recording_gaps':['a5']}
            with patch('browser_skill_agent.studio.app.generate', incomplete):
                app.launch('record', app.generate_flow(folder, '证据不完整'))
                app.job.update(recording_id=folder.name, auto_validate=True)
                await wait_for(lambda: app.worker.done())
            assert app.job['state']=='blocked', app.job
            assert app.store.get(app.job['flow_id'])['status']=='blocked'
            assert 'a5' in app.job['message']
            await page.screenshot(path='.cache/studio-cancel-generation.png')
            await browser.close()
            print('通过：弹窗取消、生成中取消、过期请求拒绝、录制删除、迟到草稿丢弃、不触发验证。')

if __name__=='__main__':
    asyncio.run(main())
