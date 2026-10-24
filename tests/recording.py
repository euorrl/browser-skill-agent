"""真实 Edge 录制测试：用户事件、跨页面、文件、重启隔离和密码遮蔽；不调用模型。"""
import asyncio
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time
from playwright.async_api import async_playwright
from browser_skill_agent.recording.recorder import Recorder
from browser_skill_agent.recording.storage import clean_url

HTML = """<!doctype html><html lang="zh"><head><title>录制测试</title></head><body><main>
<label>关键词<input id="query"></label><label>密码<input id="password" type="password"></label>
<button id="search" onclick="setTimeout(()=>{document.querySelector('#result').textContent='查询完成：'+document.querySelector('#query').value;document.querySelector('#computed').value='dynamic-result';document.querySelector('#late').disabled=false;},100)">搜索</button>
<p id="result" role="status">尚未搜索</p><input id="computed" readonly><button id="late" disabled>延迟按钮</button><button id="double">双击示例</button>
<label>排序<select id="sort"><option value="up">价格升序</option><option value="down">价格降序</option></select></label>
<label><input id="check" type="checkbox">仅现货</label>
<label>附件<input id="upload" type="file" multiple></label>
<a href="/download">下载文件</a><a href="/page2" target="_blank">新页面</a><a href="/page2">跳转</a>
<button onclick="document.querySelector('#answer').textContent=confirm('是否继续？')?'确认':'取消'">确认操作</button><p id="answer"></p>
<iframe title="嵌入表单" src="/frame"></iframe></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/download':
            body=b'recording download fixture'
            self.send_response(200);self.send_header('Content-Disposition','attachment; filename="result.txt"')
            self.send_header('Content-Length',str(len(body)));self.end_headers()
            self.wfile.write(body[:5]);self.wfile.flush();time.sleep(.8);self.wfile.write(body[5:]);return
        body=('<label>框架字段<input id="inside"></label>' if self.path=='/frame' else
              '<h1>第二页面</h1><button>结束页面</button>' if self.path=='/page2' else HTML.replace('src="/frame"',f'src="http://localhost:{self.server.server_port}/frame"')).encode('utf-8')
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass


async def wait_until(predicate):
    for _ in range(150):
        if predicate():return
        await asyncio.sleep(.1)
    raise AssertionError('等待录制状态超时')


async def verify(root,url):
    assert 'my-secret' not in clean_url('https://user:my-secret@example.com/?token=my-secret')
    assert clean_url('data:text/html,my-secret')=='data:[内容未记录]'
    async with async_playwright() as pw:
        if os.environ.get('RECORDING_PERSISTENT'):
            context=await pw.chromium.launch_persistent_context('',channel='msedge',headless=not bool(os.environ.get('RECORDING_HEADED')),accept_downloads=True)
            browser=None
        else:
            browser=await pw.chromium.launch(channel='msedge',headless=not bool(os.environ.get('RECORDING_HEADED')))
            context=await browser.new_context(accept_downloads=True)
        recorder=Recorder(context,root)
        try:
            control=await recorder.open(url)
            if os.environ.get('RECORDING_SCREENSHOT'):
                await control.screenshot(path=os.environ['RECORDING_SCREENSHOT'],full_page=True)
            await control.locator('#start').click()
            await wait_until(lambda:recorder.current is not None and bool(recorder.pages))
            page=next(p for p,r in recorder.owners.items() if r==recorder.current)
            await page.locator('#query').wait_for()
            await page.wait_for_function('!!window.__bsaRecorderFlush')
            print('测试：录制与记录核验',flush=True)
            await page.locator('#query').press_sequentially('pliers',delay=15)
            await page.locator('#password').fill('DO-NOT-SAVE-password-123')
            await page.get_by_role('button',name='搜索',exact=True).click()
            await page.get_by_role('status').filter(has_text='查询完成').wait_for()
            await page.get_by_label('排序').focus()
            await page.get_by_label('排序').press('ArrowDown')
            await page.get_by_label('排序').press('Enter')
            await page.get_by_label('仅现货').check()
            await page.locator('#double').dblclick()
            files=[root/'first.txt',root/'second.txt']
            for i,p in enumerate(files):p.write_text(f'upload fixture {i}',encoding='utf-8')
            await page.locator('#upload').set_input_files(files)
            await page.frame_locator('iframe').get_by_label('框架字段').fill('iframe value')
            async with page.expect_popup() as popup:
                await page.get_by_role('link',name='新页面',exact=True).click()
            second=await popup.value
            await second.get_by_role('button').click()
            await second.close()
            dialog_click=asyncio.create_task(page.get_by_role('button',name='确认操作').click())
            await wait_until(lambda:bool(getattr(recorder,'pending_dialog',None)))
            await control.locator('#acceptDialog').click()
            await dialog_click
            await page.locator('#answer').filter(has_text='确认').wait_for()
            async with page.expect_download():
                await page.get_by_role('link',name='下载文件').click()
            async with page.expect_download():
                await page.get_by_role('link',name='下载文件').click()
            # 同名两次下载不会覆盖，结束时等待全部保存。
            print('测试：结束并等待下载',flush=True)
            await control.locator('#stop').click()
            await wait_until(lambda:recorder.current.session['status']=='completed')
            print('测试：录制与记录核验',flush=True)
            first=recorder.current
            assert len(first.session['pages'])==2,first.session['pages']
            assert len(first.session['downloads'])==2
            assert len({d['path'] for d in first.session['downloads']})==2
            assert all(d['status']=='completed' for d in first.session['downloads'])
            download=first.session['downloads'][0]
            assert download['status']=='completed'
            assert Path(download['path']).read_bytes()==b'recording download fixture'
            actions=first.actions
            fills=[a for a in actions if a['kind']=='fill' and a['target'].get('id')=='query']
            assert len(fills)==1 and fills[0]['value']=='pliers'
            assert len(fills[0]['source_events'])==6
            assert any(a['kind']=='double_click' for a in actions)
            assert any(a['kind']=='select' and a['options'][0]['value']=='down' for a in actions),[(a['kind'],a.get('options')) for a in actions]
            assert any(a['kind']=='set_checked' and a['checked'] for a in actions)
            upload=next(a for a in actions if a['kind']=='upload')
            assert [f['name'] for f in upload['files']]==['first.txt','second.txt']
            assert upload['files'][0]['sha256']==hashlib.sha256(files[0].read_bytes()).hexdigest()
            assert any(a.get('value')=='iframe value' and a['frame_id']!='f1' for a in actions)
            assert all('DO-NOT-SAVE' not in p.read_text(encoding='utf-8') for p in first.folder.iterdir() if p.suffix in ('.json','.jsonl'))
            events=[json.loads(line) for line in (first.folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
            assert any(e['type']=='observation' and '查询完成' in e.get('text','') for e in events)
            assert any(c.get('id')=='computed' and c['value']=='dynamic-result' for e in events for c in e.get('controls',[]))
            assert any(c.get('id')=='late' and c['enabled'] for e in events for c in e.get('controls',[]))
            assert any(e['type']=='page_open' and e['page_id']=='p2' for e in events)
            assert any(e['type']=='page_close' and e['page_id']=='p2' for e in events)
            assert all('浏览器操作录制'!=e.get('title') for e in events)
            # 新开始以及重新开始不会复用上次动作；重新开始保留 Cookie。
            print('测试：重新开始',flush=True)
            await control.evaluate('(url)=>window.__bsaControl("start",url)',url)
            old=recorder.current
            page=next(p for p,r in recorder.owners.items() if r==old)
            await page.wait_for_function('!!window.__bsaRecorderFlush')
            await page.locator('#query').fill('discard this')
            await context.add_cookies([{'name':'session-test','value':'keep','url':url}])
            print('测试：调用重新开始',flush=True)
            await control.locator('#restart').click()
            assert await control.locator('#restartDialog').is_visible()
            await control.locator('#continue').click()
            assert recorder.current==old and old.session['status']=='recording'
            await control.locator('#restart').click()
            await control.locator('#confirmRestart').click()
            await wait_until(lambda:recorder.current!=old and bool(recorder.current.session['pages']))
            print('测试：重新开始已返回',flush=True)
            current=recorder.current
            assert old.session['status']=='abandoned' and current.id!=old.id
            assert not current.actions
            assert any(c['name']=='session-test' for c in await context.cookies())
            assert page.is_closed()
            page=next(p for p,r in recorder.owners.items() if r==current)
            await page.wait_for_function('!!window.__bsaRecorderFlush')
            await page.locator('#query').fill('new recording')
            await page.get_by_role('link',name='跳转',exact=True).click()
            await page.get_by_role('button').click()
            await recorder.flush(current)
            assert any(a.get('value')=='new recording' for a in current.actions)
            assert not any(a.get('value')=='discard this' for a in current.actions)
            await recorder.shutdown()
            assert current.session['status']=='interrupted'
            print('通过：输入合并、密码遮蔽、动态观察、下拉、勾选、跨源 iframe、新标签页、弹窗、上传哈希、下载完成、跳转重注入、重新开始隔离及会话保留。')
        finally:
            await recorder.shutdown();await context.close()
            if browser:await browser.close()


if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    Thread(target=server.serve_forever,daemon=True).start()
    try:
        with TemporaryDirectory() as folder:asyncio.run(asyncio.wait_for(verify(Path(folder),f'http://127.0.0.1:{server.server_port}/'),60))
    finally:server.shutdown();server.server_close()
