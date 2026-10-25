"""流程级登录接管。凭据只保留在运行时，不进入模型上下文。"""
from urllib.parse import urlsplit
import re
from copy import deepcopy

MASK = "[密码由运行时保管]"


def secret_names(skill):
    config = skill.get("login") or {}
    return {config["password_param"]} if isinstance(config, dict) and config.get("password_param") else set()


def public_params(skill, params):
    return {k: (MASK if k in secret_names(skill) else v) for k,v in params.items()}


def validate_login(skill):
    config = skill.get('login')
    if config is None:
        return
    allowed = {'origins','username_param','password_param','username_target','password_target','submit_target','detect','success'}
    if not isinstance(config, dict) or set(config)-allowed:
        raise ValueError('login 配置字段无效')
    if config.get('username_param') == config.get('password_param') and config.get('password_param'):
        raise ValueError('账号和密码不能引用同一参数')
    for key in ('username_param','password_param'):
        if key in config and config[key] not in skill.get('params', []):
            raise ValueError('登录参数必须在 params 中声明')
    origins = config.get('origins', [])
    if not isinstance(origins, list) or any(not isinstance(x,str) or urlsplit(x).scheme not in ('http','https') or not urlsplit(x).netloc or urlsplit(x).path not in ('','/') or urlsplit(x).query or urlsplit(x).fragment or urlsplit(x).username for x in origins):
        raise ValueError('login.origins 必须是明确的网站来源，例如 https://example.com，不支持通配符')
    if any('*' in x for x in origins):
        raise ValueError('登录来源不支持通配符')
    for key in ('username_target','password_target','submit_target','detect','success'):
        if key in config and not isinstance(config[key],dict):
            raise ValueError('登录定位和成功条件必须是对象')
    if 'success' in config:
        from inspect import signature
        from .tools.waiting import Waiting
        signature(Waiting.wait_for).bind(None, **config['success'])
        if not (config['success'].get('target') or config['success'].get('url')):
            raise ValueError('登录成功条件需要目标或 URL')
    for refs in skill.get('file_params', {}).values():
        if secret_names(skill).intersection(refs if isinstance(refs,list) else [refs]):
            raise ValueError('密码不能用作文件参数')
    for action in skill.get('actions', []):
        if action.get('args',{}).get('value_ref') in secret_names(skill):
            raise ValueError('密码只能由 login 工具填写，不能通过 fill/value_ref 使用')
    import json
    for name in secret_names(skill):
        if re.search(r'{{\s*'+re.escape(name)+r'\s*}}',json.dumps(skill,ensure_ascii=False)):
            raise ValueError('密码不能插入模板或普通工具参数')


class LoginHandler:
    def __init__(self, tools, skill, credentials=None, prompt=None, display=None):
        self.tools=tools
        self.config=deepcopy(skill.get('login') or {})
        self.params=dict(credentials or {})
        self.prompt=prompt
        self.display=display
        self.active=False
        self.attempted=set()
        self.generation=0

    def redact(self, value):
        secrets=[self.params.get(self.config.get('password_param'))]
        if isinstance(value,str):
            for secret in secrets:
                if secret and secret != MASK:value=value.replace(secret,'[已隐藏]')
            return value
        if isinstance(value,list):return [self.redact(x) for x in value]
        if isinstance(value,dict):return {k:self.redact(v) for k,v in value.items()}
        return value

    def html_frames(self):
        # PDF 内嵌查看器和扩展页不是登录表单，避免向其发送 DOM 查询。
        return [frame for frame in self.tools.page.frames
                if urlsplit(frame.url).scheme in ('http', 'https', 'file')
                and not urlsplit(frame.url).path.lower().endswith('.pdf')]

    def needed(self):
        page=self.tools.page
        if page.is_closed():return False
        if self.config.get('detect'):
            try:
                if self.tools.target(self.config['detect']).is_visible():return True
            except Exception:pass
        for frame in self.html_frames():
            try:
                if frame.locator('input[autocomplete=one-time-code]:visible').count():return True
                if frame.locator('input[type=password]:visible').count():
                    login_button=frame.get_by_role('button',name=re.compile(r'^(登录|登陆|sign in|log in)$',re.I))
                    if login_button.count() and login_button.first.is_visible():return True
                heading=frame.get_by_role('heading').filter(has_text=re.compile(r'^(?:(?:账号|账户|手机|扫码|密码|用户|统一身份)\s*)?(?:登录|登陆|sign in|log in)[：:！!。\s]*$',re.I))
                if heading.count() and heading.first.is_visible():return True
                if re.search(r'/(login|signin|passport)(?:[/?#]|$)',frame.url,re.I):
                    text=frame.locator('body').inner_text(timeout=1000)
                    if re.search('登录|扫码|验证码|sign in|log in',text,re.I):return True
            except Exception:pass
        return False

    def ready(self):
        if self.config.get('success'):
            from .tools.waiting import Waiting
            try:
                Waiting(self.tools.session).wait_for(**{**self.config['success'],'timeout':2})
                return not self.needed()
            except Exception:return False
        return not self.needed()

    def auto(self):
        c=self.config
        username=self.params.get(c.get('username_param'),'')
        password=self.params.get(c.get('password_param'),'')
        if not username or not password or password==MASK or not all(c.get(k) for k in ('username_target','password_target','submit_target','success')):
            return False
        for frame in self.html_frames():
            if frame.locator('input[autocomplete=one-time-code]:visible,input[name*=captcha i]:visible,input[id*=captcha i]:visible').count():return False
        locators=[self.tools.target(c[k]) for k in ('username_target','password_target','submit_target')]
        origins={x.rstrip('/') for x in c.get('origins',[])}
        for locator in locators:
            if locator.count()!=1 or not locator.is_visible():return False
            origin=locator.evaluate('el => new URL(el.ownerDocument.URL).origin')
            if origin not in origins:return False
        if locators[1].get_attribute('type') != 'password':return False
        origin=locators[1].evaluate('el => new URL(el.ownerDocument.URL).origin')
        if origin in self.attempted:return False
        self.attempted.add(origin)  # 自动提交每个来源至多一次，不重试密码。
        try:
            locators[0].fill(username)
            locators[1].fill(password)
            locators[2].click()
            return self.ready()
        except Exception:
            return False  # 不返回包含 fill 参数的 Playwright 异常。

    def ensure(self, force=False):
        if self.active or (not force and not self.needed()):return False
        if force and self.config.get("success") and not self.needed() and self.ready():return False
        self.active=True
        try:
            if self.auto():
                self.generation+=1
                return True
            if self.prompt is None:raise RuntimeError('需要人工登录，当前执行入口未提供人工接管')
            if self.display:self.display.reveal(self.tools.page)
            while True:
                accepted=self.prompt('请在任务浏览器完成登录，然后点击“登录完成，继续”。',{'url':self.tools.page.url})
                if not accepted:raise RuntimeError('用户停止登录，流程已暂停结束；没有重复上一操作')
                if self.ready():break
            if self.display:self.display.conceal()
            self.generation+=1
            return True
        finally:self.active=False
