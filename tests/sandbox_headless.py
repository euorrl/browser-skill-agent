"""验证默认无头启动，以及人工登录不会等待隐藏窗口。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from playwright.sync_api import BrowserType
from sandbox import Handler, definition, save_skill, FakeModel, checks
from browser_skill_agent.sandbox import validate_flow


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    launches = []
    original = BrowserType.launch
    def launch(self, **kwargs):
        launches.append(kwargs)
        return original(self, **kwargs)
    def prompt(*args):
        raise AssertionError('无头验证不应请求人工操作不可见窗口')
    try:
        with TemporaryDirectory() as temp, patch.object(BrowserType, 'launch', launch):
            root = Path(temp)
            path = root / 'SKILL.md'
            skill = definition(f'http://127.0.0.1:{server.server_port}/')
            save_skill(path, skill)
            result = validate_flow(path, {'query': '人工智能'}, FakeModel(), root/'runs', checks=checks(), login_prompt=prompt)
            assert result['status'] == 'passed', result
            assert result['headless'] is True
            skill['login'] = {'detect': {'id': 'query'}}
            save_skill(path, skill)
            result = validate_flow(path, {'query': '人工智能'}, FakeModel(), root/'runs', checks=checks(), login_prompt=prompt)
            assert result['status'] == 'blocked', result
            assert '无头验证遇到人工登录' in result['reason'], result
            assert not result['repairs']
            assert all(item['headless'] is True and item['args'] == [] for item in launches)
            assert len(launches) == 2
        print('通过：默认 headless、双模式执行、人工登录明确停止且不自动修复。')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
