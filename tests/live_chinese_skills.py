"""显式运行的中文网站在线验证；LLM 模式会请求 .env 配置的真实模型。"""
import argparse,hashlib,json,os,struct,time,traceback
from datetime import datetime,timezone,timedelta
from urllib.parse import unquote
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
import httpx
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from browser_skill_agent.skill import load_skill
from browser_skill_agent.runtime import Model,run,run_script
from browser_skill_agent.tools import BrowserTools
from browser_skill_agent.tools.files import FileOptions
from browser_skill_agent.approval import ApprovalPolicy

ROOT=Path(__file__).resolve().parents[1]
SAMPLE_HASHES={'sample-a.png': '110b3fbd8f1f9082358fd93a9c91d2134d245891ee17e8d8f830698c688489f9', 'sample-b.png': '97bf22a39f3ef119933dc7d83f8947b7fd4d1a6043972024608001f2759404a1'}
CASES={
 'chinese_encyclopedia_research':{'topic_a':'人工智能','topic_b':'机器学习'},
 'element_cn_tabs':{},
 'element_cn_collapse':{},
 'element_cn_dialog':{},
 'element_cn_tree':{},
 'element_cn_pagination':{},
 'vue_cn_navigation':{},
 'bejson_timestamp_precision':{},
 'element_cn_remote_select':{'query':'al','choice':'Alabama'},
 'chinese_image_file_pipeline':{'file_a':'sample-a.png','file_b':'sample-b.png'},
}
class RecordedModel(Model):
 """仅保存决策与耗时，不记录 API 密钥或完整请求上下文。"""
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.records=[]
 def decide(self,state):
  started=time.monotonic();record={'call':len(self.records)+1,'steps_left':state['steps_left'],'previous_stage':state.get('last_stage')}
  try:
   decision=super().decide(state);record['decision']=decision;return decision
  except Exception as exc:
   record['error']=f'{type(exc).__name__}: {exc}';raise
  finally:
   record['elapsed_seconds']=round(time.monotonic()-started,2);self.records.append(record)

class RecordedTools(BrowserTools):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.records=[]
 def execute(self,name,args):
  result=super().execute(name,args)
  self.records.append({'tool':name,'args':args,'result':result,'url':self.page.url})
  return result

