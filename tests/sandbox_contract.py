"""验收格式纠正必须有界，不能把未执行误报为流程失败。"""
import tempfile
from copy import deepcopy
import unittest
from pathlib import Path
from unittest.mock import patch
from browser_skill_agent.sandbox.checks import prepare_contract, normalize_checks, validate_checks
from browser_skill_agent.sandbox import validate_flow
from sandbox import definition, save_skill

GOOD={'coverage':{'complete':True,'missing':[]},'checks':[{'title':'选中标记','kind':'read','args':{'target':{'id':'choice'},'kind':'attribute','attribute':'aria-selected'},'equals':'true'}]}
BAD={'coverage':{'complete':True,'missing':[]},'checks':[{'title':'选中标记','kind':'read','args':{'target':{'id':'choice'},'kind':'attribute','attribute':'aria-selected'}}]}
class Model:
    usage={}
    def __init__(self, responses):self.responses=iter(responses);self.calls=[]
    def request(self,state,prompt):self.calls.append(state);return next(self.responses)

class Tests(unittest.TestCase):
    def test_equivalent_read_expressions(self):
        raw=[{'title':'可见','kind':'read','args':{'target':{'id':'player'},'kind':'state'},'equals':'visible'},
             {'title':'正文','kind':'read','args':{'target':{'id':'title'},'kind':'text','max_chars':200},'contains':'目标标题'}]
        original=deepcopy(raw)
        checks=validate_checks(normalize_checks(raw))
        self.assertEqual(raw,original)
        self.assertEqual(checks[0]['args']['state'],'visible')
        self.assertEqual(checks[1]['args']['value'],'目标标题')
    def test_partial_success_never_becomes_contract(self):
        response=deepcopy(GOOD)
        response['coverage']={'complete':False,'missing':['无法确认复制成功']}
        model=Model([response])
        with self.assertRaisesRegex(RuntimeError,'无法确认复制成功'):
            prepare_contract(model,{},[],lambda text:None)
        self.assertEqual(len(model.calls),1)
    def test_correct_once(self):
        model=Model([BAD,GOOD]);records=[]
        checks,_=prepare_contract(model,{'skill':{}},records,lambda text:None)
        self.assertEqual(checks,GOOD['checks']);self.assertEqual(len(records),2)
        self.assertEqual(records[0]['response'],BAD)
        self.assertIn('equals',model.calls[1]['format_error'])
    def test_no_invented_evidence(self):
        model=Model([{'coverage':{'complete':False,'missing':['持久的画质状态']},'checks':[],'message':'缺少持久的画质状态'}])
        with self.assertRaisesRegex(RuntimeError,'持久'):
            prepare_contract(model,{},[],lambda text:None)
        self.assertEqual(len(model.calls),1)
    def test_two_invalid_responses_never_launch_browser(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'SKILL.md';save_skill(source,definition('https://example.com'))
            with patch('browser_skill_agent.sandbox.runner.sync_playwright') as browser:
                result=validate_flow(source,{'query':'人工智能'},Model([BAD,BAD]),root/'reports',trial_on_contract_failure=False)
                browser.assert_not_called()
            self.assertEqual(result['status'],'not_started')
            self.assertEqual(result['attempts'],[])
            self.assertEqual(len(result['contract_attempts']),2)
            self.assertTrue((Path(result['folder'])/'report.json').exists())
    def test_supplied_invalid_contract_does_not_call_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'SKILL.md';save_skill(source,definition('https://example.com'))
            model=Model([])
            result=validate_flow(source,{'query':'人工智能'},model,root/'reports',checks=BAD['checks'])
            self.assertEqual(result['status'],'not_started');self.assertEqual(model.calls,[])

if __name__=='__main__':unittest.main()
