"""用真实 Edge 验证复杂组件、动态等待、框架、标签页及文件工具。"""

import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_skill_agent.tools import BrowserTools
from browser_skill_agent.tools.files import FileOptions


ROOT = Path(__file__).resolve().parents[1]


def verify():
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as temp:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_context().new_page()
            file = Path(temp) / "upload.txt"
            file.write_text("测试", encoding="utf-8")
            tools = BrowserTools(page, file_options=FileOptions(upload_files=[file], download_dir=Path(temp) / "downloads"))

            def call(name, **args):
                result = tools.execute(name, args)
                assert result["ok"], (name, result)
                return result.get("data")

            call("goto", url=(ROOT / "tests/fixtures/components.html").as_uri())
            select = {"label": "排序"}
            assert len(call("read", target=select, kind="options")) == 2
            call("select", target=select, label="价格降序")
            assert call("read", target=select, kind="value") == "desc"
            call("click", target={"role": "button", "name": "筛选品牌"})
            assert not tools.execute("select", {"target": {"role": "button", "name": "筛选品牌"}, "label": "x"})["ok"]
            call("type_text", target={"label": "品牌搜索"}, value="Forge")
            call("wait_for", target={"role": "option", "name": "ForgeFlex"})
            call("click", target={"role": "option", "name": "ForgeFlex"})
            call("wait_for", target={"role": "status"}, state="text", value="已选择 ForgeFlex")
            call("click", target={"role": "button", "name": "加载控件"})
            call("wait_for", target={"label": "延迟字段"}, state="enabled")
            call("fill", target={"label": "延迟字段"}, value="完成")
            call("wait_for", target={"label": "延迟字段"}, state="value", value="完成")
            call("set_checked", target={"label": "启用筛选"}, checked=True)
            assert call("read", target={"label": "启用筛选"}, kind="checked") is True
            call("click", target={"role": "button", "name": "加入", "within": {"role": "article", "name": "商品乙"}})
            assert page.get_by_role("article", name="商品甲").inner_text().endswith("0")
            assert page.get_by_role("article", name="商品乙").inner_text().endswith("1")
            frame = next(f["id"] for f in tools.observe()["frames"] if not f["main"])
            call("fill", target={"label": "框架字段", "frame": frame}, value="iframe")
            assert "iframe" in call("snapshot", frame=frame)["text"]
            original = next(t["id"] for t in tools.observe()["tabs"] if t["active"])
            tabs = call("tabs", action="new", url="about:blank")
            new_tab = next(t["id"] for t in tabs if t["active"])
            call("tabs", action="switch", page_id=original)
            call("tabs", action="close", page_id=new_tab)
            call("dialog", action="accept")
            call("click", target={"role": "button", "name": "确认操作"})
            assert page.locator("#answer").inner_text() == "已确认"
            call("click", target={"role": "button", "name": "确认操作"})
            assert page.locator("#answer").inner_text() == "已取消"
            file = Path(temp) / "upload.txt"
            file.write_text("测试", encoding="utf-8")
            call("upload", target={"label": "附件"}, paths=str(file))
            assert page.locator("#file").evaluate("e => e.files[0].name") == "upload.txt"
            result = call("download", target={"role": "link", "name": "下载示例"})
            downloaded = Path(result["path"])
            assert downloaded.read_text() == "test download"
            downloaded.unlink()
            assert not tools.execute("wait_for", {"target": {"text": "不存在的控件"}, "timeout": 0.1})["ok"]
            print("通过：自定义下拉筛选、原生下拉、动态等待、容器定位、iframe、标签页、弹窗、上传与下载。")
        finally:
            browser.close()


if __name__ == "__main__":
    verify()
