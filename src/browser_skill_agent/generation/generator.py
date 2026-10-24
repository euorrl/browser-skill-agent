"""整理录制证据、调用模型并保存独立的 Skill 草稿目录。"""
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import yaml
from dotenv import load_dotenv

from .model import GenerationModel
from ..tools import TOOL_HELP
from ..tools.registry import TOOL_GROUPS
from .prompt import SYSTEM_PROMPT, RUNTIME_HELP


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def compact(value):
    """限制自由文本长度，保留字段结构；显式标明截断。"""
    if isinstance(value, str):
        return value if len(value) <= 1600 else value[:1600] + "\n[生成输入已截断]"
    if isinstance(value, list):
        return [compact(item) for item in value]
    if isinstance(value, dict):
        return {key: compact(item) for key, item in value.items()}
    return value


def prepare_recording(folder):
    """优先使用合并动作，只从原始流补充导航、文件等非动作事件。"""
    folder = Path(folder)
    session = read_json(folder / "session.json")
    if session.get("schema_version") != 1 or session.get("status") != "completed":
        raise ValueError("仅支持 schema_version=1 且 completed 的录制；请先正常结束录制")
    actions = read_json(folder / "actions.json")
    if not isinstance(actions, list) or not actions:
        raise ValueError("录制没有可供生成的动作")
    normalized = []
    for action in actions:
        item = {key: value for key, value in action.items() if key not in
                {"observed_after", "event_id", "document_id", "client_time", "element_key"}}
        if item.get("redacted") or item.get("target", {}).get("sensitive"):
            item["value"] = None
        observations = action.get("observed_after", [])
        # 首尾变化足以作为草稿线索；完整证据仍保存在原始目录。
        selected = observations[:1] + observations[-1:] if len(observations) > 1 else observations
        item["observed_after"] = [{k: v for k, v in observation.items() if k in
                                  {"sequence", "url", "title", "text", "truncated", "controls", "controls_truncated"}}
                                 for observation in selected]
        normalized.append(compact(item))
    transitions = []
    with (folder / "events.jsonl").open(encoding="utf-8-sig") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("type") in {"page_open", "page_close", "navigation", "navigation_observed",
                                     "download_started", "download_completed", "download_failed", "download_cancelled",
                                     "dialog", "recorder_error", "flush_unavailable", "navigation_error"}:
                transitions.append(compact(event))
    state = {
        "runtime": RUNTIME_HELP, "tools": TOOL_HELP,
        "recording": {key: session.get(key) for key in
                      ("id", "status", "start_url", "pages", "downloads", "notes")},
        "actions": normalized, "page_events": transitions,
        "recording_gaps": ["观察为有限文本和控件采样，不是完整 DOM 或业务成功证明。",
                           "每个动作最多提供首尾两份已保存观察；长字符串在 1600 字符处标记截断。",
                           "输入值被截断或遮蔽时不得用于构造完整演示参数。"],
    }
    # 不静默丢掉后半段任务；超大录制留给后续分段生成功能。
    if len(json.dumps(state, ensure_ascii=False)) > 140000:
        raise ValueError("录制摘要超过 140000 字符，请录制更聚焦的单个任务；当前不支持分段生成")
    return state


