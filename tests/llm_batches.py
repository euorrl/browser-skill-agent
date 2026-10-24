"""用真实 Edge 和确定的模型响应验证批次、观察边界及有界证据。"""

from playwright.sync_api import sync_playwright

from browser_skill_agent.runtime import run
from browser_skill_agent.tools import BrowserTools


class PlannedModel:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.states = []

    def decide(self, state):
        self.states.append(state)
        return next(self.decisions)


def action(tool, **args):
    return {"tool": tool, "args": args}


finish = action("finish", status="succeeded", message="测试结束")
fill = action("fill", target={"label": "关键词"}, value_ref="query")
click = action("click", target={"role": "button", "name": "搜索"},
               wait_after={"target": {"role": "status"}, "state": "text", "value": "新结果"})
read = action("read", target={"role": "status"}, max_chars=600)
skill = {"name": "batch_test", "goal": "搜索并读取结果", "params": {"query": "009527"},
         "actions": [{"private_script_marker": True}], "stages": ["搜索", "汇总"]}
html = '''<label>关键词<input></label>
<button onclick="window.count=(window.count||0)+1;setTimeout(()=>document.querySelector('[role=status]').textContent='新结果',200)">搜索</button>
<p role="status">旧结果</p>'''

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    context = browser.new_context()
    try:
        page = context.new_page()
        tools = BrowserTools(page)
        page.set_content(html)
        single = PlannedModel([fill, click, read, finish])
        first = run(skill, tools, single)
        page.set_content(html)
        page.evaluate("window.count=0")
        batch = PlannedModel([{"stage": "填写并搜索", "actions": [fill, click, read]}, finish])
        second = run(skill, tools, batch)
        assert first["turns"] == 4 and second["turns"] == 2
        assert first["steps"] == second["steps"] == 4
        assert second["action_steps"] == 3 and second["finish_steps"] == 1 and second["invalid_plans"] == 0
        assert page.evaluate("window.count") == 1
        assert batch.states[-1]["evidence"][0]["data"] == "新结果"
        assert "actions" not in batch.states[0]["skill"]
        assert batch.states[0]["skill"]["stages"] == skill["stages"]

        # 阶段超过旧的 4 步上限仍可完整执行，由末尾读取决定观察节点。
        page.set_content(html)
        page.evaluate("window.count=0")
        model = PlannedModel([{"stage": "完整搜索", "success_criteria": "读取新结果",
                               "actions": [fill, fill, fill, fill, click, read]}, finish])
        result = run(skill, tools, model)
        assert result["turns"] == 2 and result["steps"] == 7
        assert page.evaluate("window.count") == 1
        assert "batch_limit" not in model.states[0]
        last = model.states[-1]["last_stage"]
        assert last["goal"] == "完整搜索" and last["success_criteria"] == "读取新结果"
        assert last["executed"] == 6 and last["skipped"] == 0
        assert "读取结果" in last["stop_reason"]

        # 未知控件展开后由模型主动选择观察，再使用实际看到的选项。
        page.set_content('<button onclick="document.querySelector(\'section\').hidden=false">展开</button>'
                         '<section hidden><button onclick="window.selected=true">动态选项</button></section>')
        page.evaluate("window.selected=false")
        model = PlannedModel([
            {"stage": "查看选项", "actions": [action("click", target={"role": "button", "name": "展开"}), action("snapshot")]},
            {"stage": "选择已观察选项", "actions": [action("click", target={"role": "button", "name": "动态选项"})]}, finish])
        run(skill, tools, model)
        assert "动态选项" in model.states[1]["evidence"][0]["data"]
        assert page.evaluate("window.selected")
        assert "阶段计划已执行" in model.states[2]["last_stage"]["stop_reason"]

        # 等待失败意味着动作已执行，后续点击必须丢弃。
        page.set_content(html)
        page.evaluate("window.count=0")
        bad_wait = action("click", target={"role": "button", "name": "搜索"},
                          wait_after={"target": {"role": "status"}, "state": "text", "value": "永不出现", "timeout": 0.1})
        model = PlannedModel([{"actions": [bad_wait, click]}, finish])
        run(skill, tools, model)
        assert page.evaluate("window.count") == 1
        assert model.states[-1]["recent_actions"][-1]["batch_skipped"] == 1

        # 读取产生新证据后不继续执行预先猜测的后续动作。
        page.evaluate("window.count=0")
        model = PlannedModel([{"actions": [read, click]}, finish])
        run(skill, tools, model)
        assert page.evaluate("window.count") == 0

        # 标签页创建后停止批次；不得在新页面上盲目填写旧目标。
        model = PlannedModel([{"actions": [action("tabs", action="new"), fill]}, finish])
        run(skill, tools, model)
        assert model.states[-1]["recent_actions"][-1]["batch_skipped"] == 1
        tools.page.close()

        # 批次数超出剩余预算时，整批拒绝，不能偷偷扩大操作上限。
        page.evaluate("window.count=0")
        model = PlannedModel([{"actions": [click, click]}])
        result = run(skill, tools, model, max_steps=1)
        assert result["status"] == "blocked" and page.evaluate("window.count") == 0
        assert result["invalid_plans"] == 1 and result["action_steps"] == result["finish_steps"] == 0
        model = PlannedModel([{"actions": [click, finish]}, finish])
        run(skill, tools, model)
        assert page.evaluate("window.count") == 0, "finish 不得混入批次"

        # 读取退出六次历史窗口后仍能复用，不需要切页重新读取。
        page.set_content('<p role="status">历史证据</p><p>' + '长正文' * 5000 + '</p>')
        model = PlannedModel([read] + [action("wait", seconds=0)] * 7 + [finish])
        run(skill, tools, model)
        assert model.states[-1]["evidence"][0]["data"] == "历史证据"
        assert all(item.get("action", {}).get("tool") != "read" for item in model.states[-1]["recent_actions"])
        assert len(model.states[-1]["page"]["text"]) <= 10000
        assert model.states[-1]["page"]["truncated"]
    finally:
        browser.close()

print("通过：相同任务模型调用 4→2、等待失败不重放、读取/标签页观察边界、预算限制、证据保留和上下文裁剪。")
