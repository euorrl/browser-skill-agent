"""全文/摘要消歧、生成证据约束及伪 PDF 拒绝。"""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright
from browser_skill_agent.tools import BrowserTools
from browser_skill_agent.tools.files import verify_download_content
from browser_skill_agent.generation.generator import validate_recording_alignment, ground_recorded_targets

class Tests(unittest.TestCase):
 def test_recorded_identity_cannot_be_shortened_or_selected_by_index(self):
  state={'actions':[{'id':'a1','target':{'role':'link','name':'公司：2026年半年度报告'}}]}
  result={'skill':{'actions':[{'tool':'click','args':{'target':{'role':'link','has_text':'2026年半年度报告','nth':0}}}]},'example_params':{},'evidence_map':[{'action_index':1,'source_actions':['a1']}]}
  with self.assertRaisesRegex(ValueError,'截短'):validate_recording_alignment(result,state)
  result['skill']['actions'][0]['args']['target']={'role':'link','has_text':'公司：2026年半年度报告','has_text_exact':True}
  validate_recording_alignment(result,state)
 def test_recorded_dom_name_is_grounded_for_actions_and_llm(self):
  state={'actions':[{'id':'a1','target':{'role':'button','name':'下载报告','label':''}}]}
  result={'skill':{'instructions':'下载文件','actions':[{'tool':'download','args':{'target':{'role':'button','name':'{{button}}'}}}]},'example_params':{'button':'下载报告'}}
  ground_recorded_targets(result,state)
  target=result['skill']['actions'][0]['args']['target']
  self.assertEqual(target,{'role':'button','has_text':'{{button}}','has_text_exact':True})
  self.assertIn('has_text_exact',result['skill']['instructions'])
  self.assertEqual(len(result['grounding_changes']),1)
 def test_bare_list_wait_uses_unique_recorded_option(self):
  state={'actions':[{'id':'a1','target':{'role':'option','name':'600519 A股 贵州茅台','label':''}}]}
  result={'skill':{'instructions':'查询','actions':[{'tool':'wait_for','args':{'target':{'role':'option'},'state':'visible'}}]},'example_params':{}}
  ground_recorded_targets(result,state)
  self.assertEqual(result['skill']['actions'][0]['args']['target'],{'role':'option','has_text':'600519 A股 贵州茅台','has_text_exact':True})
 def test_download_button_recovery_is_not_completion(self):
  target={'role':'button','has_text':'下载'}
  result={'skill':{'actions':[{'tool':'download','args':{'target':target}},{'tool':'wait_for','args':{'target':target,'state':'enabled'}}]},'example_params':{},'evidence_map':[]}
  with self.assertRaisesRegex(ValueError,'保存完成'):validate_recording_alignment(result,{'actions':[]})
 def test_link_context_is_not_mistaken_for_recorded_full_title(self):
  state={'actions':[{'id':'a1','target':{'role':'link','name':'播放量123'}}]}
  result={'skill':{'actions':[{'tool':'click','args':{'target':{'role':'link','has_text':'BVexample'}}}]},'example_params':{},'evidence_map':[{'action_index':1,'source_actions':['a1']}]}
  validate_recording_alignment(result,state)
 def test_icon_click_records_enclosing_control(self):
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True)
   page=browser.new_page(); events=[]
   page.expose_function('__bsaRecorderReady',lambda: {'id':'test'})
   page.expose_function('__bsaRecord',lambda event: events.append(event))
   page.set_content('<span title="点赞" style="cursor:pointer"><svg width="40" height="40"><path d="M0 0H40V40H0Z" /></svg></span>')
   page.evaluate(Path('src/browser_skill_agent/recording/browser.js').read_text(encoding='utf-8'))
   page.wait_for_function('!!window.__bsaRecorderFlush')
   page.locator('path').click()
   page.evaluate('window.__bsaRecorderFlush(true)')
   clicks=[e for e in events if e.get('type')=='click']
   self.assertTrue(clicks, events)
   self.assertIn({'title':'点赞'},clicks[0]['target']['candidates'])
   self.assertEqual(BrowserTools(page).target({'title':'点赞'}).count(),1)
   browser.close()
 def test_press_switches_to_popup(self):
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True)
   page=browser.new_page()
   page.set_content("<input aria-label='搜索' onkeydown=\"if(event.key==='Enter')window.open('about:blank')\">")
   tools=BrowserTools(page)
   result=tools.execute('press',{'target':{'label':'搜索'},'key':'Enter','expect_popup':True})
   self.assertTrue(result['ok'],result)
   self.assertNotEqual(tools.page,page)
   self.assertEqual(len(page.context.pages),2)
   browser.close()
 def test_fake_pdf_is_rejected(self):
  with TemporaryDirectory() as temp:
   path=Path(temp)/'report.pdf';path.write_bytes(b'<!DOCTYPE html><h1>error</h1>')
   with self.assertRaisesRegex(ValueError,'PDF'):verify_download_content(path)
   path.write_bytes(b'%PDF-1.7\nfixture');verify_download_content(path)
 def test_exact_dom_text_ignores_icon_but_excludes_summary(self):
  with sync_playwright() as pw:
   browser=pw.chromium.launch(channel='msedge',headless=True)
   page=browser.new_page();page.set_content('<style>a::before{content:"\\e633"}</style><a href="#full">公司：2026年半年度报告</a><a href="#summary">公司：2026年半年度报告摘要</a>')
   tools=BrowserTools(page)
   target={'role':'link','has_text':'公司：2026年半年度报告','has_text_exact':True}
   self.assertEqual(tools.target(target).count(),1)
   self.assertEqual(tools.target(target).get_attribute('href'),'#full')
   browser.close()
if __name__=='__main__':unittest.main()
