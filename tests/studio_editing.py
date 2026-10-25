"""聊天修改流程闭环：真实页面确认、脚本重放，模型使用测试响应。"""
import asyncio
import copy
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright

from studio import fixture
from browser_skill_agent.studio.app import Studio, ASSETS
from browser_skill_agent.studio.store import Store, metadata
from browser_skill_agent.studio.editing import proposal


async def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        fixture(root)
        app = Studio(root)
        async def skip_validation(*args, **kwargs):
            app.job.update(state="done", message="测试替身：验证由 sandbox 测试覆盖")
        app.validate = skip_validation
        item = app.store.items[0]
        ident = item['id']
        original = app.store.path(ident).read_text(encoding='utf-8')
        requests = []
        class Model:
            def request(self, state, prompt):
                requests.append(state)
                if 'flows' in state:
                    return {'action': 'edit', 'flow_id': ident}
                skill = copy.deepcopy(state['skill'])
                skill['params'] = []
                skill['actions'][0]['args'].pop('value_ref')
                skill['actions'][0]['args']['value'] = '人工智能'
                skill['description'] = '固定查询人工智能并读取结果。'
                return {'status': 'proposal', 'name': '固定查询', 'message': '去除查询参数，固定为人工智能。',
                        'defaults': {}, 'skill': skill}
        app.model = lambda *args, **kwargs: Model()
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(channel='msedge', headless=True)
            page = await browser.new_page()
            app.page = page
            await page.expose_binding('__flowStudio', app.command)
            await page.goto((ASSETS/'index.html').as_uri())
            await page.locator('#chatInput').fill('删除查询流程的查询参数，固定使用人工智能')
            await page.locator('#send').click()
            await page.get_by_role('button', name='确认修改', exact=True).wait_for()
            assert app.store.path(ident).read_text(encoding='utf-8') == original
            assert requests[1]['defaults'] == {'query': '人工智能'}
            await page.get_by_role('button', name='取消修改', exact=True).click()
            assert app.edit_draft is None
            assert app.store.path(ident).read_text(encoding='utf-8') == original
            await page.locator('#chatInput').fill('按刚才的要求修改流程')
            await page.locator('#send').click()
            await page.get_by_role('button', name='确认修改', exact=True).click()
            await page.get_by_text('流程已修改，正在后台验证与修复。验证结果将在对话中显示。', exact=True).wait_for()
            saved = Store(root).get(ident)
            assert saved['defaults'] == {} and saved['status'] == 'unverified'
            assert saved['description'] == '固定查询人工智能并读取结果。'
            assert saved['last_result'] is None
            assert metadata(app.store.path(ident).read_text(encoding='utf-8'))['actions'][0]['args']['value'] == '人工智能'
            # 修改后的真实脚本不再需要已删除的参数。
            app.job = {'logs': []}
            await app.execute(ident, {}, True, 'allow')
            assert app.job['result']['status'] == 'succeeded', app.job
            # 无效引用不能保存；方案不能覆盖后续手工修改，也不能重复应用。
            try:
                app.apply_edit('expired')
                raise AssertionError('旧方案不应生效')
            except ValueError:
                pass
            app.store.update(ident, {'definition': original, 'defaults': {'query': '人工智能'}})
            result = await app.chat('去掉查询参数')
            app.store.update(ident, {'name': '用户的新名称'})
            try:
                app.apply_edit(result['edit_id'])
                raise AssertionError('不应覆盖新版本')
            except ValueError:
                pass
            assert app.store.get(ident)['name'] == '用户的新名称'
            invalid = Model().request(requests[1], '')
            invalid['skill']['actions'][0]['args'] = {'target': {'id': 'query'}, 'value_ref': 'query'}
            try:
                proposal(invalid, original)
                raise AssertionError('未声明参数不应通过')
            except ValueError:
                pass
            class ClarifyModel:
                def request(self, state, prompt):
                    if 'flows' in state:
                        return {'action': 'edit', 'flow_id': ident}
                    return {'status': 'clarification', 'message': '请指定固定查询值。'}
            app.model = lambda *args, **kwargs: ClarifyModel()
            clarification = await app.chat('删除一个尚无默认值的参数')
            assert clarification['action'] == 'clarification' and app.edit_draft is None
            assert app.store.get(ident)['name'] == '用户的新名称'
            await browser.close()
        print('通过：聊天生成修改、取消、确认保存、默认值固定、脚本执行、过期方案和无效引用。')


if __name__ == '__main__':
    asyncio.run(main())
