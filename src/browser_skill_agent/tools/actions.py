"""输入、点击及原生表单操作，自定义组件由多轮动作完成。"""


class Actions:
    def __init__(self, session):
        self.s = session

    def click(self, target, button="left", expect_popup=False):
        if not isinstance(expect_popup, bool):
            raise ValueError("expect_popup 必须为布尔值")
        locator = self.s.prepare(target)
        if expect_popup:
            display = getattr(self.s.context, '_bsa_display', None)
            minimized = display and display.is_minimized(self.s.current())
            with self.s.current().expect_popup() as pending:
                locator.click(button=button)
            self.s.page = pending.value
            self.s.register_page(self.s.page)
            self.s.page.wait_for_load_state("domcontentloaded")
            if minimized:
                display.conceal()
        else:
            locator.click(button=button)

    def double_click(self, target):
        self.s.prepare(target).dblclick()

    def hover(self, target):
        self.s.target(target).hover()

    def fill(self, target, value):
        self.s.prepare(target, editable=True).fill(value)

    def type_text(self, target, value):
        # 逐键输入会触发键盘事件，适用于自动补全；在已有内容后追加。
        self.s.prepare(target, editable=True).press_sequentially(value, delay=40)

    def press(self, target, key, expect_popup=False):
        if not isinstance(expect_popup, bool):
            raise ValueError("expect_popup 必须为布尔值")
        locator = self.s.prepare(target)
        if expect_popup:
            display = getattr(self.s.context, '_bsa_display', None)
            minimized = display and display.is_minimized(self.s.current())
            with self.s.current().expect_popup() as pending:
                locator.press(key)
            self.s.page = pending.value
            self.s.register_page(self.s.page)
            self.s.page.wait_for_load_state("domcontentloaded")
            if minimized:
                display.conceal()
        else:
            locator.press(key)

    def select(self, target, value=None, label=None):
        if (value is None) == (label is None):
            raise ValueError("select 只提供 value 或 label 中的一项，可为字符串或列表")
        locator = self.s.prepare(target)
        if locator.evaluate("el => el.tagName") != "SELECT":
            raise ValueError("这是自定义下拉组件：先 click 展开，再 snapshot 观察，最后点击选项；可搜索时先填写搜索框")
        return locator.select_option(value=value) if value is not None else locator.select_option(label=label)

    def set_checked(self, target, checked):
        self.s.prepare(target).set_checked(checked)

    def scroll(self, dy=600, target=None):
        if target is not None:
            self.s.target(target).scroll_into_view_if_needed()
        else:
            self.s.current().mouse.wheel(0, dy)

    def drag(self, source, target):
        self.s.target(source).drag_to(self.s.target(target))