def validate(result):
    """只检查落盘契约和现有工具签名，不把格式校验冒充执行验证。"""
    if not isinstance(result, dict) or result.get("status") not in {"draft", "needs_evidence", "unsupported"}:
        raise ValueError("模型没有返回有效的草稿状态")
    if "display_name" in result and (not isinstance(result["display_name"], str) or not 1 <= len(result["display_name"].strip()) <= 80):
        raise ValueError("流程显示名称须为 1–80 个字符")
    skill = result.get("skill")
    if not isinstance(skill, dict):
        raise ValueError("模型缺少 skill 对象")
    allowed = {"name", "description", "params", "start", "goal", "actions", "stages", "instructions", "file_params"}
    if set(skill) - allowed:
        raise ValueError("Skill 含不支持的字段：" + ", ".join(sorted(set(skill) - allowed)))
    for key in ("name", "description", "start", "goal", "instructions"):
        if not isinstance(skill.get(key), str) or not skill[key].strip():
            raise ValueError(f"Skill 缺少有效的 {key}")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", skill["name"]):
        raise ValueError("Skill 名称须为不超过 80 字符的 snake_case")
    params = skill.get("params")
    if not isinstance(params, list) or any(not isinstance(p, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", p) for p in params):
        raise ValueError("params 必须为 snake_case 参数名列表")
    if len(set(params)) != len(params):
        raise ValueError("参数名重复")
    examples = result.get("example_params")
    if not isinstance(examples, dict) or set(examples) - set(params) or any(not isinstance(v, str) for v in examples.values()):
        raise ValueError("example_params 只能包含已声明参数的字符串示例值")
    for key in ("evidence_map", "assumptions", "unresolved"):
        if not isinstance(result.get(key), list):
            raise ValueError(f"缺少 {key} 列表")
    mapping = skill.get("file_params", {})
    if not isinstance(mapping, dict) or set(mapping) - {"uploads", "upload_dir", "download_dir", "download_name"}:
        raise ValueError("file_params 字段不符合 runtime 规范")
    for key, value in mapping.items():
        refs = value if key == "uploads" else [value]
        if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in params for ref in refs):
            raise ValueError("file_params 必须引用已声明参数")
    # 直接复用注册表的签名，无浏览器、网络或文件操作。
    from inspect import signature
    from ..tools.waiting import Waiting
    methods = {name: getattr(group, name) for group, names in TOOL_GROUPS for name in names}
    actions = skill.get("actions")
    if not isinstance(actions, list):
        raise ValueError("actions 必须为列表")
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("args"), dict):
            raise ValueError("action 必须包含 tool 和 args 对象")
        name = action.get("tool")
        method = methods.get(name) if isinstance(name, str) else None
        if method is None:
            raise ValueError(f"未知工具：{name}")
        args = dict(action["args"])
        ref = args.pop("value_ref", None)
        if ref is not None:
            if ref not in params:
                raise ValueError(f"未声明参数：{ref}")
            args["value"] = "示例"
        for key in ("requires_approval", "wait_response"):
            args.pop(key, None)
        after = args.pop("wait_after", None)
        if after is not None:
            signature(Waiting.wait_for).bind(None, **after)
        if name == "upload" and "file_ids" in args:
            if "paths" in args:
                raise ValueError("upload 不能同时指定 file_ids 和 paths")
            args["paths"] = args.pop("file_ids")
        signature(method).bind(None, **args)
    for ref in re.findall(r"{{\s*(\w+)\s*}}", json.dumps(skill, ensure_ascii=False)):
        if ref not in params:
            raise ValueError(f"模板引用了未声明参数：{ref}")
    stages = skill.get("stages")
    if not isinstance(stages, list) or any(not isinstance(s, dict) or
            not all(k in s for k in ("goal", "path", "evidence", "observe_when", "interrupt_when")) for s in stages):
        raise ValueError("stages 缺少阶段字段")
    for entry in result["evidence_map"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("action_index"), int) or not 1 <= entry["action_index"] <= len(actions):
            raise ValueError("evidence_map 必须引用有效的动作序号")
        if not isinstance(entry.get("source_actions"), list):
            raise ValueError("证据映射缺少 source_actions 列表")
    for param in set(params) - set(examples):
        result["unresolved"].append({"source_actions": [], "issue": f"参数 {param} 缺少演示值", "needed_evidence": "执行前提供真实参数；不自动填入敏感值或猜测资源位置。"})
    if result["status"] == "draft" and (result["unresolved"] or not actions or not stages):
        result["status"] = "needs_evidence"
    return result


def normalize_guidance(value=None):
    """用户自愿提供的生成指导，与网页证据分开传递。"""
    if value is None:
        return {}
    if not isinstance(value, dict) or set(value) - {"name", "description", "parameters"}:
        raise ValueError("生成指导仅支持名称、描述和参数建议")
    result = {}
    for key, limit in (("name", 80), ("description", 4000), ("parameters", 2000)):
        text = value.get(key, "")
        if not isinstance(text, str) or len(text) > limit:
            raise ValueError(f"{key} 须为不超过 {limit} 字的文字")
        if text.strip():
            result[key] = text.strip()
    return result


