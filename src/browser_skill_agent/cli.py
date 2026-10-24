"""命令行入口；从 .env 或环境变量读取模型配置。"""

import argparse
import os
from pathlib import Path
import sys
from time import monotonic
from contextlib import nullcontext

import httpx
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from .runtime import Model, run, run_script
from .skill import load_skill
from .tools import BrowserTools
from .output import print_result, progress
from .browser_display import RESULT_ONLY_ARGS, ResultOnlyDisplay


ROOT = Path.cwd()


def parameter(text: str) -> tuple[str, str]:
    name, sep, value = text.partition("=")
    if not name or not sep:
        raise argparse.ArgumentTypeError("请使用 --param 参数名=参数值")
    return name, value


def main() -> int:
    parser = argparse.ArgumentParser(description="执行文字浏览器 Skill")
    parser.add_argument("skill", help="SKILL.md 文件路径")
    parser.add_argument("--param", action="append", type=parameter, default=[],
                        help="任务参数，格式为 参数名=参数值，可重复指定")
    parser.add_argument("--max-steps", type=int, default=30, help="最大脚本步数或 LLM 决策轮数，默认 30")
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--headless", action="store_true", help="全程无界面运行浏览器")
    display.add_argument("--result-only", action="store_true", help="执行期间窗口位于屏幕外，结束后显示最终页面")
    parser.add_argument("--keep-open", action=argparse.BooleanOptionalAction, default=True,
                        help="默认结束后保留可见浏览器，回车关闭；--no-keep-open 自动关闭，无界面模式不等待")
    parser.add_argument("--json", action="store_true", help="将最终结果输出为 JSON，供其他程序读取")
    parser.add_argument("--llm", action="store_true", help="启用 LLM 决策；默认直接执行 Skill 的 actions，无需 API 密钥")
    parser.add_argument("--profile-dir", type=Path,
                        help="可选的固定浏览器会话目录；默认每次使用独立临时目录，避免保留窗口时冲突")
    parser.add_argument("--ignore-https-errors", action="store_true",
                        help="忽略网页 HTTPS 证书错误，仅在信任目标网站时使用")
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps 必须为正整数")
    if args.result_only and not args.keep_open:
        parser.error("--result-only 需要保留最终窗口，不能与 --no-keep-open 一起使用")

    load_dotenv(ROOT / ".env")
    started = monotonic()
    model = None
    reported = False

    def report(result):
        nonlocal reported
        result["elapsed_seconds"] = round(monotonic() - started, 1)
        result["mode"] = "script" if not args.llm else "llm"
        result["usage"] = dict(model.usage) if model else {
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
            "requests": 0, "reported_requests": 0,
        }
        print_result(result, as_json=args.json)
        sys.stdout.flush()
        reported = True
    try:
        skill = load_skill(args.skill, dict(args.param))
        settings = {name: os.environ.get(name, "") for name in (
            "MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME",
        )}
        missing = [name for name, value in settings.items() if not value]
        if missing and args.llm:
            raise ValueError(f"请在 .env 或环境变量中配置模型：{', '.join(missing)}")
        if not args.llm and (not isinstance(skill.get("actions"), list) or not skill["actions"]):
            raise ValueError("此 Skill 尚未定义 actions，默认模式无法执行；请添加结构化工具步骤，或使用 --llm")

        progress(f"任务：{skill['name']}\n目标：{skill['goal']}")
        progress(f"执行模式：{'脚本执行（不使用 LLM）' if not args.llm else 'LLM 决策'}")
        display_name = "结束后显示" if args.result_only else ("无界面运行" if args.headless else "全程显示")
        progress(f"浏览器模式：{display_name}；执行上限：{args.max_steps}")
        profile_dir = str(args.profile_dir.resolve()) if args.profile_dir else ""
        progress(f"浏览器会话：{profile_dir or '本次独立临时会话'}")
        progress("正在启动浏览器…")
        with (nullcontext() if not args.llm else httpx.Client(timeout=120)) as client, sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                # 空路径由 Playwright 创建并清理独立临时目录。
                user_data_dir=profile_dir,
                channel="msedge",
                headless=args.headless,
                ignore_https_errors=args.ignore_https_errors,
                args=RESULT_ONLY_ARGS if args.result_only else [],
            )
            try:
                presentation = None
                tools = None
                try:
                    if args.result_only:
                        presentation = ResultOnlyDisplay(context)
                    page = context.pages[0] if context.pages else context.new_page()
                    tools = BrowserTools(page)
                    if not args.llm:
                        result = run_script(skill, tools, args.max_steps)
                    else:
                        model = Model(client, settings["MODEL_BASE_URL"],
                                      settings["MODEL_API_KEY"], settings["MODEL_NAME"])
                        result = run(skill, tools, model, args.max_steps)
                except Exception as exc:
                    result = {"status": "failed", "message": f"运行遇到异常（{type(exc).__name__}）：{exc}"}
                report(result)
                if presentation is not None:
                    try:
                        presentation.show(tools.page if tools and context.pages else None)
                        progress("已显示任务结束时的浏览器页面，原有标签页与页面状态已保留。")
                    except Exception as exc:
                        progress(f"无法显示最终窗口：{exc}")
                if args.keep_open and not args.headless:
                    progress("任务已结束，浏览器保持打开，可查看所有标签页。按回车关闭浏览器并退出。")
                    try:
                        input()
                    except EOFError:
                        progress("终端输入已关闭，结束浏览器会话。自动化运行可使用 --no-keep-open。")
                    except KeyboardInterrupt:
                        progress("正在关闭浏览器。")
            finally:
                context.close()
    except Exception as exc:
        result = {"status": "failed", "message": f"运行遇到异常（{type(exc).__name__}），任务未正常结束。\n错误详情：{exc}"}

    if not reported:
        report(result)
    return 0 if result["status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
