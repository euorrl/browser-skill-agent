"""加载文字 SKILL.md，并绑定运行参数。"""

import re
from pathlib import Path

import yaml


def load_skill(path: str, params: dict[str, str]) -> dict:
    text = Path(path).read_text(encoding="utf-8-sig")
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError("SKILL.md 必须以两行 --- 包围的 YAML 配置开头")
    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict) or not metadata.get("name") or not metadata.get("goal"):
        raise ValueError("Skill 必须包含 name 和 goal")
    missing = set(metadata.get("params", [])) - params.keys()
    if missing:
        raise ValueError(f"缺少参数：{', '.join(sorted(missing))}")

    def replace(match):
        name = match.group(1)
        if name not in params:
            raise ValueError(f"缺少参数：{name}")
        return params[name]

    def bind(value):
        if isinstance(value, str):
            return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace, value)
        if isinstance(value, list):
            return [bind(item) for item in value]
        if isinstance(value, dict):
            return {key: bind(item) for key, item in value.items()}
        return value

    skill = bind(metadata)
    skill["instructions"] = bind(parts[2].strip())
    skill["params"] = dict(params)
    return skill