def generate(recording, model, output_root, guidance=None):
    state = prepare_recording(recording)
    guidance = normalize_guidance(guidance)
    state["user_guidance"] = guidance
    raw = model.request(state, SYSTEM_PROMPT)
    corrections = []
    for attempt in range(2):
        try:
            result = validate(raw)
            break
        except (ValueError, TypeError, KeyError) as exc:
            corrections.append(str(exc))
            if attempt == 1:
                failed = Path(output_root) / ("invalid-" + uuid4().hex[:8])
                failed.mkdir(parents=True, exist_ok=False)
                (failed / "generation.json").write_text(json.dumps({"status": "invalid", "errors": corrections,
                    "model_output": raw, "usage": dict(model.usage)}, ensure_ascii=False, indent=2), encoding="utf-8")
                raise ValueError(f"格式修正后仍无效；诊断保存在 {failed}") from exc
            if hasattr(model, "progress"):
                model.progress(f"草稿格式需修正：{exc}；仅尝试一次格式修正，不操作网页。")
            raw = model.request({"runtime": RUNTIME_HELP, "tools": TOOL_HELP, "draft": raw,
                                 "user_guidance": guidance,
                                 "validation_error": str(exc),
                                 "instruction": "仅修正结构或工具参数错误，保持任务、参数和已有证据；不能增加未经证实的操作。返回完整 JSON。"}, SYSTEM_PROMPT)
    source_ids = {action["id"] for action in state["actions"]}
    if guidance.get("name"):
        result["display_name"] = guidance["name"]
    for entry in result["evidence_map"]:
        unknown = [source for source in entry["source_actions"] if source not in source_ids]
        if unknown:
            # 证据缺口不丢弃整个草稿，也不保留虚假的溯源引用。
            entry["source_actions"] = [source for source in entry["source_actions"] if source in source_ids]
            result["unresolved"].append({"source_actions": entry["source_actions"],
                "issue": f"生成动作 {entry['action_index']} 引用了不存在的录制动作：{unknown}",
                "needed_evidence": "重新核对原始录制，补充真实来源；该映射不能作为已验证证据。"})
            if result["status"] == "draft":
                result["status"] = "needs_evidence"
    skill = dict(result["skill"])
    body = skill.pop("instructions")
    destination = Path(output_root) / (skill["name"] + "-" + uuid4().hex[:8])
    destination.mkdir(parents=True, exist_ok=False)
    report = {k: v for k, v in result.items() if k not in {"skill", "example_params"}}
    report.update(recording_id=state["recording"]["id"], source=str(Path(recording).resolve()),
                  generated_at=datetime.now(timezone.utc).isoformat(), validated=False,
                  usage=dict(model.usage), model=getattr(model, "model", None), format_corrections=corrections,
                  user_guidance=guidance)
    (destination / "SKILL.md").write_text(
        "---\n" + yaml.safe_dump(skill, allow_unicode=True, sort_keys=False) + "---\n\n" + body + "\n", encoding="utf-8")
    for name, data in (("example_params.json", result["example_params"]), ("generation.json", report)):
        (destination / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, report


def main(argv=None):
    parser = argparse.ArgumentParser(description="从已完成录制生成 Skill 草稿（调用 LLM，不执行网页操作）")
    parser.add_argument("recording", type=Path, help="录制目录，含 session.json、actions.json、events.jsonl")
    parser.add_argument("--output-dir", type=Path, default=Path("data/generated"), help="草稿父目录，默认 data/generated")
    parser.add_argument("--timeout", type=float, default=300, help="模型请求超时秒数，默认 300；不自动重试")
    args = parser.parse_args(argv)
    if not 0 < args.timeout < float("inf"):
        parser.error("--timeout 必须为有限正数")
    load_dotenv(Path.cwd() / ".env")
    settings = [os.environ.get(name, "") for name in ("MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME")]
    try:
        if not all(settings):
            raise ValueError("请配置 MODEL_BASE_URL、MODEL_API_KEY 和 MODEL_NAME")
        print("正在整理录制并请求模型生成 Skill 草稿…", flush=True)
        with httpx.Client(timeout=args.timeout) as client:
            model = GenerationModel(client, *settings, timeout=args.timeout,
                                    progress=lambda message: print(message, flush=True))
            destination, report = generate(args.recording, model, args.output_dir)
        print(f"草稿已保存：{destination}\n生成状态：{report['status']}；尚未运行验证。")
        print(f"参数示例：{destination / 'example_params.json'}\n生成报告：{destination / 'generation.json'}")
        print(f"待解决问题：{len(report['unresolved'])} 项")
        usage = report["usage"]
        if usage["reported_requests"] == usage["requests"]:
            print(f"Token 消耗：输入 {usage['prompt_tokens']}，输出 {usage['completion_tokens']}，合计 {usage['total_tokens']}")
        else:
            print("Token 消耗：服务端未完整报告")
        return 0
    except (ValueError, TypeError, KeyError, OSError, httpx.HTTPError) as exc:
        print(f"生成失败：{exc}")
        return 1