def verify(name,tools):
 good=[r for r in tools.records if r['result'].get('ok')]
 reads=[r for r in good if r['tool']=='read']
 if name=='chinese_encyclopedia_research':
  sources=[]
  for topic in ['人工智能','机器学习']:
   article=[r for r in reads if unquote(r['url']).split('?')[0].endswith('/wiki/'+topic) and r['args'].get('target',{}).get('id')=='mw-content-text' and len(str(r['result'].get('data','')))>=100]
   assert article,f'缺少 {topic} 实际条目正文读取，搜索摘要不能替代'
   headings=[{'url':page.url,'title':page.locator('#firstHeading .mw-page-title-main').inner_text().strip()} for page in tools.page.context.pages if '/wiki/' in page.url]
   assert any(item['title']==topic for item in headings),f'缺少 {topic} 对应条目标签页：{headings}'
   sources.append(article[-1]['url'])
  for topic in ['人工智能','机器学习']:
   assert any(r['tool']=='fill' and r['args'].get('value')==topic for r in good),f'未实际搜索 {topic}'
  return {'topics':['人工智能','机器学习'],'sources':sources,'article_reads_checked':True}
 if name in {'element_cn_tabs' ,'element_cn_collapse','element_cn_dialog','element_cn_tree','element_cn_pagination'}:
  example=tools.page.locator('.example-showcase').first
  def read_has(value,attribute=None):
   return any(r['result'].get('data')==value and (attribute is None or r['args'].get('attribute')==attribute) for r in reads)
  if name=='element_cn_tabs':
   for label in ['Config','Task','User']:
    assert read_has(label),f'缺少实际面板读取：{label}'
    assert any(r['args'].get('target',{}).get('name')==label and r['args'].get('attribute')=='aria-selected' and r['result'].get('data')=='true' for r in reads),f'缺少选中状态：{label}'
   assert example.get_by_role('tab',name='User',exact=True).get_attribute('aria-selected')=='true'
  elif name=='element_cn_collapse':
   for word in ['Operation feedback','Simplify the process']:
    assert any(word in str(r['result'].get('data')) for r in reads),word
   for label,value in [('Feedback','false'),('Efficiency','true')]:
    assert example.get_by_role('button',name=label,exact=True).get_attribute('aria-expanded')==value
    assert any(r['args'].get('target',{}).get('name')==label and r['args'].get('attribute')=='aria-expanded' and r['result'].get('data')==value for r in reads)
  elif name=='element_cn_dialog':
   assert sum('This is a message' in str(r['result'].get('data')) for r in reads)>=2,'缺少两次弹窗内容读取'
   for label in ['Cancel','Confirm']:
    assert any(r['tool']=='click' and r['args'].get('target',{}).get('name')==label and r['result'].get('after_wait',{}).get('ok') for r in good),label
   assert sum(r['args'].get('kind')=='count' and r['result'].get('data')==0 for r in reads)>=2
   assert tools.page.get_by_role('dialog',name='Tips').count()==0
  elif name=='element_cn_tree':
   assert sum(r['result'].get('data')=='Level three 1-1-1' for r in reads)>=2
   assert read_has(0),'缺少折叠后可见数量0的读取'
   assert example.get_by_text('Level three 1-1-1',exact=True).is_visible()
   assert sum(r['tool']=='click' and r['args'].get('target',{}).get('text')=='Level one 1' for r in good)>=3
  else:
   pages=[r['args'].get('target',{}).get('name') for r in reads if r['args'].get('attribute')=='aria-current' and r['result'].get('data')=='true']
   assert pages==['page 3','page 4','page 3','page 1'],pages
   assert example.get_by_role('button',name='Go to previous page').first.is_disabled()
   assert read_has('','disabled'),'缺少读取禁用属性'
  return {'component':name,'actual_reads_checked':len(reads),'final_dom_checked':True}
 if name=='vue_cn_navigation':
  assert any(r['result'].get('data')=='Count is: 1' for r in reads),'缺少实际计数按钮读取'
  assert any('/guide/quick-start' in r['url'] and '快速上手' in str(r['result'].get('data')) for r in reads),'未读取快速上手'
  assert any('/reactivity-fundamentals' in r['url'] and '响应式基础' in str(r['result'].get('data')) for r in reads),'未读取响应式基础'
  assert sum(r['tool']=='back' for r in good)>=2,'未实际执行两次返回'
  assert '/guide/introduction' in tools.page.url,'最终未返回简介'
  return {'counter':'Count is: 1','returned':2,'final_url':tools.page.url}
 if name=='bejson_timestamp_precision':
  values=[r['result'].get('data') for r in reads]
  required=['1970-01-01 08:00:00','1704067200123','2024-01-01 08:00:00 123']
  assert all(value in values for value in required),values
  assert any(r['args'].get('wait_after',{}).get('target',{}).get('id')=='msecond' and r['args']['wait_after'].get('state')=='visible' and r['result'].get('after_wait',{}).get('ok') for r in good),'缺少毫秒字段出现的等待证据'
  assert any(r['tool']=='fill' and r['args'].get('target',{}).get('id')=='msecond' and r['args'].get('value')=='123' for r in good),'缺少毫秒字段成功填写证据'
  return {'read_values':required,'millisecond_field_observed_and_filled':True}
 if name=='element_cn_remote_select':
  assert any(r['args'].get('attribute')=='aria-selected' and r['result'].get('data')=='true' for r in reads),'缺少选中属性 true 的实际读取'
  assert tools.page.get_by_role('option',name='label:Alabama',exact=True).get_attribute('aria-selected')=='true'
  return {'selected':'label:Alabama','aria_selected':'true'}
 downloads=[r['result']['data'] for r in good if r['tool']=='download']
 assert len(downloads)==4,f'应有四个下载，实际 {len(downloads)}'
 outputs=[]
 for index,item in enumerate(downloads):
  p=Path(item['path']);raw=p.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n','下载不是 PNG'
  size=struct.unpack('!II',raw[16:24]);assert size==[(96,64),(80,120),(96,64),(80,120)][index],size
  outputs.append({'name':p.name,'bytes':len(raw),'dimensions':size})
 assert len([r for r in good if r['tool']=='upload'])>=3,'未分别选择两份文件并批量选择'
 return {'downloads':outputs,'processing_complete':tools.page.locator('#error-message').inner_text()}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--skill',choices=CASES,required=True)
 parser.add_argument('--mode',choices=['script','llm'],required=True)
 parser.add_argument('--report-root',type=Path,default=ROOT/'.cache'/'live-validation',help='本次评测报告目录')
 args=parser.parse_args();os.chdir(ROOT);load_dotenv(ROOT/'.env')
 stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d-%H%M%S')
 folder=args.report_root/f'{args.skill}-{args.mode}-{stamp}';folder.mkdir(parents=True)
 params=dict(CASES[args.skill]);params['save_dir']=str(ROOT/'files'/'downloads'/'validation'/folder.name)
 result={};model=None;tools=None;started=time.monotonic();verified=False;error=None
 with (folder/'progress.log').open('w',encoding='utf-8') as log,redirect_stderr(log),redirect_stdout(log):
  try:
   if args.skill=='chinese_image_file_pipeline':
    for filename,expected in SAMPLE_HASHES.items():
     actual=hashlib.sha256((ROOT/'files'/'uploads'/filename).read_bytes()).hexdigest()
     if actual!=expected:raise ValueError(f'测试文件不符合生成样本，停止上传：{filename}')
   skill=load_skill(str(ROOT/'skills'/args.skill/'SKILL.md'),params)
   with sync_playwright() as pw,httpx.Client(timeout=120) as client:
    browser=pw.chromium.launch(channel='msedge',headless=True)
    try:
     context=browser.new_context()
     page=context.new_page()
     tools=RecordedTools(page,approval=ApprovalPolicy('allow',skill),file_options=FileOptions.from_skill(skill))
     if args.mode=='llm':
      names=['MODEL_BASE_URL','MODEL_API_KEY','MODEL_NAME']
      if any(not os.environ.get(n) for n in names):raise ValueError('缺少模型配置，不打印密钥')
      model=RecordedModel(client,*(os.environ[n] for n in names))
      result=run(skill,tools,model,max_steps=30)
     else:result=run_script(skill,tools,max_steps=30)
     if result.get('status')=='succeeded':
      result['verification']=verify(args.skill,tools);verified=True
     else:error='运行未成功结束'
    finally:browser.close()
  except Exception as exc:
   error=f'{type(exc).__name__}: {exc}';traceback.print_exc()
 report={'skill':args.skill,'mode':args.mode,'approval':'allow','tested_at':stamp,'elapsed_seconds':round(time.monotonic()-started,1),'verified':verified,'error':error,'result':result,'usage':dict(model.usage) if model else None}
 report.update({'model':os.environ.get('MODEL_NAME') if model else None,
                'skill_sha256':hashlib.sha256((ROOT/'skills'/args.skill/'SKILL.md').read_bytes()).hexdigest(),
                'runtime_sha256':hashlib.sha256((ROOT/'src/browser_skill_agent/runtime.py').read_bytes()).hexdigest(),
                'llm_seconds':round(sum(r['elapsed_seconds'] for r in model.records),2) if model else 0,
                'recorded_actions':len(tools.records) if tools else 0})
 (folder/'stages.json').write_text(json.dumps(model.records if model else [],ensure_ascii=False,indent=2),encoding='utf-8')
 (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 (folder/'trace.json').write_text(json.dumps(tools.records if tools else [],ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'report':str(folder/'report.json'),**report},ensure_ascii=False),flush=True)
 return 0 if verified else 1
if __name__=='__main__':raise SystemExit(main())
