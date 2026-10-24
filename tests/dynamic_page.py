"""验证动态重绘、重复元素、遮挡、延迟启用和动作后的结果等待。"""

from playwright.sync_api import sync_playwright
from browser_skill_agent.tools import BrowserTools


HTML = """<html><body>
<button style="display:none" id="hidden">保存</button>
<div id="host"><button id="save" disabled>保存</button></div>
<p role="status">尚未保存</p>
<button id="search">搜索</button><p id="result">旧结果</p>
<article aria-label="商品甲"><button data-testid="buy-a">加入</button></article>
<article aria-label="商品乙"><button data-testid="buy-b">加入</button></article>
<input aria-label="关键词" disabled>
<script>
window.saved=0; window.searched=0; window.keys=0;
document.querySelector('input').addEventListener('input', () => window.keys++);
setTimeout(() => {
  document.querySelector('#host').innerHTML='<button id="save">保存</button>';
  document.querySelector('#save').onclick=() => { window.saved++; document.querySelector('[role=status]').textContent='已保存'; };
  document.querySelector('input').disabled=false;
},400);
document.querySelector('#search').onclick=() => {
  window.searched++;
  document.querySelector('#result').setAttribute('aria-busy','true');
  setTimeout(() => { document.querySelector('#result').textContent='新结果'; document.querySelector('#result').removeAttribute('aria-busy'); },500);
};
</script></body></html>"""


def verify():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_context().new_page()
            tools = BrowserTools(page)
            page.set_content(HTML)

            def call(name, **args):
                result = tools.execute(name, args)
                assert result["ok"], result
                return result

            # 没有手工 sleep：等待延迟启用，重绘后仍定位到正确的可见按钮。
            call("click", target={"text": "保存"})
            assert page.evaluate("window.saved") == 1
            page.evaluate("document.querySelector('input').disabled=true; setTimeout(() => document.querySelector('input').disabled=false,250)")
            call("type_text", target={"label": "关键词"}, value="abc")
            assert page.evaluate("window.keys") == 3
            found = call("locate", target={"role": "button", "name": "加入"})["data"]
            assert found["count"] == 2
            assert found["candidates"][1]["suggested_target"] == {"test_id": "buy-b"}
            # 列表顺序改变后，稳定标识仍指向原商品，而不是之前的序号。
            page.evaluate("document.body.prepend(document.querySelector('[aria-label=商品乙]'))")
            target = found["candidates"][1]["suggested_target"]
            assert tools.target(target).get_attribute("data-testid") == "buy-b"
            # 遮挡层消失前不穿透点击，不使用 force。
            page.evaluate("""() => {
              const cover=document.createElement('div');
              cover.style.cssText='position:fixed;inset:0;z-index:9999;background:white';
              document.body.append(cover); setTimeout(() => cover.remove(),300);
            }""")
            call("click", target={"id": "save"})
            assert page.evaluate("window.saved") == 2
            result = call("click", target={"role": "button", "name": "搜索"},
                          wait_after={"target": {"id": "result"}, "state": "text", "value": "新结果"})
            assert result["after_wait"]["ok"]
            assert page.locator("#result").inner_text() == "新结果"
            result = call("click", target={"role": "button", "name": "搜索"},
                          wait_after={"target": {"text": "永远不存在"}, "timeout": 0.1})
            assert result["after_wait"]["ok"] is False
            assert page.evaluate("window.searched") == 2  # 不因等待失败重放提交。
            bad = tools.execute("click", {"target": {"id": "search"}, "wait_after": {"typo": True}})
            assert not bad["ok"] and page.evaluate("window.searched") == 2
            observation = tools.observe()
            assert "新结果" in observation["text"]
            assert observation["readiness"]["settled"]
            # 持续动态内容也必须在等待上限后返回，而非无限等待网络/DOM 空闲。
            page.evaluate("document.querySelector('#result').setAttribute('aria-busy','true')")
            assert tools.observe()["readiness"]["settled"] is False
            print("通过：重绘与隐藏副本定位、延迟启用、稳定候选标识、结果等待、等待超时不重复动作、有界页面稳定等待。")
        finally:
            browser.close()


if __name__ == "__main__":
    verify()
