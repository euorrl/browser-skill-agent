import json
from pathlib import Path
from tempfile import TemporaryDirectory


import httpx
from playwright.sync_api import sync_playwright
from browser_skill_agent.skill import load_skill
from browser_skill_agent.runtime import Model, run
from browser_skill_agent.tools import BrowserTools

root = Path(__file__).resolve().parents[1]
# 正式 Skill 均应保留能力描述，且能绑定任务参数。
for name, params in [
    ('chinese_encyclopedia_research', dict(topic_a='人工智能', topic_b='机器学习')),
    ('element_cn_remote_select', dict(query='al', choice='Alabama')),
    ('chinese_image_file_pipeline', dict(file_a='sample-a.png', file_b='sample-b.png')),
]:
    path = str(root / 'skills' / name / 'SKILL.md')
    loaded = load_skill(path, params)
    assert loaded['description'] and loaded['instructions']
    assert '{{' not in json.dumps(loaded, ensure_ascii=False)
    try:
        load_skill(path, {})
        raise AssertionError('缺少参数时未按预期报错')
    except ValueError:
        pass

# 临时任务仅供执行循环测试，不作为对外发布的 Skill。
with TemporaryDirectory() as directory:
    path = Path(directory) / 'SKILL.md'
    path.write_text('---\nname: search_test\nparams: [query]\ngoal: "搜索 {{query}}"\n---\n提交后读取结果。', encoding='utf-8')
    skill = load_skill(str(path), {'query': '009527'})
assert '009527' in skill['goal']
html = '''<meta charset="utf-8">
<label>备注<input value="保留"></label>
<label>关键词<input id="query" placeholder="搜索内容"></label>
<button onclick="document.querySelector('[role=status]').textContent='搜索结果：'+document.querySelector('#query').value">搜索</button>
<p role="status"></p>'''

requests = []
def respond(request):
    body = json.loads(request.content)
    assert request.url.path == '/v1/chat/completions'
    assert body['response_format'] == {'type': 'json_object'}
    state = json.loads(body['messages'][1]['content'])
    requests.append(state)
    text = state['page']['text']
    if len(requests) == 1:
        action = {'tool': 'not_registered', 'args': {}}
    elif '搜索结果：009527' in text:
        action = {'tool': 'finish', 'args': {'status': 'succeeded', 'message': '测试完成'}}
    elif '009527' in text:
        action = {'tool': 'click', 'args': {'target': {'role': 'button', 'name': '搜索'}}}
    else:
        action = {'tool': 'fill', 'args': {'target': {'role': 'textbox', 'name': '关键词'}, 'value_ref': 'query'}}
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(action)}}]})

with httpx.Client(transport=httpx.MockTransport(respond)) as client, sync_playwright() as pw:
    browser = pw.chromium.launch(channel='msedge', headless=True)
    try:
        page = browser.new_page()
        page.set_content(html)
        tools = BrowserTools(page)
        model = Model(client, 'https://model.invalid/v1', 'test', 'stub')
        result = run(skill, tools, model, 8)
        assert result['status'] == 'succeeded', result
        assert result['turns'] == 4, result
        assert requests[1]['recent_actions'][-1]['result']['ok'] is False
        assert page.locator('[role=status]').inner_text() == '搜索结果：009527'
        assert page.get_by_label('备注').input_value() == '保留'
        page.set_content(html)
        result = run(skill, tools, model, 1)
        assert result['status'] == 'blocked'
        assert tools.read({'label': '关键词'}, 'value') == '009527'
        assert tools.execute('wait', {'seconds': 0})['ok']
        assert tools.execute('read', {'target': {'placeholder': '搜索内容'}, 'kind': 'value'})['data'] == '009527'
    finally:
        browser.close()
print('通过：Skill 参数绑定、真实 Edge 表单、模型 HTTP 接口适配、执行循环、工具错误及轮数上限。模型响应为模拟数据。')

