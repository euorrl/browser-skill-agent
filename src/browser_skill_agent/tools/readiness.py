"""页面短时稳定性观察：仅提供就绪线索，不判断业务完成。"""

from time import monotonic


WATCH = """() => {
  if (!window.__browserSkillReadiness) {
    const state = {changed: performance.now()};
    new MutationObserver(() => {state.changed = performance.now();}).observe(document, {
      subtree: true, childList: true, characterData: true, attributes: true,
      attributeFilter: ['disabled','hidden','aria-busy','aria-expanded','aria-disabled','class','style']
    });
    window.__browserSkillReadiness = state;
  }
  const visible = el => !!(el.getClientRects().length) && getComputedStyle(el).visibility !== 'hidden';
  return {document_state: document.readyState,
    busy: [...document.querySelectorAll('[aria-busy="true"]')].some(visible),
    quiet_ms: performance.now() - window.__browserSkillReadiness.changed};
}"""


def settle(page, timeout=2):
    deadline = monotonic() + timeout
    state = {}
    while monotonic() < deadline:
        try:
            state = page.evaluate(WATCH)
            if state["document_state"] != "loading" and not state["busy"] and state["quiet_ms"] >= 200:
                return {"settled": True, **state}
        except Exception as exc:
            state = {"error": str(exc)}
        if page.is_closed():
            break
        page.wait_for_timeout(100)
    return {"settled": False, **state}
