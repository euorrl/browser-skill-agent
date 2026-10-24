"""真实本地页面验证授权闸门；模型审核使用模拟响应，不消耗 API。"""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
import yaml
from playwright.sync_api import sync_playwright

from browser_skill_agent.approval import ApprovalPolicy, REVIEW_PROMPT
from browser_skill_agent.runtime import Model, run, run_script
from browser_skill_agent.tools import BrowserTools


class Planner:
    def __init__(self):
        self.states = []

    def decide(self, state):
        self.states.append(state)
        if len(self.states) == 1:
            return {"actions": [click, click]}
        return {"tool": "finish", "args": {"status": "succeeded", "message": "完成"}}


click = {"tool": "click", "args": {"target": {"id": "opaque"}}}
skill = {"name": "授权测试", "goal": "测试删除按钮", "params": {}, "actions": [click, click]}
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    try:
        page = browser.new_page()
        page.set_content('<input type="search" aria-label="搜索"><button id="opaque" onclick="window.count++">删除</button>')
        page.evaluate("window.count=0")
        policy = ApprovalPolicy("human", skill)
        tools = BrowserTools(page, policy)
        with patch("builtins.input", side_effect=AssertionError("普通搜索不应询问")):
            assert tools.execute("fill", {"target": {"label": "搜索"}, "value": "测试"})["ok"]
        with patch("builtins.input", return_value="no"):
            result = run_script(skill, tools)
        assert result["status"] == "blocked" and page.evaluate("window.count") == 0
        with patch("builtins.input", return_value="yes"):
            assert tools.execute(**dict(name="click", args=click["args"]))["ok"]
        assert page.evaluate("window.count") == 1
        with patch("builtins.input", side_effect=EOFError):
            assert tools.execute("click", click["args"])["approval_denied"]
        with patch("builtins.input", return_value="no"):
            assert tools.execute("read", {"target": {"id": "opaque"}, "requires_approval": True})["approval_denied"]

        def changed():
            page.locator("#opaque").evaluate("el=>el.textContent='支付'")
            return "yes"

        with patch("builtins.input", side_effect=changed):
            assert tools.execute("click", click["args"])["approval_denied"]
        assert page.evaluate("window.count") == 1

        for response in ({"approved": False, "reason": "不允许"}, {"approved": "true", "reason": "错误类型"}, {}):
            tools.approval = ApprovalPolicy("ai", skill, lambda state: response)
            assert tools.execute("click", click["args"])["approval_denied"]
        tools.approval = ApprovalPolicy("ai", skill, lambda state: {"approved": True, "reason": "符合测试任务"})
        planner = Planner()
        assert run(skill, tools, planner)["status"] == "succeeded"
        assert page.evaluate("window.count") == 2
        assert planner.states[-1]["recent_actions"][-1]["batch_skipped"] == 1
        tools.approval = ApprovalPolicy("ai", skill, lambda state: {"approved": False, "reason": "拒绝"})
        planner = Planner()
        assert run(skill, tools, planner)["status"] == "blocked"
        assert len(planner.states) == 1 and page.evaluate("window.count") == 2
        tools.approval = ApprovalPolicy("ai", skill, lambda state: 1 / 0)
        assert tools.execute("click", click["args"])["approval_denied"]
        tools.approval = ApprovalPolicy("allow", skill)
        with patch("builtins.input", side_effect=AssertionError("allow 不应询问")):
            assert tools.execute("click", {**click["args"], "requires_approval": True})["ok"]
        assert page.evaluate("window.count") == 3
    finally:
        browser.close()


def respond(request):
    body = json.loads(request.content)
    assert body["messages"][0]["content"] == REVIEW_PROMPT
    return httpx.Response(200, json={"choices": [{"message": {"content": '{"approved":true,"reason":"测试"}'}}],
                                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})


with httpx.Client(transport=httpx.MockTransport(respond)) as client:
    model = Model(client, "https://example.test", "test", "test")
    assert model.review({"task": "测试"})["approved"]
    assert model.usage["total_tokens"] == 15 and model.usage["requests"] == 1

with TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "page.html").write_text('<button id="opaque">Delete</button>', encoding="utf-8")
    document = {**skill, "start": (root / "page.html").as_uri(), "actions": [click]}
    (root / "SKILL.md").write_text("---\n" + yaml.safe_dump(document, allow_unicode=True) + "---\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("MODEL_")}
    env["PYTHONIOENCODING"] = "utf-8"
    command = [sys.executable, "-m", "browser_skill_agent", "SKILL.md", "--headless", "--json"]
    for flags, answer, status in (([], "no\n", "blocked"), (["--approval", "human"], "yes\n", "succeeded"),
                                   ([], "y\n", "succeeded"), ([], "\n", "succeeded"),
                                   ([], "Y\n", "succeeded"), ([], "", "blocked"),
                                   (["--approval", "allow"], "", "succeeded"), (["--approval", "ai"], "", "failed")):
        proc = subprocess.run(command + flags, cwd=root, env=env, input=answer,
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
        result = json.loads(proc.stdout)
        assert result["status"] == status, proc.stderr + proc.stdout
        assert result["usage"]["requests"] == 0
        if flags == ["--approval", "ai"]:
            assert "MODEL_API_KEY" in result["message"]

print("通过：人工/AI/全部允许、拒绝无副作用、授权时对象变化、批次停止和审核 Token 统计。")
