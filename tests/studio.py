"""工作台本地闭环：真实浏览器交互，生成与聊天使用测试响应。"""
import asyncio
import json
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright

from browser_skill_agent.studio.app import Studio, ASSETS
from browser_skill_agent.studio.store import Store


def fixture(root):
    path = root / "skills/demo"
    path.mkdir(parents=True)
    page = root / "page.html"
    page.write_text('<meta charset="utf-8"><label>查询<input id="query"></label><p id="result">准备完成</p>', encoding="utf-8")
    (path / "SKILL.md").write_text('''---
name: demo
description: 根据关键词查询资料，并读取页面结果。
params: [query]
start: ''' + page.as_uri() + '''
goal: 查询指定资料
actions:
- title: 填写查询
  tool: fill
  args:
    target: {label: 查询}
    value_ref: query
- title: 读取输入值
  tool: read
  args:
    target: {id: query}
    kind: value
---
只查询，不提交或修改其他内容。
''', encoding="utf-8")
    (path / "example_params.json").write_text('{"query":"人工智能"}', encoding="utf-8")
    return page, path / "SKILL.md"


async def wait_for(predicate, timeout=15):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(.1)


async def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        page_path, definition = fixture(root)
        app = Studio(root)
        item = app.store.items[0]
        assert item["defaults"] == {"query": "人工智能"}
        async with async_playwright() as pw:
            app.pw = pw
            browser = await pw.chromium.launch(channel="msedge", headless=True)
            page = await browser.new_page(viewport={"width": 1380, "height": 900}, device_scale_factor=1)
            app.page = page
            await page.expose_binding("__flowStudio", app.command)
            await page.goto((ASSETS / "index.html").as_uri())
            await page.get_by_role('button', name='▶ 运行', exact=True).wait_for()
            await page.screenshot(path=str(Path.cwd() / '.cache/studio-desktop.png'), full_page=True)
            await page.get_by_role('button', name='▶ 运行', exact=True).click()
            assert await page.locator('#params input').input_value() == '人工智能'
            await page.get_by_role('button', name='编辑流程', exact=True).click()
            await page.locator('#editName').fill('搜索中文资料')
            await page.locator('#editParams input').fill('机器学习')
            await page.get_by_role('button', name='保存修改', exact=True).click()
            await wait_for(lambda: app.store.items[0]['name'] == '搜索中文资料')
            assert Store(root).items[0]['defaults']['query'] == '机器学习'
            # 对话匹配只准备参数，不执行；保留短对话上下文用于后续修改。
            requests = []
            class ChatModel:
                def request(self, state, prompt):
                    requests.append(state)
                    return {'flow_id': item['id'], 'params': {'query': '自然语言参数'}, 'message': '已找到查询流程。'}
            app.model = lambda *args, **kwargs: ChatModel()
            await page.locator('#chatInput').fill('查询自然语言参数')
            await page.locator('#send').click()
            await page.get_by_role('button', name='检查参数并运行', exact=True).click()
            assert await page.locator('#params input').input_value() == '自然语言参数'
            assert app.worker is None
            await page.locator('#flowDialog .icon.close').click()
            await app.chat('沿用刚才的参数')
            assert requests[-1]['history']
            await page.get_by_role('button', name='▶ 运行', exact=True).click()
            await page.locator('#closeAfter').check()
            assert await page.locator('#approvalMode').input_value() == 'human'
            assert not await page.locator('#enableLlm').is_checked()
            await page.locator('#runFlow').click()
            await wait_for(lambda: app.worker is not None)
            await app.worker
            assert app.job['result']['status'] == 'succeeded', app.job
            assert app.job['result']['mode'] == 'script'
            assert app.job['browser_open'] is False
            assert any('操作步骤' in line['text'] for line in app.job['logs'])
            await page.evaluate('refresh()')
            assert '开始运行' in await page.locator('#messages').inner_text()
            assert '已完成' in await page.locator('#messages').inner_text()
            assert '已找到查询流程' not in await page.locator('#messages').inner_text()
            assert not await page.locator('#jobLogs').evaluate('el=>el.open')
            await page.get_by_text('展开运行日志', exact=True).click()
            await page.evaluate('refresh()')
            assert await page.locator('#jobLogs').evaluate('el=>el.open')
            assert await page.locator('#messages .message').count() == 3
            old_job = app.job['id']
            app.log('上一任务专用日志')
            original = app.store.path(item['id']).read_text(encoding='utf-8')
            app.store.path(item['id']).write_text(original.replace('value_ref: query','value_ref: query\n    requires_approval: true'),encoding='utf-8')
            class Reviewer:
                usage = {'requests': 0}
                def review(self, state):
                    self.usage['requests'] += 1
                    return {'approved': True, 'reason': '测试操作'}
            reviewer = Reviewer()
            app.model = lambda *args, **kwargs: reviewer
            for mode in ('ai','allow'):
                await page.get_by_role('button', name='▶ 运行', exact=True).click()
                await page.locator('#approvalMode').select_option(mode)
                await page.locator('#runFlow').click()
                await app.worker
                assert app.job['result']['status'] == 'succeeded'
                assert app.job['result']['approval']['mode'] == mode
                assert app.pending is None
                assert app.job['id'] != old_job
                assert all('上一任务专用日志' not in line['text'] for line in app.job['logs'])
                assert app.chat_history == []
            assert reviewer.usage['requests'] == 1
            app.store.path(item['id']).write_text(original,encoding='utf-8')
            class Planner:
                usage = {'requests': 0}
                def decide(self, state):
                    self.usage['requests'] += 1
                    if self.usage['requests'] == 1:
                        return {'stage':'查询', 'actions':[
                            {'tool':'fill','args':{'target':{'label':'查询'},'value':'模型执行'}},
                            {'tool':'read','args':{'target':{'id':'query'},'kind':'value'}}]}
                    return {'tool':'finish','args':{'status':'succeeded','message':'模型流程完成'}}
                def review(self, state):
                    raise AssertionError('人工授权不应请求 AI 审核')
            planner = Planner()
            app.model = lambda *args, **kwargs: planner
            await page.get_by_role('button', name='▶ 运行', exact=True).click()
            await page.locator('#enableLlm').check()
            await page.locator('#runFlow').click()
            await app.worker
            assert app.job['result']['mode'] == 'llm'
            assert app.job['result']['status'] == 'succeeded'
            assert app.job['result']['approval']['mode'] == 'human'
            assert planner.usage['requests'] == 2
            await page.get_by_role('button', name='▶ 运行', exact=True).click()
            assert not await page.locator('#enableLlm').is_checked()
            await page.locator('#flowDialog .icon.close').click()
            # 保留窗口选项：结果返回后仍可查看，用户从工作台关闭。
            app.launch('run', app.execute(item['id'], {}, False), item['id'])
            await wait_for(lambda: app.job.get('browser_open') is True)
            app.stop_browser.set()
            await app.worker
            assert app.job['browser_open'] is False
            # 使用实际授权弹窗确认，避免调用终端 input。
            pending = asyncio.create_task(app.ask('测试操作确认', {'tool': 'fill'}))
            await page.get_by_role('button', name='允许操作', exact=True).wait_for()
            await page.get_by_role('button', name='允许操作', exact=True).click()
            assert await pending is True
            # 独立录制窗口关闭后应保存并调用生成；不发送测试数据到模型。
            calls = []
            async def generated(folder, name, guidance=None):
                session = json.loads((folder / 'session.json').read_text(encoding='utf-8'))
                actions = json.loads((folder / 'actions.json').read_text(encoding='utf-8'))
                assert session['status'] == 'completed'
                assert any(a.get('value') == '录制测试' for a in actions)
                assert name == '查询资料流程'
                assert guidance == {'name':'查询资料流程','description':'查找内容并读取结果','parameters':'查询词作为参数'}
                calls.append(folder)
                app.job.update(state='done', message='测试生成已完成')
            app.generate_flow = generated
            app.launch('record', app.record(page_path.as_uri(), '录制测试'))
            await wait_for(lambda: app.job['state'] == 'recording')
            target = next(p for p in app.record_context.pages if p.url == page_path.as_uri())
            await target.locator('#query').fill('录制测试')
            await wait_for(lambda: any(a.get('value') == '录制测试' for a in app.recorder.current.actions))
            old = app.recorder.current
            await app.command({'page': page, 'frame': page.main_frame}, 'record_restart')
            assert old.session['status'] == 'abandoned'
            assert app.recorder.current.id != old.id
            assert not app.recorder.closed.is_set()
            target = next(p for p in app.record_context.pages if p.url == page_path.as_uri())
            await target.locator('#query').fill('录制测试')
            await wait_for(lambda: any(a.get('value') == '录制测试' for a in app.recorder.current.actions))
            await app.record_context.close()
            await page.locator('#guidanceDialog').wait_for(state='visible')
            assert not calls
            await page.locator('#guidanceName').fill('查询资料流程')
            await page.locator('#guidanceDescription').fill('查找内容并读取结果')
            await page.locator('#guidanceParameters').fill('查询词作为参数')
            await page.evaluate('refresh()')
            assert await page.locator('#guidanceParameters').input_value() == '查询词作为参数'
            await page.screenshot(path=str(Path.cwd() / '.cache/studio-guidance.png'))
            await page.get_by_role('button', name='按补充信息生成', exact=True).click()
            await app.worker
            assert calls and app.job['state'] == 'done', app.job
            async def skip_flow():
                assert await app.collect_guidance('') == {}
                app.job.update(state='done', message='已跳过选填说明')
            app.launch('record', skip_flow())
            await page.locator('#guidanceDialog').wait_for(state='visible')
            assert await page.locator('#guidanceName').input_value() == ''
            await page.get_by_role('button', name='直接生成', exact=True).click()
            await app.worker
            assert app.job['state'] == 'done'
            assert not page.is_closed()
            # 禁止外部网页借用绑定操纵本地流程。
            result = await app.command({'page': target, 'frame': None}, 'delete', {'id': item['id']})
            assert 'error' in result
            await page.set_viewport_size({'width': 390, 'height': 844})
            await page.screenshot(path=str(Path.cwd() / '.cache/studio-mobile.png'), full_page=True)
            app.store.delete(item['id'])
            assert Store(root).items == []
            await browser.close()
    print('通过：默认参数、改名持久化、聊天选流程及参数、运行关闭/保留、网页授权、独立录制关闭与自动生成、重录、来源限制、删除。')


if __name__ == '__main__':
    asyncio.run(main())
