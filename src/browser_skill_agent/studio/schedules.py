"""本地单次定时计划；工作台打开时触发，不自动补跑关机期间任务。"""
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4


def utcnow():
    return datetime.now(timezone.utc)


class Schedules:
    def __init__(self, root, flows):
        self.path = root / 'data/studio/schedules.json'
        self.flows = flows
        self.items = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else []
        for item in self.items:
            if item['status'] == 'running':
                item.update(status='interrupted', message='工作台已退出，未自动重试，避免重复操作。')
            elif item['status'] in ('scheduled', 'waiting') and datetime.fromisoformat(item['at']) <= utcnow():
                item.update(status='missed', message='工作台未运行期间已过期，请重新设置时间。')
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)

    def get(self, ident):
        return next(item for item in self.items if item['id'] == ident)

    def fingerprint(self, flow_id):
        return hashlib.sha256(self.flows.path(flow_id).read_bytes()).hexdigest()

    def put(self, data):
        flow = self.flows.get(data['flow_id'])
        at = datetime.fromisoformat(data['at'])
        if at.tzinfo is None or at <= utcnow():
            raise ValueError('请选择未来的时间（包含时区）。')
        params = data.get('params', {})
        if not isinstance(params, dict) or set(params) != set(flow['defaults']):
            raise ValueError('请配置完整的流程参数。')
        if any(not isinstance(v, str) or not v.strip() for k,v in params.items() if k not in flow.get('secret_params', [])):
            raise ValueError('运行参数不能为空。')
        if any(params.get(k) for k in flow.get('secret_params', [])):
            raise ValueError('定时计划不保存密码，请在流程参数面板提前填写本次会话密码。')
        approval = data.get('approval', 'human')
        if approval not in ('human', 'ai', 'allow'):
            raise ValueError('未知授权模式。')
        for key in ('llm', 'background', 'close_after', 'enabled'):
            if not isinstance(data.get(key), bool):
                raise ValueError('请配置运行选项和计划启用状态。')
        old = self.get(data['id']) if data.get('id') else None
        if old and old['status'] == 'running':
            raise ValueError('正在执行的计划不能修改。')
        item = dict(id=old['id'] if old else uuid4().hex, flow_id=flow['id'], name=flow['name'],
                    at=at.astimezone(timezone.utc).isoformat(), params=dict(params), approval=approval,
                    llm=data['llm'], background=data['background'], close_after=data['close_after'],
                    status='scheduled' if data['enabled'] else 'paused', message='', fingerprint=self.fingerprint(flow['id']))
        if old: self.items[self.items.index(old)] = item
        else: self.items.append(item)
        self.save()
        return item

    def remove(self, ident):
        item = self.get(ident)
        if item['status'] == 'running':
            raise ValueError('正在执行的计划不能删除。')
        self.items.remove(item)
        self.save()
