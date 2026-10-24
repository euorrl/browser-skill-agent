"""验证无模型执行、动态响应等待、失败不重放及服务端 token 累计。"""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import yaml
from playwright.sync_api import sync_playwright

from browser_skill_agent.runtime import Model, run_script
from browser_skill_agent.tools import BrowserTools


html = '''<meta charset="utf-8"><label>关键词<input disabled></label>
<button onclick="window.calls=(window.calls||0)+1;fetch('/items').then(r=>r.text()).then(t=>setTimeout(()=>document.querySelector('[role=status]').textContent=t,250))">搜索</button>
<p role="status">旧结果</p><script>setTimeout(()=>document.querySelector('input').disabled=false,250)</script>'''
actions = [
    {"tool": "fill", "args": {"target": {"label": "关键词"}, "value_ref": "query"}},
    {"tool": "click", "args": {"target": {"role": "button", "name": "搜索"},
      "wait_response": "https://test.invalid/items",
      "wait_after": {"target": {"role": "status"}, "state": "text", "value": "新结果"}}},
    {"title": "查询结果", "tool": "read", "args": {"target": {"role": "status"}}},
]
skill = {"name": "test", "goal": "测试", "params": {"query": "009527"}, "actions": actions}
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    try:
        page = browser.new_page()
        page.route("https://test.invalid/", lambda route: route.fulfill(body=html, content_type="text/html"))
        page.route("https://test.invalid/items", lambda route: route.fulfill(body="新结果", content_type="text/plain; charset=utf-8"))
        page.goto("https://test.invalid/")
        tools = BrowserTools(page)
        result = run_script(skill, tools)
        assert result["status"] == "succeeded", result
        assert result["outputs"][0]["data"] == "新结果", result
        assert page.get_by_label("关键词").input_value() == "009527"
        assert page.evaluate("window.calls") == 1
        actions[1]["args"]["wait_after"].update(value="永不出现", timeout=0.1)
        result = run_script(skill, tools)
        assert result["status"] == "blocked" and result["turns"] == 2
        assert page.evaluate("window.calls") == 2, "等待失败不能重复点击"
        result = run_script(skill, tools, max_steps=1)
        assert result["status"] == "blocked" and page.evaluate("window.calls") == 2
    finally:
        browser.close()

responses = [
    {"usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}},
    {},
    {"usage": {"prompt_tokens": 200, "completion_tokens": 30, "total_tokens": 230}},
]
def respond(request):
    payload = responses.pop(0)
    payload["choices"] = [{"message": {"content": '{"tool":"finish","args":{}}'}}]
    return httpx.Response(200, json=payload)

with httpx.Client(transport=httpx.MockTransport(respond)) as client:
    model = Model(client, "https://model.invalid/v1", "test", "test")
    for _ in range(3):
        model.decide({})
    assert model.usage == dict(prompt_tokens=300, completion_tokens=50, total_tokens=350, requests=3, reported_requests=2)

# 从没有 .env 的目录调用真实 CLI，确保默认模式无需任何模型设置。
with TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "page.html").write_text('<p role="status">本地结果</p>', encoding="utf-8")
    document = {"name": "cli_test", "goal": "读取本地页面", "start": (root / "page.html").as_uri(),
                "actions": [{"tool": "read", "args": {"target": {"role": "status"}}}]}
    (root / "SKILL.md").write_text("---\n" + yaml.safe_dump(document, allow_unicode=True) + "---\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("MODEL_")}
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, "-m", "browser_skill_agent", "SKILL.md", "--headless", "--json"], cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    result = json.loads(proc.stdout)
    assert result["mode"] == "script" and result["usage"]["requests"] == 0
    assert result["outputs"][0]["data"] == "本地结果"

print("通过：默认 CLI 无密钥执行、动态加载与响应等待、超时停止且不重放、步数限制、token 累计及缺失统计。")
