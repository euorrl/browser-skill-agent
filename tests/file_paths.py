"""本地验证文件选择范围、路径默认值、下载命名和 CLI 参数，不请求模型。"""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml
from playwright.sync_api import sync_playwright

from browser_skill_agent.approval import ApprovalPolicy
from browser_skill_agent.tools import BrowserTools
from browser_skill_agent.tools.files import FileOptions


with TemporaryDirectory() as temp, sync_playwright() as pw:
    root = Path(temp)
    uploads = root / "uploads"
    uploads.mkdir()
    selected = uploads / "报告.txt"
    selected.write_text("chosen", encoding="utf-8")
    other = uploads / "other.txt"
    other.write_text("not chosen", encoding="utf-8")
    html = root / "page.html"
    html.write_text('<input type="file" aria-label="附件"><a download="web.txt" href="data:text/plain,hello">下载</a>', encoding="utf-8")
    options = FileOptions(uploads, [selected.name], root / "results", "指定.txt")
    ordinary = FileOptions.from_skill({"params": {"file": str(other), "topic": "测试"}})
    assert ordinary.uploads == {}, "普通参数不能自动授权上传"
    mapped = FileOptions.from_skill({"params": {"first": str(selected), "second": str(other)},
                                     "file_params": {"uploads": ["first", "second"]}})
    assert list(mapped.uploads) == ["u1", "u2"]
    defaults = FileOptions.from_skill({"file_params": {"uploads": ["optional_file"], "download_name": "save_as"}})
    assert defaults.uploads == {} and defaults.download_name is None
    for bad in ({"uploads": "file"}, {"unknown": "x"}, {"download_name": []}):
        try:
            FileOptions.from_skill({"file_params": bad})
        except ValueError:
            pass
        else:
            raise AssertionError(bad)
    assert options.available() == [{"id": "u1", "name": selected.name}]
    assert FileOptions().download_dir == (Path.cwd() / "files/downloads").resolve()
    for bad in ("../outside.txt", "C:\\outside.txt", "CON", "a:b", "a/b"):
        try:
            FileOptions(download_name=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(bad)
    browser = pw.chromium.launch(channel="msedge", headless=True)
    try:
        page = browser.new_page()
        page.goto(html.as_uri())
        tools = BrowserTools(page, approval=ApprovalPolicy("human", {}), file_options=options)
        upload = {"target": {"label": "附件"}, "file_ids": ["u1"]}
        with patch("builtins.input", return_value="n"):
            assert tools.execute("upload", upload)["approval_denied"]
        assert page.get_by_label("附件").evaluate("e=>e.files.length") == 0
        tools.approval = ApprovalPolicy("allow", {})
        assert not tools.execute("upload", {"target": upload["target"], "paths": [str(other)]})["ok"]
        assert not tools.execute("upload", {"target": upload["target"], "file_ids": ["u2"]})["ok"]
        assert tools.execute("upload", upload)["ok"]
        assert page.get_by_label("附件").evaluate("e=>e.files[0].name") == selected.name
        assert tools.observe()["upload_files"] == options.available()
        for expected in ("指定.txt", "指定-1.txt"):
            result = tools.execute("download", {"target": {"text": "下载"}, "filename": "model.txt"})
            assert result["ok"], result
            saved = Path(result["data"]["path"])
            assert saved == root / "results" / expected and saved.read_text() == "hello"
        # 未指定文件的工具实例不能上传；默认采用网站建议名称。
        tools = BrowserTools(page, file_options=FileOptions(download_dir=root / "suggested"))
        assert not tools.execute("upload", upload)["ok"]
        result = tools.execute("download", {"target": {"text": "下载"}})
        assert result["ok"] and Path(result["data"]["path"]).name == "web.txt"
        assert selected.read_text(encoding="utf-8") == "chosen"
    finally:
        browser.close()

    skill = {"name": "文件测试", "goal": "选择本地文件并下载", "start": html.as_uri(),
             "params": ["file"], "file_params": {"uploads": ["file"], "upload_dir": "source", "download_dir": "save_dir", "download_name": "save_as"},
             "actions": [{"tool": "upload", "args": upload},
                         {"tool": "download", "args": {"target": {"text": "下载"}}}]}
    (root / "SKILL.md").write_text("---\n" + yaml.safe_dump(skill, allow_unicode=True) + "---\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("MODEL_")}
    env["PYTHONIOENCODING"] = "utf-8"
    command = [sys.executable, "-m", "browser_skill_agent", "SKILL.md", "--headless", "--json", "--approval", "allow",
               "--param", "source=uploads", "--param", f"file={selected.name}", "--param", "save_dir=cli-downloads", "--param", "save_as=cli.txt"]
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "succeeded"
    assert (root / "cli-downloads" / "cli.txt").read_text() == "hello"

print("通过：文件编号、上传选择范围、授权拒绝、默认目录、指定下载名称、同名避让和真实 CLI 文件参数。")
