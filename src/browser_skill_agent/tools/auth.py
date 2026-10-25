"""仅运行时持有密码，模型只能请求登录接管。"""
class Authentication:
    def __init__(self, session):self.s=session
    def login(self):
        handler=getattr(self.s,'login_handler',None)
        if handler is None:raise ValueError('当前运行未配置登录接管')
        handler.ensure(force=True)
        return {'logged_in':True}
