"""
CLI skill log analysis utilities.

Each `skills/cli/*.py` script appends a line to the path given by the
`CLI_LOG_PATH` env var (runner sets this per-task to
`<result_dir>/<task_id>/cli.log`). When the env var is unset, the scripts
fall back to `<repo_root>/cli.log`. This module reads such a log file and
counts invocations per tool.
"""

import json
import re
from collections import defaultdict
from pathlib import Path


# Log line format (see skills/cli/*.py):
#   "%(asctime)s %(name)s %(levelname)s %(message)s"
# Example:
#   2026-04-17 01:52:08,119 __main__ INFO leanexplore.search called: num_results=5 query='...'
_LOG_LINE_RE = re.compile(
    r"^(?P<ts>\S+ \S+)\s+(?P<logger>\S+)\s+(?P<level>\S+)\s+(?P<msg>.*)$"
)
# Tool name = leading identifier in the message (optionally dotted, e.g. leanexplore.search).
_TOOL_RE = re.compile(r"^(?P<tool>[a-zA-Z_][\w.]*)\b")


def get_cli_log_path() -> Path:
    """Return the default shared CLI log path: `<repo_root>/cli.log`.

    Used as a fallback when `result_dir` is not set on the task; per-task runs
    should use the path written to `CLI_LOG_PATH` instead.
    """
    return Path(__file__).resolve().parents[1] / "cli.log"


def _tool_key(msg: str) -> str | None:
    m = _TOOL_RE.match(msg)
    if not m:
        return None
    # Collapse "leanexplore.search" -> "leanexplore"
    return m.group("tool").split(".", 1)[0]


def analyze_cli_log(log_path: str | Path, out_dir: str | Path) -> dict:
    """
    Count CLI skill invocations in `log_path` and save results.

    Args:
        log_path: Path to the CLI log file (usually per-task, sometimes the
            shared repo-root fallback).
        out_dir: Output directory for the stats JSON.

    Returns:
        {"by_tool": {tool: {called, ok, fail}}, "total": {...}}
    """
    log_path = Path(log_path).expanduser().resolve()
    out_path = Path(out_dir).expanduser().resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    summary = {
        "by_tool": {},
        "total": {"called": 0, "ok": 0, "fail": 0},
    }

    if not log_path.exists():
        print(f"[warn] cli.log does not exist: {log_path}")
        return summary

    stats = defaultdict(lambda: {"called": 0, "ok": 0, "fail": 0})
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            m = _LOG_LINE_RE.match(raw.rstrip("\n"))
            if not m:
                continue
            level = m.group("level").upper()
            msg = m.group("msg")
            tool = _tool_key(msg)
            if not tool:
                continue

            # Arguments can contain event words; only inspect the log prefix.
            event = msg.split(":", 1)[0]
            if re.search(r"\bcalled\b", event):
                stats[tool]["called"] += 1
            if re.search(r"\bsucceeded\b", event):
                stats[tool]["ok"] += 1
            elif level in ("ERROR", "WARNING") or re.search(r"\b(failed|exhausted)\b", event):
                stats[tool]["fail"] += 1

    total = {"called": 0, "ok": 0, "fail": 0}
    for t, s in stats.items():
        for k in total:
            total[k] += s[k]
        print(f'{t:25}  called={s["called"]:3}  ok={s["ok"]:3}  fail={s["fail"]:3}')
    print("-" * 60)
    print(f'{"TOTAL":25}  called={total["called"]:3}  ok={total["ok"]:3}  fail={total["fail"]:3}')

    summary = {
        "by_tool": {k: dict(v) for k, v in stats.items()},
        "total": total,
    }
    json_file = out_path / "cli_stats.json"
    with json_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nCLI skill call stats saved to {json_file}")

    return summary
