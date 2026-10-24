"""按录制会话保存原始事件和合并动作，不执行任何网页操作。"""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from uuid import uuid4
import re


def now():
    return datetime.now(timezone.utc).isoformat()


def clean_url(value):
    """URL 中常见认证参数与用户信息不进入记录；不是通用脱敏器。"""
    try:
        parts = urlsplit(value)
        if parts.scheme == "data":
            return "data:[内容未记录]"
        host = parts.netloc.rsplit("@", 1)[-1]
        pairs = [(k, "[已遮蔽]" if re.search(r"token|password|secret|session|authorization|code", k, re.I) else v)
                 for k, v in parse_qsl(parts.query, keep_blank_values=True)]
        fragment = "[已遮蔽]" if re.search(r"token|password|secret|session|authorization", parts.fragment, re.I) else parts.fragment
        return urlunsplit((parts.scheme, host, parts.path, urlencode(pairs), fragment))
    except ValueError:
        return "[无法解析网址]"


class Recording:
    def __init__(self, root, start_url):
        self.id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
        self.folder = Path(root) / "data" / "recordings" / self.id
        self.download_dir = Path(root) / "files" / "recordings" / self.id / "downloads"
        self.folder.mkdir(parents=True)
        self.session = {"schema_version": 1, "id": self.id, "status": "recording",
                        "started_at": now(), "ended_at": None, "start_url": clean_url(start_url),
                        "pages": {}, "downloads": [], "action_count": 0, "event_count": 0,
                        "notes": ["观察到的页面变化不等于业务成功；记录未生成参数或 Skill。"]}
        self.actions = []
        self.by_event = {}
        self.save()

    def event(self, kind, page_id=None, frame_id=None, **data):
        self.session["event_count"] += 1
        record = {"sequence": self.session["event_count"], "time": now(), "type": kind,
                  "page_id": page_id, "frame_id": frame_id, **data}
        with (self.folder / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def action(self, event):
        kind = event["type"]
        if kind == "observation":
            previous = self.by_event.get(event.get("related_event"))
            if previous:
                previous["observed_after"].append({k: v for k, v in event.items() if k not in ("type", "page_id", "frame_id")})
                previous["observed_after"] = previous["observed_after"][-5:]
            return
        if kind == "file_hash":
            previous = self.by_event.get(event.get("related_event"))
            if previous:
                previous["files"] = event["files"]
            return
        if kind not in {"input", "click", "double_click", "select", "set_checked", "press", "upload", "scroll", "dialog"}:
            return
        if kind == "scroll":
            return  # 原始记录保留滚动，暂不推断为可执行步骤。
        action = {"id": f"a{len(self.actions)+1}", "kind": "fill" if kind == "input" else kind,
                  "page_id": event["page_id"], "frame_id": event["frame_id"],
                  "source_events": [event["sequence"]], "observed_after": [],
                  **{k: v for k, v in event.items() if k not in ("sequence", "type", "page_id", "frame_id")}}
        last = self.actions[-1] if self.actions else None
        if kind == "double_click" and last and last["kind"] == "click" and last.get("element_key") == action.get("element_key"):
            last["kind"] = "double_click"
            last["source_events"].append(event["sequence"])
            action = last
        elif kind == "input" and last and last["kind"] == "fill" and all(
                last.get(key) == action.get(key) for key in ("page_id", "frame_id", "element_key")):
            last["value"] = action.get("value")
            last["value_truncated"] = action.get("value_truncated",False)
            last["time"] = action["time"]
            last["source_events"].append(event["sequence"])
            action = last
        else:
            self.actions.append(action)
        if event.get("event_id"):
            self.by_event[event["event_id"]] = action
        self.session["action_count"] = len(self.actions)

    def save(self):
        for filename, data in (("session.json", self.session), ("actions.json", self.actions)):
            path = self.folder / filename
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(path)
