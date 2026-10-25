"""验收格式纠正必须有界，不能把未执行误报为流程失败。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from browser_skill_agent.sandbox.checks import prepare_contract
from browser_skill_agent.sandbox import validate_flow
from sandbox import definition, save_skill

GOOD={'checks':[{'title':'选中标记','kind':'read','args':{'target':{'id':'choice'},'kind':'attribute','attribute':'aria-selected'},'equals':'true'}]}
BAD={'checks':[{'title':'选中标记','kind':'read','args':{'target':{'id':'choice'},'kind':'attribute','attribute':'aria-selected'}}]}
class Model:
    usage={}
    def __init__(self, responses):self.responses=iter(responses);self.calls=[]
    def request(self,state,prompt):self.calls.append(state);return next(self.responses)

class Tests(unittest.TestCase):
    def test_correct_once(self):
        model=Model([BAD,GOOD]);records=[]
        checks,_=prepare_contract(model,{'skill':{}},records,lambda text:None)
        self.assertEqual(checks,GOOD['checks']);self.assertEqual(len(records),2)
        self.assertEqual(records[0]['response'],BAD)
        self.assertIn('equals',model.calls[1]['format_error'])
    def test_no_invented_evidence(self):
        model=Model([{'checks':[],'message':'缺少持久的画质状态'}])
        with self.assertRaisesRegex(RuntimeError,'持久'):
            prepare_contract(model,{},[],lambda text:None)
        self.assertEqual(len(model.calls),1)
    def test_two_invalid_responses_never_launch_browser(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'SKILL.md';save_skill(source,definition('https://example.com'))
            with patch('browser_skill_agent.sandbox.runner.sync_playwright') as browser:
                result=validate_flow(source,{'query':'人工智能'},Model([BAD,BAD]),root/'reports')
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
