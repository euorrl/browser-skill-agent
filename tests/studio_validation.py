"""工作台自动验证：生成、保存默认参数、聊天修改都触发真实双模式浏览器重放。"""
import asyncio
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.async_api import async_playwright
from sandbox import HTML, definition, save_skill, checks, FakeModel
from browser_skill_agent.studio.app import Studio, ASSETS
import browser_skill_agent.studio.app as app_module
from browser_skill_agent.sandbox.checks import CONTRACT_PROMPT
from browser_skill_agent.studio.editing import EDIT_PROMPT


class Model(FakeModel):
    ident = None
    def request(self, state, prompt):
        if 'flows' in state:
            return {'action':'edit','flow_id':self.ident}
        if prompt == EDIT_PROMPT:
            return {'status':'proposal','name':state['name'],'defaults':{'query':'深度学习'},
                    'skill':state['skill'],'message':'将默认关键词修改为深度学习'}
        if prompt == CONTRACT_PROMPT:
            contract=checks();contract[0]['args']['value']='查询完成：'+state['skill']['params']['query']+' / 教程'
            contract[1]['equals']=contract[0]['args']['value']
            return {'coverage':{'complete':True,'missing':[]},'checks':contract,'message':'验证真实结果'}
        return super().request(state,prompt)
    def decide(self, state):
        result=super().decide(state)
        for action in result.get('actions',[]):
            if action['tool']=='click':action['args']['wait_after']['value']='查询完成：'+state['skill']['params']['query']+' / 教程'
        return result


async def main():
    with TemporaryDirectory() as temporary:
        root=Path(temporary);html=root/'page.html';html.write_text(HTML,encoding='utf-8')
        generated=root/'generated';generated.mkdir();save_skill(generated/'SKILL.md',definition(html.as_uri()))
        (generated/'example_params.json').write_text('{"query":"人工智能"}',encoding='utf-8')
        app=Studio(root);app.model=lambda *args,**kwargs: Model()
        original_generate=app_module.generate
        app_module.generate=lambda *args,**kwargs:(generated,{'usage':{}})
        try:
            app.launch('record',app.generate_flow(root/'recording','自动验证测试'))
            app.job['auto_validate']=True
            await app.worker
        finally:app_module.generate=original_generate
        assert app.job['state']=='done',app.job
        item=app.store.items[0];Model.ident=item['id']
        assert item['status']=='verified' and item['validation']['status']=='passed'
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(channel='msedge',headless=True)
            page=await browser.new_page();app.page=page
            await page.expose_binding('__flowStudio',app.command)
            await page.goto((ASSETS/'index.html').as_uri())
            await page.get_by_role('button',name='编辑自动验证测试').click()
            await page.locator('#editParams input').fill('机器学习')
            await page.get_by_role('button',name='保存修改',exact=True).click()
            await app.worker
            assert app.store.get(item['id'])['status']=='verified',app.job
            assert app.store.get(item['id'])['defaults']=={'query':'机器学习'}
            old_report=app.store.get(item['id'])['validation']['folder']
            source={'page':page,'frame':page.main_frame}
            await app.command(source,'update',{'id':item['id'],'name':'改名不重跑'})
            assert app.store.get(item['id'])['validation']['folder']==old_report
            # 对话确认默认参数修改后必须启动验证，并产生新的报告。
            result=await app.chat('把改名不重跑流程的默认关键词改成深度学习')
            await app.command(source,'apply_edit',{'edit_id':result['edit_id']})
            await app.worker
            assert app.store.get(item['id'])['status']=='verified',app.job
            assert app.store.get(item['id'])['defaults']=={'query':'深度学习'}
            assert app.store.get(item['id'])['validation']['folder']!=old_report
            await page.evaluate('refresh()')
            await page.locator('.badge.verified').first.wait_for()
            await page.screenshot(path='.cache/studio-validation.png')
            await browser.close()
        print('通过：创建后自动验证、参数修改后自动验证、聊天修改后自动验证、改名不重复执行。')


if __name__=='__main__':asyncio.run(main())
