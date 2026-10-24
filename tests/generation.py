"""生成契约与 HTTP 模型接口集成测试，不访问外部网站或消耗 Token。"""
import json
import tempfile
import unittest
from pathlib import Path

import httpx

from browser_skill_agent.generation.generator import generate, prepare_recording, validate, normalize_guidance
from browser_skill_agent.generation.model import GenerationModel
from browser_skill_agent.runtime import Model
from browser_skill_agent.skill import load_skill


def draft():
    return {
        "status": "draft",
        "skill": {
            "name": "search_records", "description": "按输入检索记录；需要查询时使用。",
            "params": ["query"], "start": "https://example.org/", "goal": "查询 {{query}}",
            "actions": [{"title": "填写查询", "tool": "fill", "args": {"target": {"label": "查询"}, "value_ref": "query"}},
                        {"title": "读取结果", "tool": "read", "args": {"target": {"id": "results"}, "max_chars": 600}}],
            "stages": [{"goal": "查询", "path": ["填写后读取"], "evidence": "读取到结果", "observe_when": "读取后", "interrupt_when": "定位失败"}],
            "instructions": "查询只读记录。query 为查询内容。",
        },
        "example_params": {"query": "示例"}, "assumptions": [], "unresolved": [],
        "evidence_map": [{"action_index": 1, "source_actions": ["a1"], "basis": "实际输入", "side_effect": False}],
    }


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = self.root / "record"
        self.record.mkdir()
        self.write("session.json", {"schema_version": 1, "id": "r1", "status": "completed", "pages": {}, "start_url": "https://example.org/"})
        self.write("actions.json", [{"id": "a1", "kind": "fill", "value": "示例", "source_events": [1],
                                     "target": {"label": "查询"}, "observed_after": [{"sequence": n, "text": "正文" * 1000} for n in range(4)]}])
        (self.record / "events.jsonl").write_text(json.dumps({"type": "page_close", "page_id": "p1"}) + "\n", encoding="utf-8")

    def write(self, name, value):
        (self.record / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def test_http_generation_and_runtime_loading(self):
        def respond(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["response_format"], {"type": "json_object"})
            state = json.loads(payload["messages"][1]["content"])
            self.assertEqual(state["recording"]["id"], "r1")
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(draft(), ensure_ascii=False)}}],
                                           "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            model = Model(client, "https://example.org/v1", "test", "test-model")
            folder, report = generate(self.record, model, self.root / "output")
            second, _ = generate(self.record, model, self.root / "output")
        self.assertNotEqual(folder, second)
        skill = load_skill(str(folder / "SKILL.md"), {"query": "另一输入"})
        self.assertEqual(skill["goal"], "查询 另一输入")
        self.assertFalse(report["validated"])
        self.assertEqual(report["usage"]["total_tokens"], 120)
        self.assertTrue((folder / "generation.json").exists())

    def test_summary_and_sensitive_value(self):
        state = prepare_recording(self.record)
        observations = state["actions"][0]["observed_after"]
        self.assertEqual([o["sequence"] for o in observations], [0, 3])
        self.assertIn("截断", observations[0]["text"])
        self.assertEqual(state["page_events"][0]["type"], "page_close")
        self.write("actions.json", [{"id": "a1", "kind": "fill", "value": "secret", "target": {"sensitive": True}}])
        self.assertIsNone(prepare_recording(self.record)["actions"][0]["value"])

    def test_incomplete_recording_rejected(self):
        self.write("session.json", {"schema_version": 1, "status": "abandoned"})
        with self.assertRaises(ValueError):
            prepare_recording(self.record)

    def test_optional_guidance(self):
        guidance = {'name':'我的查询流程','description':'查找目标信息','parameters':'查询词可调整'}
        class GuidedModel:
            usage = {}
            def request(self, state, prompt):
                self.received = state['user_guidance']
                return draft()
        model = GuidedModel()
        folder, report = generate(self.record, model, self.root / 'guided', guidance)
        self.assertEqual(model.received, guidance)
        self.assertEqual(report['display_name'], guidance['name'])
        self.assertEqual(report['user_guidance'], guidance)
        self.assertEqual(normalize_guidance({'description':'  '}), {})
        with self.assertRaises(ValueError):
            normalize_guidance({'name': '名' * 81})

    def test_invalid_tool_and_parameter_rejected(self):
        for mutate in (lambda x: x["skill"]["actions"][0].update(tool="execute_code"),
                       lambda x: x["skill"]["actions"][0]["args"].update(value_ref="missing"),
                       lambda x: x["skill"].update(name="../../escape"),
                       lambda x: x["skill"]["actions"][0]["args"].update(unknown=True)):
            value = draft()
            mutate(value)
            with self.assertRaises((ValueError, TypeError)):
                validate(value)

    def test_missing_evidence_is_not_ready(self):
        value = draft()
        value["unresolved"] = [{"issue": "完成状态未知"}]
        self.assertEqual(validate(value)["status"], "needs_evidence")

    def test_upload_public_arguments(self):
        value = draft()
        value["skill"]["actions"] = [{"tool": "upload", "args": {"target": {"id": "file"}, "file_ids": ["u1"]}}]
        self.assertEqual(validate(value)["skill"]["actions"][0]["tool"], "upload")

    def test_missing_examples_and_invalid_file_mapping(self):
        value = draft()
        value["example_params"] = {}
        self.assertEqual(validate(value)["status"], "needs_evidence")
        value = draft()
        value["skill"]["file_params"] = {"uploads": ["unknown"]}
        with self.assertRaises(ValueError):
            validate(value)

    def test_stream_generation_and_usage(self):
        encoded = json.dumps(draft(), ensure_ascii=False)
        def respond(request):
            body = json.loads(request.content)
            self.assertTrue(body["stream"])
            self.assertEqual(body["reasoning_effort"], "low")
            chunks = [{"choices": [{"delta": {"reasoning_content": "not persisted"}}]},
                      *[{"choices": [{"index": 0, "delta": {"content": part}}]} for part in (encoded[:40], encoded[40:])],
                      {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                      {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}]
            data = ": heartbeat\n\n" + "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"
            return httpx.Response(200, text=data, headers={"content-type": "text/event-stream"})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            model = GenerationModel(client, "https://example.org", "test", "glm-5.3-flash")
            folder, report = generate(self.record, model, self.root / "stream")
        self.assertEqual(report["usage"]["total_tokens"], 30)
        self.assertNotIn("not persisted", (folder / "SKILL.md").read_text(encoding="utf-8"))

    def test_stream_rejects_interruption_and_truncation(self):
        for finish, done in ((None, False), ("length", True), ("stop", False)):
            data = "data: " + json.dumps({"choices": [{"delta": {"content": "{}"}, "finish_reason": finish}]}) + "\n\n"
            if done:
                data += "data: [DONE]\n\n"
            with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=data))) as client:
                model = GenerationModel(client, "https://example.org", "test", "other")
                with self.assertRaises(ValueError):
                    model.request({}, "test")

    def test_unknown_evidence_is_flagged_not_trusted(self):
        result = draft()
        result["evidence_map"][0]["source_actions"] = ["a1", "a99"]
        class FakeModel:
            usage = {}
            def request(self, state, prompt):
                return result
        folder, report = generate(self.record, FakeModel(), self.root / "unknown")
        self.assertEqual(report["status"], "needs_evidence")
        self.assertEqual(report["evidence_map"][0]["source_actions"], ["a1"])
        self.assertIn("a99", report["unresolved"][0]["issue"])

    def test_one_format_correction_and_failed_diagnostic(self):
        invalid = draft()
        invalid["skill"]["actions"][0]["args"]["visible"] = True
        class FakeModel:
            usage = {}
            def __init__(self, replies):
                self.replies = iter(replies)
                self.calls = 0
            def request(self, state, prompt):
                self.calls += 1
                return next(self.replies)
        model = FakeModel([invalid, draft()])
        folder, report = generate(self.record, model, self.root / "corrected")
        self.assertEqual(model.calls, 2)
        self.assertIn("visible", report["format_corrections"][0])
        model = FakeModel([invalid, invalid])
        with self.assertRaises(ValueError):
            generate(self.record, model, self.root / "failed")
        self.assertEqual(model.calls, 2)
        self.assertEqual(len(list((self.root / "failed").glob("*/generation.json"))), 1)
        self.assertEqual(list((self.root / "failed").glob("*/SKILL.md")), [])


if __name__ == "__main__":
    unittest.main()
