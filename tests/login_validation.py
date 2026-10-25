"""登录双模式验证与凭据隔离。"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import ThreadingHTTPServer
from login import Handler, SECRET, definition, save
from browser_skill_agent.sandbox import validate_flow
class Model:
    usage={}
    def __init__(self):self.states=[]
    def decide(self,state):
        self.states.append(state)
        if len(self.states)==1:return {'tool':'read','args':{'target':{'id':'result'}}}
        return {'tool':'finish','args':{'status':'succeeded','message':'完成'}}
    def request(self,*args):raise AssertionError('不应需要修复')
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start()
try:
    Handler.posts=0
    with TemporaryDirectory() as d:
        root=Path(d);path=root/'SKILL.md';save(path,definition(f'http://127.0.0.1:{server.server_port}','/login'))
        model=Model()
        report=validate_flow(path,{'username':'tester','password':''},model,root/'validation',credentials={'password':SECRET},checks=[{'title':'登录后任务完成','kind':'read','args':{'target':{'id':'result'}},'equals':'任务完成'}])
        assert report['status']=='passed',report
        assert Handler.posts==2,Handler.posts
        assert SECRET not in json.dumps(model.states)
        for file in root.rglob('*'):
            if file.is_file() and file.suffix in ('.json','.md'):assert SECRET not in file.read_text(encoding='utf-8'),file
        print('通过：双模式独立登录、实际验收、密码未进入模型或验证文件。')
finally:server.shutdown();server.server_close()
