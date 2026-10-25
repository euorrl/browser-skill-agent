"""显式发起双模式验证，会调用配置的模型服务。"""
import argparse
import getpass
import yaml
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
from ..generation.model import GenerationModel
from ..cli import parameter
from .runner import validate_flow
from ..login import secret_names


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skill', type=Path)
    parser.add_argument('--param', action='append', type=parameter, default=[])
    parser.add_argument('--checks', type=Path, help='固定验收 JSON 列表；省略时由模型根据原任务制定')
    parser.add_argument('--max-repairs', type=int, default=2, choices=range(4))
    parser.add_argument('--allow-files', action=argparse.BooleanOptionalAction, default=True, help='默认允许有限次数上传下载；--no-allow-files 暂停文件操作')
    parser.add_argument('--output', type=Path, default=Path('data/validations'))
    args = parser.parse_args(argv)
    load_dotenv()
    config = [os.getenv(k) for k in ('MODEL_BASE_URL','MODEL_API_KEY','MODEL_NAME')]
    if not all(config):
        parser.error('请先配置 .env 模型服务')
    sample = args.skill.parent/'example_params.json'
    defaults = json.loads(sample.read_text(encoding='utf-8')) if sample.exists() else {}
    defaults.update(dict(args.param))
    raw = yaml.safe_load(args.skill.read_text(encoding='utf-8-sig').split('---',2)[1])
    credentials = {}
    for name in secret_names(raw):
        credentials[name] = defaults.pop(name, '') or getpass.getpass(f'请输入 {name}（仅本次验证）：')
        defaults[name] = ''
    def login_prompt(message, details):
        print(message)
        try:return input('完成后回车继续，n 停止：').strip().lower() not in ('n','no')
        except (EOFError, KeyboardInterrupt):return False
    checks = json.loads(args.checks.read_text(encoding='utf-8')) if args.checks else None
    with httpx.Client(timeout=60) as client:
        model = GenerationModel(client, *config, timeout=120, progress=print)
        report = validate_flow(args.skill, defaults, model, args.output, checks=checks,
                               max_repairs=args.max_repairs, allow_files=args.allow_files, progress=print,
                               credentials=credentials, login_prompt=login_prompt)
    print(json.dumps({k: report.get(k) for k in ('status','reason','folder','usage','elapsed_seconds')}, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'passed' else 1
