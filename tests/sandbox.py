"""隔离验证测试；--live 额外跑真实录制→真实模型生成→双模式验证。"""
import argparse
import asyncio
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread, Event

import httpx
import yaml
from dotenv import load_dotenv

from browser_skill_agent.sandbox import validate_flow
from browser_skill_agent.sandbox.checks import CONTRACT_PROMPT
from browser_skill_agent.sandbox.runner import REPAIR_PROMPT
from browser_skill_agent.generation.generator import generate
from browser_skill_agent.generation.model import GenerationModel

HTML = """<!doctype html><html lang="zh"><meta charset="utf-8"><title>沙箱验证练习</title>
<label>关键词<input id="query"></label><label for="category">分类</label><select id="category"><option>全部</option><option>教程</option></select>
<button id="search" onclick="document.querySelector('#result').textContent='加载中';setTimeout(()=>document.querySelector('#result').textContent='查询完成：'+document.querySelector('#query').value+' / '+document.querySelector('#category').value,300)">搜索</button>
<p id="result" role="status">尚未搜索</p><label>附件<input id="upload" type="file" onchange="setTimeout(()=>document.querySelector('#uploaded').textContent='文件已读取：'+this.files[0].name,200)"></label><p id="uploaded"></p>
<a download href="/download">下载结果</a></html>"""
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        if self.path == '/download':
            self.send_header('Content-Disposition','attachment; filename="result.txt"')
            body = '真实下载结果'.encode()
        else:
            self.send_header('Content-Type','text/html; charset=utf-8'); body=HTML.encode()
        self.end_headers();self.wfile.write(body)
    def log_message(self,*args): pass


def definition(url, broken=False, files=False):
    actions = [
        {'title':'填写关键词','tool':'fill','args':{'target':{'id':'wrong' if broken else 'query'},'value_ref':'query'}},
        {'title':'精确选择教程','tool':'select','args':{'target':{'label':'分类'},'label':'教程'}},
        {'title':'搜索并等待动态结果','tool':'click','args':{'target':{'role':'button','name':'搜索'},'wait_after':{'target':{'id':'result'},'state':'text','value':'查询完成：{{query}} / 教程'}}},
        {'title':'读取真实结果','tool':'read','args':{'target':{'id':'result'}}}]
    if files:
        actions += [{'title':'选择附件','tool':'upload','args':{'target':{'id':'upload'},'file_ids':['u1'],'wait_after':{'target':{'id':'uploaded'},'state':'text','value':'文件已读取：sample.txt'}}},
                    {'title':'下载结果','tool':'download','args':{'target':{'role':'link','name':'下载结果'}}}]
    skill={'name':'sandbox_demo','description':'查询教程并读取真实动态结果。','params':['query']+(['file'] if files else []),
           'start':url,'goal':'搜索 {{query}} 的教程，读取查询完成结果。'+('选择附件并下载结果。' if files else ''),
           'actions':actions,'stages':[{'goal':'完成查询','path':'填写关键词，分类选教程，搜索并等待状态包含查询完成，读取状态。',
                                    'evidence':'状态显示查询完成：{{query}} / 教程','observe_when':'读取结果后','interrupt_when':'操作失败或目标不唯一'}],
           'instructions':'通过 id=query 输入关键词、label=分类选择教程，点击搜索并等待 id=result 显示完整结果后读取。'}
    if files: skill['file_params']={'uploads':['file']}
    return skill


def save_skill(path, skill):
    skill=deepcopy(skill);body=skill.pop('instructions');path.write_text('---\n'+yaml.safe_dump(skill,allow_unicode=True,sort_keys=False)+'---\n'+body,encoding='utf-8')


def checks(files=False):
    items=[{'title':'实际查询结果','kind':'page','args':{'target':{'id':'result'},'state':'text','value':'查询完成：人工智能 / 教程','timeout':1}}]
    items.append({'title':'结果精确读取','kind':'read','args':{'target':{'id':'result'},'kind':'text'},'equals':'查询完成：人工智能 / 教程'})
    if files:
        items += [{'title':'文件实际读取','kind':'page','args':{'target':{'id':'uploaded'},'state':'text','value':'文件已读取：sample.txt','timeout':1}},
                  {'title':'下载完成','kind':'download','name':'result.txt','count':1,'min_bytes':1}]
    return items


class FakeModel:
    def __init__(self, files=False, early=False): self.files=files;self.early=early;self.call=0;self.usage={}
    def request(self, state, prompt):
        if prompt == CONTRACT_PROMPT: return {'coverage':{'complete':True,'missing':[]},'checks':checks(self.files),'message':'验证最终查询结果'}
        assert prompt == REPAIR_PROMPT
        skill=deepcopy(state['skill']);skill['actions'][0]['args']['target']={'id':'query'}
        return {'status':'proposal','message':'根据页面 id 修正错误定位','defaults':state['defaults'],'skill':skill}
    def decide(self, state):
        self.call+=1
        if self.files and (state.get('last_stage') or {}).get('skipped', 0) == 1:
            return {'tool':'download','args':{'target':{'role':'link','name':'下载结果'}}}
        if self.early or state.get('last_stage'):
            return {'tool':'finish','args':{'status':'succeeded','message':'已完成'}}
        actions=definition('',files=self.files)['actions']
        for action in actions:
            if action['tool']=='click':action['args']['wait_after']['value']='查询完成：人工智能 / 教程'
        return {'stage':'完成查询','success_criteria':'结果及文件符合目标','actions':actions}


