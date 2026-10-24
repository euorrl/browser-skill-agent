"""显式运行全部中文 Skill 的双模式评测，会消耗真实模型 Token。"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys

from live_chinese_skills import CASES, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", type=Path)
    parser.add_argument("--modes", nargs="+", choices=["script", "llm"], default=["script", "llm"])
    args = parser.parse_args()
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d-%H%M%S")
    folder = (args.report_root or ROOT / ".cache" / f"stage-evaluation-{stamp}").resolve()
    folder.mkdir(parents=True, exist_ok=True)
    print(f"评测目录：{folder}", flush=True)
    records = []

    def execute(name, mode):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        process = subprocess.run(
            [sys.executable, str(ROOT / "tests/live_chinese_skills.py"), "--skill", name,
             "--mode", mode, "--report-root", str(folder)],
            cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            report = json.loads(process.stdout.strip().splitlines()[-1])
            return {"skill": name, "mode": mode, "exit_code": process.returncode,
                    "report": report["report"], "verified": report["verified"],
                    "elapsed_seconds": report["elapsed_seconds"], "error": report["error"]}
        except (ValueError, IndexError, KeyError):
            diagnostic = folder / f"{name}-{mode}-runner-error.log"
            diagnostic.write_text(process.stdout + process.stderr, encoding="utf-8")
            return {"skill": name, "mode": mode, "exit_code": process.returncode,
                    "verified": False, "error": "评测入口未生成有效报告", "diagnostic": str(diagnostic)}

    for mode in args.modes:
        # 两个独立浏览器并行；不共享 profile，不自动重试失败任务。
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(execute, name, mode) for name in CASES]
            for future in as_completed(futures):
                item = future.result()
                records.append(item)
                (folder / "index.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps(item, ensure_ascii=False), flush=True)
    passed = sum(item["verified"] for item in records)
    print(f"评测结束：{passed}/{len(records)} 通过，详见 {folder / 'index.json'}", flush=True)
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
