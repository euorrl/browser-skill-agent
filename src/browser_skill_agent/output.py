"""终端中文展示；不改变工具接口或 Runtime 返回值。"""

import json
import sys


TOOL_NAMES = {
    "click": "点击", "double_click": "双击", "hover": "悬停",
    "fill": "填写", "type_text": "逐字输入", "press": "按键",
    "select": "选择下拉选项", "set_checked": "设置勾选状态",
    "scroll": "滚动", "drag": "拖动", "goto": "打开网页",
    "back": "返回上一页", "reload": "刷新网页", "tabs": "管理标签页",
    "dialog": "处理弹窗", "read": "读取页面信息", "snapshot": "读取文字快照",
    "locate": "查找候选元素", "wait": "等待", "wait_for": "等待页面条件",
    "upload": "上传文件", "download": "下载文件", "finish": "结束任务",
}
STATUS_NAMES = {"succeeded": "已完成", "blocked": "未完成（遇到阻碍）", "failed": "运行失败"}
FIELD_NAMES = {
    "target": "目标", "role": "角色", "name": "名称", "label": "标签",
    "text": "文字", "placeholder": "占位文字", "test_id": "测试标识",
    "id": "元素标识", "within": "所在容器", "has_text": "包含文字",
    "visible": "可见", "nth": "序号", "frame": "框架", "url": "网址",
    "value_ref": "使用任务参数", "value": "值", "key": "按键",
    "state": "等待状态", "timeout": "超时秒数", "seconds": "秒数",
    "wait_after": "操作后等待", "kind": "读取类型", "checked": "勾选",
    "wait_response": "等待响应",
}


def compact(value, limit=400):
    """限制进度行长度，避免页面内容或异常堆栈淹没终端。"""
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[:limit] + "…"


def progress(message):
    print(message, file=sys.stderr, flush=True)


def describe(value):
    if isinstance(value, dict):
        return "；".join(f"{FIELD_NAMES.get(key, key)}：{describe(item)}" for key, item in value.items())
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def action_progress(turn, maximum, name, args):
    progress(f"[第 {turn}/{maximum} 轮] {TOOL_NAMES.get(name, '未知工具')}（{name}）")
    if args and name != "finish":
        progress(f"  操作信息：{compact(describe(args))}")


def result_progress(result, scripted=False):
    if not result.get("ok"):
        progress(f"  操作报错：{compact(result.get('error', '未知原因'))}")
        progress("  已停止后续步骤；报错不代表操作一定未生效。" if scripted else "  将重新观察页面；报错不代表操作一定未生效。")
    elif result.get("after_wait", {}).get("ok") is False:
        progress("  操作已执行，但后续等待未满足；已停止，不会重复提交。" if scripted else "  操作已执行，但后续等待未满足；下一轮重新观察，不能直接重复提交。")
        progress(f"  等待详情：{compact(result['after_wait'].get('error', '未知原因'))}")
    else:
        suffix = "，后续等待条件已满足" if "after_wait" in result else ""
        progress(f"  工具执行成功{suffix}。")


def print_result(result, as_json=False):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"\n运行结果：{STATUS_NAMES.get(result['status'], result['status'])}")
    if "turns" in result:
        label = "执行步数" if result.get("mode") == "script" else "决策轮数"
        print(f"{label}：{result['turns']}")
    if "elapsed_seconds" in result:
        print(f"总耗时：{result['elapsed_seconds']:.1f} 秒")
    if result.get("url"):
        print(f"最后页面：{result['url']}")
    print(f"结果说明：\n{result.get('message', '未提供说明')}")
    for item in result.get("outputs", []):
        data = item["data"]
        print(f"\n{item['title']}：\n{data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2)}")
        if item.get("url"):
            print(f"来源：{item['url']}")
    usage = result.get("usage")
    if usage is not None:
        if usage["requests"] == 0:
            print("Token 消耗：0（未请求 LLM）")
        elif usage["reported_requests"] == 0:
            print(f"Token 消耗：未知（已尝试 {usage['requests']} 次请求，未取得服务端用量）")
        else:
            print(f"Token 消耗：输入 {usage['prompt_tokens']}，输出 {usage['completion_tokens']}，合计 {usage['total_tokens']}")
            if usage["reported_requests"] < usage["requests"]:
                print(f"用量不完整：仅取得 {usage['reported_requests']}/{usage['requests']} 次请求的统计，以上为已知累计值。")
