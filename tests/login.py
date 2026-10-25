"""真实本地浏览器登录：凭据隔离、中途登录、人工 MFA、取消和不重复提交。"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs
import unittest
import yaml
from playwright.sync_api import sync_playwright

from browser_skill_agent.login import LoginHandler, MASK
from browser_skill_agent.skill import load_skill
from browser_skill_agent.runtime import run_script, run
from browser_skill_agent.tools import BrowserTools
from browser_skill_agent.output import capture_progress
from browser_skill_agent.browser_display import ResultOnlyDisplay, RESULT_ONLY_ARGS
from browser_skill_agent.sandbox import validate_flow
from browser_skill_agent.studio.store import Store
from browser_skill_agent.generation.generator import validate
from generation import draft

SECRET='test-only-password-73!'
class Handler(BaseHTTPRequestHandler):
    posts=0
    visits=0
    def do_GET(self):
        if self.path.startswith('/favicon'):
            self.send_response(204);self.end_headers();return
        if self.path.startswith('/start'):
            body='<button onclick="location.href=\'/login\'">打开后台</button>'
        elif self.path.startswith('/inside'):
            body='<h1>工作台</h1><p id="result">任务完成</p><input type="password" hidden value="'+SECRET+'">'
        else:
            Handler.visits+=1
            body='<h1>用户登录</h1><form method="post" action="/auth"><label>账号<input id="username" name="username"></label><label>密码<input id="password" name="password" type="password"></label>'
            if 'mfa' in self.path:body+='<label>验证码<input autocomplete="one-time-code" name="otp"></label>'
            body+='<button>登录</button></form>'
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body.encode())
    def do_POST(self):
        Handler.posts+=1
        values=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
        self.send_response(303)
        self.send_header('Location','/inside' if values.get('password')==[SECRET] else '/mfa')
        self.end_headers()
    def log_message(self,*args):pass


def definition(origin, start='/start'):
    return {'name':'login_demo','description':'在中途登录后读取任务结果','start':origin+start,'goal':'读取任务完成结果',
            'params':['username','password'],'login':{'origins':[origin],'username_param':'username','password_param':'password',
            'username_target':{'label':'账号'},'password_target':{'label':'密码'},'submit_target':{'role':'button','name':'登录'},
            'detect':{'label':'密码'},'success':{'target':{'id':'result'},'state':'text','value':'任务完成'}},
            'actions':([{'tool':'click','args':{'target':{'role':'button','name':'打开后台'},'wait_after':{'target':{'id':'result'},'state':'visible','timeout':.1}}}] if start=='/start' else [])+
                      [{'tool':'read','args':{'target':{'id':'result'}}}],
            'stages':[]}


def save(path, meta):path.write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False)+'---\n读取任务完成结果。',encoding='utf-8')


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.origin=f'http://127.0.0.1:{cls.server.server_port}'
        cls.pw=sync_playwright().start()
    @classmethod
    def tearDownClass(cls):cls.pw.stop();cls.server.shutdown();cls.server.server_close()
    def setUp(self):
        Handler.posts=Handler.visits=0
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path=self.root/'SKILL.md';save(self.path,definition(self.origin))
        self.params={'username':'tester','password':SECRET}
    def browser(self, headed=False):
        b=self.pw.chromium.launch(channel='msedge',headless=not headed,args=RESULT_ONLY_ARGS if headed else [])
        self.addCleanup(b.close);c=b.new_context();page=c.new_page();return c,page
    def test_mid_flow_auto_login_no_secret_in_model_logs_or_result(self):
        c,page=self.browser();skill=load_skill(str(self.path),self.params)
        self.assertEqual(skill['params']['password'],MASK)
        tools=BrowserTools(page);tools.session.login_handler=LoginHandler(tools,skill,self.params)
        logs=[]
        with capture_progress(logs.append):result=run_script(skill,tools)
        self.assertEqual(result['status'],'succeeded',result)
        self.assertEqual(Handler.posts,1);self.assertEqual(Handler.visits,1)
        self.assertNotIn(SECRET,json.dumps([skill,logs,result,tools.observe()]))
        # 直接定位密码字段也不能读取（包括隐藏的历史表单）。
        page.set_content('<input id="pwd" type="password" value="'+SECRET+'">')
        bare=BrowserTools(page);self.assertFalse(bare.execute('read',{'target':{'id':'pwd'},'kind':'value'})['ok'])
    def test_wrong_origin_never_autofills(self):
        c,page=self.browser();skill=load_skill(str(self.path),self.params);skill['login']['origins']=['https://other.example']
        tools=BrowserTools(page);calls=[]
        def manual(message,details):
            calls.append(details);self.assertEqual(page.locator('#password').input_value(),'')
            page.get_by_label('账号').fill('manual');page.get_by_label('密码').fill(SECRET);page.get_by_role('button',name='登录').click();return True
        tools.session.login_handler=LoginHandler(tools,skill,self.params,manual)
        result=run_script(skill,tools)
        self.assertEqual(result['status'],'succeeded');self.assertEqual(len(calls),1);self.assertEqual(Handler.posts,1)
    def test_mfa_shows_same_browser_then_hides(self):
        save(self.path,definition(self.origin,'/mfa'));skill=load_skill(str(self.path),self.params)
        c,page=self.browser(True);display=ResultOnlyDisplay(c);tools=BrowserTools(page);seen=[]
        def manual(message,details):
            seen.append(True);self.assertFalse(display.hidden);self.assertEqual(page.locator('#password').input_value(),'')
            page.get_by_label('密码').fill(SECRET);page.get_by_label('验证码').fill('123456');page.get_by_role('button',name='登录').click();return True
        tools.session.login_handler=LoginHandler(tools,skill,self.params,manual,display)
        result=run_script(skill,tools);self.assertEqual(result['status'],'succeeded',result)
        self.assertTrue(display.hidden);self.assertEqual(len(seen),1);self.assertEqual(Handler.posts,1)
    def test_failed_password_only_attempted_once_then_manual(self):
        c,page=self.browser();skill=load_skill(str(self.path),self.params);tools=BrowserTools(page);calls=[]
        def manual(message,details):calls.append(True);return False
        tools.session.login_handler=LoginHandler(tools,skill,{**self.params,'password':'wrong'},manual)
        result=run_script(skill,tools);self.assertEqual(result['status'],'blocked')
        self.assertEqual(Handler.posts,1);self.assertEqual(len(calls),1)
    def test_pdf_and_extension_frames_are_not_queried_for_login(self):
        from types import SimpleNamespace
        frames=[SimpleNamespace(url=url) for url in ('https://example.com/detail', 'https://example.com/report.PDF#page=1', 'about:blank', 'chrome-extension://pdf/viewer.html')]
        handler=LoginHandler(SimpleNamespace(page=SimpleNamespace(frames=frames)), {})
        self.assertEqual(handler.html_frames(), frames[:1])

    def test_password_demo_is_not_mistaken_for_login(self):
        c,page=self.browser();page.set_content('<h1>密码输入组件说明</h1><input type="password">')
        tools=BrowserTools(page);handler=LoginHandler(tools,{})
        self.assertFalse(handler.needed())

    def test_store_and_generation_do_not_persist_password(self):
        folder=self.root/'skills/demo';folder.mkdir(parents=True);save(folder/'SKILL.md',definition(self.origin))
        (folder/'example_params.json').write_text(json.dumps(self.params),encoding='utf-8')
        store=Store(self.root);item=store.items[0];self.assertEqual(item['secret_params'],['password'])
        store.update(item['id'],{'defaults':self.params})
        for p in [store.index,folder/'example_params.json',folder/'SKILL.md']:
            self.assertNotIn(SECRET,p.read_text(encoding='utf-8'))
        result=draft();result['skill']['params']=['username','password'];result['skill']['login']=definition(self.origin)['login'];result['skill']['actions']=[{'tool':'login','args':{}}]
        result['skill']['goal']='登录后读取结果';result['skill']['instructions']='调用 login 后读取结果。';result['example_params']=self.params.copy();result['evidence_map']=[]
        validate(result);self.assertEqual(result['example_params']['password'],'')
    def test_llm_never_receives_password(self):
        c,page=self.browser();skill=load_skill(str(self.path),self.params);tools=BrowserTools(page);tools.session.login_handler=LoginHandler(tools,skill,self.params)
        states=[]
        class Model:
            def decide(model,state):
                states.append(state)
                return {'actions':definition(self.origin)['actions']} if len(states)==1 else {'tool':'finish','args':{'status':'succeeded','message':'已完成'}}
        result=run(skill,tools,Model());self.assertEqual(result['status'],'succeeded')
        self.assertNotIn(SECRET,json.dumps(states))

if __name__=='__main__':unittest.main()