async def record(root, url):
    from playwright.async_api import async_playwright
    from browser_skill_agent.recording.recorder import Recorder
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(channel='msedge',headless=True)
        context=await browser.new_context()
        rec=Recorder(context,root)
        control=await rec.open(url)
        await control.locator('#start').click()
        for _ in range(100):
            if rec.current and rec.owners:break
            await asyncio.sleep(.1)
        page=next(p for p,r in rec.owners.items() if r==rec.current)
        await page.wait_for_function('!!window.__bsaRecorderFlush')
        await page.get_by_label('关键词').fill('人工智能')
        await page.get_by_label('分类').select_option(label='教程')
        await page.get_by_role('button',name='搜索',exact=True).click()
        await page.get_by_role('status').filter(has_text='查询完成：人工智能 / 教程').wait_for()
        await page.wait_for_timeout(500)
        rec.current.session["status"] = "finishing"
        await rec.finish(rec.current)
        folder=rec.current.folder
        await rec.shutdown();await browser.close()
        return folder


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/'
    try:
        with TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'SKILL.md';params={'query':'人工智能'}
            save_skill(path,definition(url,broken=True));original=path.read_text(encoding='utf-8')
            result=validate_flow(path,params,FakeModel(),root/'runs',progress=print)
            assert result['status']=='passed',result
            assert len(result['attempts'])==3 and len(result['repairs'])==1
            assert path.read_text(encoding='utf-8')==original
            save_skill(path,definition(url))
            class MissingContract(FakeModel):
                def request(self,state,prompt):
                    if prompt == CONTRACT_PROMPT:
                        return {'coverage':{'complete':False,'missing':['结果缺少持久证据']},'checks':[]}
                    return super().request(state,prompt)
            trial=validate_flow(path,params,MissingContract(),root/'runs',max_repairs=0)
            assert trial['status']=='executed' and len(trial['attempts'])==1,trial
            assert trial['attempts'][0]['evidence']==[]
            result=validate_flow(path,params,FakeModel(early=True),root/'runs',checks=checks(),max_repairs=0)
            assert result['status']=='blocked' and result['attempts'][-1]['evidence'][0]['ok'] is False
            cancelled=Event();cancelled.set()
            cancelled_report=validate_flow(path,params,FakeModel(),root/'runs',checks=checks(),cancel=cancelled)
            assert cancelled_report['status']=='not_started' and not cancelled_report['attempts']
            sample=root/'sample.txt';sample.write_text('测试附件',encoding='utf-8')
            params['file']=str(sample);save_skill(path,definition(url,files=True))
            denied=validate_flow(path,params,FakeModel(files=True),root/'runs',checks=checks(True),allow_files=False)
            assert denied['status']=='blocked' and denied['file_calls']==0 and not denied['repairs']
            passed=validate_flow(path,params,FakeModel(files=True),root/'runs',checks=checks(True),allow_files=True)
            assert passed['status']=='passed' and passed['file_calls']==4,passed
            assert len(list(Path(passed['folder']).glob('revision-*/downloads/result.txt')))==2
            # 文件操作完成后的步骤失败，修复版仍有完整的脚本+LLM文件额度。
            broken=definition(url,files=True)
            broken['actions'].append({'tool':'wait_for','args':{'target':{'id':'missing'},'state':'visible','timeout':0.1}})
            save_skill(path,broken)
            class RepairAfterDownload(FakeModel):
                def request(self,state,prompt):
                    result=super().request(state,prompt)
                    if prompt == REPAIR_PROMPT:
                        result['skill']['actions'][-1]['args']={'target':{'id':'result'},'state':'visible','timeout':1}
                    return result
            repaired=validate_flow(path,params,RepairAfterDownload(files=True),root/'runs',checks=checks(True),max_repairs=1)
            assert repaired['status']=='passed' and repaired['file_calls']==6,repaired
            assert repaired['approval']=='allow' and repaired['allow_files'] is True
            save_skill(path,definition(url,files=True))
            bad=checks(True);bad[-1]['min_bytes']=999999
            limited=validate_flow(path,params,FakeModel(files=True),root/'runs',checks=bad,allow_files=True)
            assert limited['status']=='blocked' and limited['file_calls']<=4
            print('通过：动态页面、错误定位修复、双模式同版验收、虚假 finish 拒绝、文件隔离与预算。')
        if args.live:
            load_dotenv();config=[os.getenv(k) for k in ('MODEL_BASE_URL','MODEL_API_KEY','MODEL_NAME')]
            assert all(config),'缺少模型配置'
            root=Path('.cache/sandbox-live').resolve();root.mkdir(parents=True,exist_ok=True)
            recording=asyncio.run(record(root,url))
            with httpx.Client(timeout=60) as client:
                model=GenerationModel(client,*config,timeout=120,progress=print)
                destination,generated=generate(recording,model,root/'generated',guidance={'name':'动态教程查询','description':'输入关键词，分类选择教程，搜索并读取查询完成结果。','parameters':'关键词为 query 参数，默认人工智能；分类固定教程。'})
                params=json.loads((destination/'example_params.json').read_text(encoding='utf-8'))
                result=validate_flow(destination/'SKILL.md',params,model,root/'validations',checks=checks(),progress=print)
                write={'recording':str(recording),'generated':str(destination),'generation_usage':generated['usage'],
                       'validation':{k:result.get(k) for k in ('status','reason','folder','usage','elapsed_seconds')}}
                (root/'latest.json').write_text(json.dumps(write,ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps(write,ensure_ascii=False,indent=2),flush=True)
                assert result['status']=='passed',result['reason']
    finally:
        server.shutdown();server.server_close()


if __name__=='__main__':main()
