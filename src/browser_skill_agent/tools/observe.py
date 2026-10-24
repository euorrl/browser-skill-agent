"""页面文字、区域快照与控件状态读取。"""

from .readiness import settle

class Observation:
    def __init__(self, session):
        self.s = session

    def snapshot(self, target=None, frame=None):
        locator = self.s.target(target) if target else self.s.frame(frame).locator("body")
        text = locator.aria_snapshot()
        return {"text": text[:24000], "truncated": len(text) > 24000}

    def observe(self):
        for _ in range(2):
            page = self.s.current()
            readiness = settle(page)
            result = {"url": page.url, "readiness": readiness, "tabs": self.s.tab_list(),
                      "frames": self.s.frame_list(), "dialog": self.s.last_dialog}
            try:
                result.update(self.snapshot())
            except Exception as exc:
                result.update(text="", error=str(exc))
            if not page.is_closed() and page.url == result["url"]:
                return result
        # 不把跳转前的地址和跳转后的内容拼成同一个现场。
        return {"url": self.s.current().url, "text": "",
                "readiness": {"settled": False}, "error": "观察期间页面持续跳转，请重新等待和观察"}

    def locate(self, target, limit=10):
        """返回真实候选信息；只建议当前唯一的 ID 或测试标识，不猜测序号。"""
        locator = self.s.target(target)
        locator.first.wait_for(state="attached")
        count = locator.count()
        candidates = []
        for index in range(min(count, max(1, min(limit, 20)))):
            element = locator.nth(index)
            info = element.evaluate("""el => ({tag: el.tagName.toLowerCase(),
                id: el.id, test_id: el.getAttribute('data-testid'),
                label: el.getAttribute('aria-label') || [...(el.labels || [])].map(x => x.innerText).join(' '),
                text: (el.innerText || '').slice(0,300), placeholder: el.getAttribute('placeholder'),
                disabled: el.matches(':disabled') || el.getAttribute('aria-disabled') === 'true'})""")
            info.update(index=index, visible=element.is_visible(), suggested_target=None)
            for key in ("test_id", "id"):
                if info.get(key):
                    proposal = {key: info[key]}
                    # 容器和框架条件原样保留，防止建议跳出原定位范围。
                    for scope in ("within", "frame"):
                        if scope in target:
                            proposal[scope] = target[scope]
                    if self.s.target(proposal).count() == 1:
                        info["suggested_target"] = proposal
                        break
            candidates.append(info)
        return {"count": count, "candidates": candidates,
                "hint": "按标签和容器选择；动态列表的 index 仅作观察参考，不是稳定身份"}

    def read(self, target, kind="text", attribute=None, max_chars=16000):
        locator = self.s.target(target)
        if kind == "text":
            return locator.inner_text()[:max(1, min(int(max_chars), 16000))]
        if kind == "value":
            return locator.input_value()
        if kind == "count":
            return locator.count()
        if kind == "checked":
            return locator.is_checked()
        if kind == "attribute":
            if attribute not in ("href", "title", "aria-expanded", "aria-selected", "aria-label",
                                 "aria-controls", "aria-current", "aria-disabled", "disabled", "data-test", "data-testid", "type", "name"):
                raise ValueError("不支持读取该属性")
            return locator.get_attribute(attribute)
        if kind == "options":
            locator.wait_for(state="attached")
            # 固定只读脚本用于原生 select；不接受模型提供的脚本。
            return locator.locator("option").evaluate_all(
                "els => els.map(e => ({label:e.label,value:e.value,selected:e.selected,disabled:e.disabled}))")
        if kind == "state":
            try:
                editable = locator.is_editable()
            except Exception:
                editable = False
            return {"visible": locator.is_visible(), "enabled": locator.is_enabled(),
                    "editable": editable}
        raise ValueError("不支持的 read 类型")
