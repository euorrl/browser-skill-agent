"""长草稿使用流式传输，只累计最终正文，不展示或保存推理文本。"""
import json
from time import monotonic

from ..runtime import Model


class GenerationModel(Model):
    def __init__(self, client, base_url, api_key, model, timeout=300, progress=None):
        super().__init__(client, base_url, api_key, model)
        self.timeout = timeout
        self.progress = progress or (lambda message: None)

    def check_cancelled(self):
        cancel = getattr(self, "cancel", None)
        if cancel is not None and cancel.is_set():
            raise RuntimeError("流程生成已取消")

    def request(self, state, prompt):
        self.check_cancelled()
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": prompt},
                         {"role": "user", "content": json.dumps(state, ensure_ascii=False)}],
            "response_format": {"type": "json_object"},
            "stream": True, "stream_options": {"include_usage": True}, "max_tokens": 16384,
        }
        # GLM 5.3 强制思考，只降低强度；不向其他模型发送专用参数。
        if self.model.lower() in {"glm-5.3", "glm-5.3-flash"}:
            body["reasoning_effort"] = "low"
        self.usage["requests"] += 1
        start = last = monotonic()
        content, usage, finish, done = [], None, None, False
        try:
            with self.client.stream("POST", self.url, headers={"Authorization": f"Bearer {self.api_key}"}, json=body) as response:
                response.raise_for_status()
                self.progress("模型已连接，正在接收生成结果…")
                for line in response.iter_lines():
                    self.check_cancelled()
                    now = monotonic()
                    if now - start > self.timeout:
                        raise TimeoutError("模型生成超过总时间上限；未保存不完整草稿")
                    if now - last >= 15:
                        self.progress(f"生成中：已等待 {now-start:.0f} 秒，已接收正文 {sum(map(len, content))} 字符")
                        last = now
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        done = True
                        break
                    if not data:
                        continue
                    chunk = json.loads(data)
                    if chunk.get("error"):
                        raise ValueError("模型流返回错误，未生成完整草稿")
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                    for choice in chunk.get("choices", []):
                        if choice.get("index", 0) != 0:
                            continue
                        text = choice.get("delta", {}).get("content")
                        if isinstance(text, str):
                            content.append(text)
                        finish = choice.get("finish_reason") or finish
        finally:
            if isinstance(usage, dict) and all(isinstance(usage.get(k), int) for k in
                    ("prompt_tokens", "completion_tokens", "total_tokens")):
                self.usage["reported_requests"] += 1
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    self.usage[key] += usage[key]
        self.check_cancelled()
        if finish == "length":
            raise ValueError("模型输出达到 Token 上限，草稿不完整；请缩短录制任务")
        if not done or finish != "stop":
            raise ValueError(f"模型流未正常完成（finish_reason={finish}），未保存草稿")
        if not "".join(content).strip():
            raise ValueError("模型未返回 JSON 正文，未保存草稿")
        return json.loads("".join(content))
