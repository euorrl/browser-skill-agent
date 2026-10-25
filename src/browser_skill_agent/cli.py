"""命令行入口；从 .env 或环境变量读取模型配置。"""

import argparse
import getpass
import yaml
import os
from pathlib import Path
import sys
from time import monotonic
from contextlib import nullcontext

import httpx
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from .runtime import Model, run, run_script
from .login import LoginHandler, secret_names
from .skill import load_skill
from .tools import BrowserTools
from .output import print_result, progress
from .browser_display import RESULT_ONLY_ARGS, ResultOnlyDisplay
from .approval import ApprovalPolicy
from .tools.files import FileOptions


ROOT = Path.cwd()


def parameter(text: str) -> tuple[str, str]:
    name, sep, value = text.partition("=")
    if not name or not sep:
        raise argparse.ArgumentTypeError("请使用 --param 参数名=参数值")
    return name, value


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        from .sandbox.cli import main as validate_main
        return validate_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "studio":
        from .studio.app import main as studio_main
        return studio_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        from .generation.generator import main as generate_main
        return generate_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "record":
        from .recording.recorder import main as record_main
        return record_main(sys.argv[2:])
    parser = argparse.ArgumentParser(description="执行文字浏览器 Skill",
                                     epilog="录制用户操作：python -m browser_skill_agent record [--url 起始网址]")
    parser.add_argument("skill", help="SKILL.md 文件路径")
    parser.add_argument("--param", action="append", type=parameter, default=[],
                        help="任务参数，格式为 参数名=参数值，可重复指定")
    parser.add_argument("--max-steps", type=int, default=30, help="最大执行步数，LLM 模式含 finish 和无效计划，默认 30")
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--headless", action="store_true", help="后台运行；需要人工登录时显示同一浏览器，结束后关闭")
    display.add_argument("--result-only", action="store_true", help="执行期间窗口最小化，可从任务栏恢复，结束后显示最终页面")
    parser.add_argument("--keep-open", action=argparse.BooleanOptionalAction, default=True,
                        help="默认结束后保留可见浏览器，回车关闭；--no-keep-open 自动关闭，无界面模式不等待")
    parser.add_argument("--json", action="store_true", help="将最终结果输出为 JSON，供其他程序读取")
    parser.add_argument("--llm", action="store_true", help="启用 LLM 决策；默认直接执行 Skill 的 actions，无需 API 密钥")
    parser.add_argument("--approval", choices=("human", "ai", "allow"), default="human",
                        help="关键操作授权：human 人工确认（默认）、ai 模型审核、allow 全部允许")
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
    policy = None
    needs_model = args.llm or args.approval == "ai"
    reported = False
    tools = None

    def report(result):
        nonlocal reported
        result["elapsed_seconds"] = round(monotonic() - started, 1)
        result["mode"] = "script" if not args.llm else "llm"
        result["usage"] = dict(model.usage) if model else {
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
            "requests": 0, "reported_requests": 0,
        }
        result["approval"] = {"mode": args.approval, "decisions": policy.decisions if policy else []}
        if tools is not None and getattr(tools.session, "login_handler", None):
            result = tools.session.login_handler.redact(result)
        print_result(result, as_json=args.json)
        sys.stdout.flush()
        reported = True
    try:
        supplied = dict(args.param)
        raw = yaml.safe_load(Path(args.skill).read_text(encoding="utf-8-sig").split("---",2)[1])
        for name in secret_names(raw):
            if not supplied.get(name):
                supplied[name] = getpass.getpass(f"请输入 {name}（不保存，留空改为人工登录）：")
        skill = load_skill(args.skill, supplied)
        file_options = FileOptions.from_skill(skill)
        settings = {name: os.environ.get(name, "") for name in (
            "MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME",
        )}
        missing = [name for name, value in settings.items() if not value]
        if missing and needs_model:
            raise ValueError(f"请在 .env 或环境变量中配置模型：{', '.join(missing)}")
        if not args.llm and (not isinstance(skill.get("actions"), list) or not skill["actions"]):
            raise ValueError("此 Skill 尚未定义 actions，默认模式无法执行；请添加结构化工具步骤，或使用 --llm")

        progress(f"任务：{skill['name']}\n目标：{skill['goal']}")
        progress(f"执行模式：{'脚本执行（不使用 LLM 规划）' if not args.llm else 'LLM 决策'}")
        progress(f"授权模式：{ {'human': '关键操作由人工确认', 'ai': '关键操作由 AI 审核（会调用模型）', 'allow': '全部允许，不进行授权确认'}[args.approval] }")
        display_name = "结束后显示" if args.result_only else ("后台运行（可人工登录）" if args.headless else "全程显示")
        progress(f"浏览器模式：{display_name}；执行上限：{args.max_steps}")
        profile_dir = str(args.profile_dir.resolve()) if args.profile_dir else ""
        progress(f"浏览器会话：{profile_dir or '本次独立临时会话'}")
        if file_options.uploads:
            progress("本次可上传文件：\n" + "\n".join(f"  {key}：{path}" for key, path in file_options.uploads.items()))
        progress(f"下载目录：{file_options.download_dir}")
        progress("正在启动浏览器…")
        with (httpx.Client(timeout=120) if needs_model else nullcontext()) as client, sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                # 空路径由 Playwright 创建并清理独立临时目录。
                user_data_dir=profile_dir,
                channel="msedge",
                headless=False,
                ignore_https_errors=args.ignore_https_errors,
                args=RESULT_ONLY_ARGS if args.result_only or args.headless else [],
            )
            try:
                presentation = None
                tools = None
                try:
                    if args.result_only or args.headless:
                        presentation = ResultOnlyDisplay(context)
                    page = context.pages[0] if context.pages else context.new_page()
                    if needs_model:
                        model = Model(client, settings["MODEL_BASE_URL"],
                                      settings["MODEL_API_KEY"], settings["MODEL_NAME"])

                    def show_for_approval(active_page):
                        if presentation:
                            presentation.reveal(active_page)

                    def hide_after_approval():
                        if presentation:
                            presentation.conceal()

                    policy = ApprovalPolicy(args.approval, skill, model.review if model else None,
                                            show_for_approval, hide_after_approval)
                    tools = BrowserTools(page, approval=policy, file_options=file_options)
                    def login_prompt(message, details):
                        progress(message + "\n完成后按回车继续；输入 n 停止。")
                        try:return input().strip().lower() not in ("n", "no")
                        except (EOFError, KeyboardInterrupt):return False
                    tools.session.login_handler = LoginHandler(tools, skill, supplied, login_prompt, presentation)
                    if not args.llm:
                        result = run_script(skill, tools, args.max_steps)
                    else:
                        result = run(skill, tools, model, args.max_steps)
                except Exception as exc:
                    result = {"status": "failed", "message": f"运行遇到异常（{type(exc).__name__}）：{exc}"}
                report(result)
                if presentation is not None and not args.headless:
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
