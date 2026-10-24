"""验证默认保留可见浏览器、结果先输出，以及主动关闭开关。"""

import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread

import yaml


with TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "page.html").write_text('<p role="status">' + '可读内容' * 300 + '</p>', encoding="utf-8")
    skill = {"name": "lifecycle", "goal": "读取短摘录后保留页面", "start": (root / "page.html").as_uri(),
             "actions": [{"title": "短摘录", "tool": "read",
                          "args": {"target": {"role": "status"}, "max_chars": 600}}]}
    (root / "SKILL.md").write_text('---\n' + yaml.safe_dump(skill, allow_unicode=True) + '---\n', encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.startswith('MODEL_')}
    env['PYTHONIOENCODING'] = 'utf-8'
    command = [sys.executable, '-m', 'browser_skill_agent', 'SKILL.md', '--json']
    with (root / 'result.json').open('w', encoding='utf-8') as output:
        proc = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.PIPE,
                                stdout=output, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        messages = Queue()

        def collect():
            for line in proc.stderr:
                messages.put(line)
            messages.put(None)

        reader = Thread(target=collect, daemon=True)
        reader.start()
        try:
            while True:
                line = messages.get(timeout=30)
                assert line is not None, '程序未保持浏览器就退出了'
                if '浏览器保持打开' in line:
                    break
            assert proc.poll() is None, '默认模式应等待用户查看'
            result = json.loads((root / 'result.json').read_text(encoding='utf-8'))
            assert result['status'] == 'succeeded', result
            assert len(result['outputs'][0]['data']) == 600
            # 第一个窗口仍保留时，从同一工作目录启动第二个任务。
            parallel = subprocess.run(command + ['--headless'], cwd=root, env=env,
                                      capture_output=True, text=True, encoding='utf-8', timeout=30)
            assert parallel.returncode == 0, parallel.stderr
            assert json.loads(parallel.stdout)['status'] == 'succeeded'
            assert proc.poll() is None, '第二次启动不应关闭原有窗口'
            proc.stdin.write('\n')
            proc.stdin.flush()
            assert proc.wait(timeout=15) == 0
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            reader.join(timeout=3)
            proc.stdin.close()
            proc.stderr.close()
    proc = subprocess.run(command + ['--no-keep-open'], cwd=root, env=env,
                          capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert '浏览器保持打开' not in proc.stderr
    assert json.loads(proc.stdout)['status'] == 'succeeded'
    proc = subprocess.run(command + ['--headless', '--profile-dir', str(root / 'profile')],
                          cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert (root / 'profile' / 'Default').is_dir()
    proc = subprocess.run(command + ['--result-only'], cwd=root, env=env, input='\n',
                          capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert '已显示任务结束时的浏览器页面' in proc.stderr
    assert json.loads(proc.stdout)['status'] == 'succeeded'

print('通过：保留旧窗口时启动新任务、独立临时会话、显式固定目录、窗口保留与自动关闭、结果先输出、短摘录。')
