"""流程名称、默认参数及内部执行文件；不修改原始录制和示例。"""
import json
import re
from pathlib import Path
from uuid import uuid4

import yaml

DISPLAY_NAMES = {
    "bejson_timestamp_precision": "转换时间戳与日期",
    "chinese_encyclopedia_research": "查询与比较百科资料",
    "chinese_image_file_pipeline": "批量处理并下载图片",
    "element_cn_collapse": "展开并读取折叠面板",
    "element_cn_dialog": "操作弹窗并读取结果",
    "element_cn_remote_select": "搜索并选择下拉选项",
    "vue_cn_navigation": "浏览文档并返回原页",
}


def metadata(text):
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError("流程内容格式无效")
    value = yaml.safe_load(parts[1])
    if not isinstance(value, dict) or not isinstance(value.get("actions"), list):
        raise ValueError("流程缺少操作步骤")
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root) / "data" / "flows"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = self.root / "index.json"
        self.items = json.loads(self.index.read_text(encoding="utf-8")) if self.index.exists() else []
        if not self.index.exists():
            sources = list((Path(root) / "skills").glob("*/SKILL.md")) + list((Path(root) / "data/generated").glob("*/SKILL.md"))
            for path in sources:
                try:
                    self.add(path)
                except (ValueError, OSError, yaml.YAMLError):
                    continue
            self.save()
        else:
            # 为早期自动导入的长标题补上显示名；用户自行改过的名字不变。
            changed = False
            for item in self.items:
                meta = metadata(self.path(item["id"]).read_text(encoding="utf-8"))
                legacy = re.sub(r"{{.*?}}", "指定内容", meta.get("goal", "未命名流程"))[:28]
                if item["name"] == legacy and meta.get("name") in DISPLAY_NAMES:
                    item["name"] = DISPLAY_NAMES[meta["name"]]
                    changed = True
            if changed:
                self.save()

    def save(self):
        temporary = self.index.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.index)

    def get(self, ident):
        return next((x for x in self.items if x["id"] == ident), None) or self.missing()

    @staticmethod
    def missing():
        raise ValueError("流程不存在或已删除")

    def path(self, ident):
        self.get(ident)
        return self.root / ident / "SKILL.md"

    def add(self, path, name=None):
        path = Path(path)
        text = path.read_text(encoding="utf-8-sig")
        meta = metadata(text)
        example = path.parent / "example_params.json"
        defaults = json.loads(example.read_text(encoding="utf-8")) if example.exists() else {}
        report = path.parent / "generation.json"
        report = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
        ident = uuid4().hex
        title = name or report.get("display_name") or DISPLAY_NAMES.get(meta.get("name")) or re.sub(r"{{.*?}}", "指定内容", meta.get("goal", "未命名流程"))[:28]
        item = {"id": ident, "name": title, "description": meta.get("description", meta.get("goal", "")),
                "defaults": {p: str(defaults.get(p, "")) for p in meta.get("params", [])},
                "status": "unverified", "issues": report.get("unresolved", []), "last_result": None}
        folder = self.root / ident
        folder.mkdir()
        (folder / "SKILL.md").write_text(text, encoding="utf-8")
        self.items.append(item)
        self.save()
        return item

    def update(self, ident, data):
        item = self.get(ident)
        name = str(data.get("name", item["name"])).strip()
        if not name or len(name) > 80:
            raise ValueError("流程名称须为 1–80 个字符")
        text = data.get("definition")
        meta = metadata(text if text is not None else self.path(ident).read_text(encoding="utf-8"))
        defaults = data.get("defaults", item["defaults"])
        if not isinstance(defaults, dict):
            raise ValueError("默认参数格式无效")
        if text is not None:
            self.path(ident).write_text(text, encoding="utf-8")
            item["status"] = "unverified"
        item.update(name=name, defaults={p: str(defaults.get(p, "")) for p in meta.get("params", [])})
        self.save()
        return item

    def delete(self, ident):
        self.get(ident)
        self.items = [x for x in self.items if x["id"] != ident]
        self.save()  # 从流程库移除；原始录制与生成产物保留。
