#!/usr/bin/env python3
"""
Driver for running the Numina Lean Agent across LiveProveBench problems.

Reads problem rows from lists.txt (ProblemName / LeanFolder / Blueprint, all
relative to lists_base) and shared settings from a YAML config. For each row:

  1. In the LiveProveBench repo: `git checkout main`, then create or reuse a
     branch `NN_<ProblemName>` (NN = 1-based zero-padded index from lists.txt).
  2. Build the per-problem prompt by substituting absolute blueprint and
     target-folder paths into the prompt template. The blueprint content is
     NOT inlined — only its path is given to the agent.
  3. Run the numina-lean-agent runner on the target folder.
  4. Optionally `git add -A && git commit` the produced changes on that branch.

Usage:
    python scripts/run_liveprovebench.py [--config config/config_liveprovebench.yaml]
                                         [--only NAME] [--skip NAME]...
                                         [--from N] [--dry-run]
"""

import argparse
import csv
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

# Make sibling modules importable when run as `python scripts/run_liveprovebench.py`
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.task import TaskMetadata, TaskResult
from scripts.runner import run_task


def parse_lists(lists_file: Path, lists_base: Path) -> List[Tuple[str, Path, Path]]:
    """Parse the 3-column lists.txt. Returns [(name, lean_folder_abs, blueprint_abs), ...]."""
    rows: List[Tuple[str, Path, Path]] = []
    for lineno, raw in enumerate(lists_file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(
                f"{lists_file}:{lineno}: expected 3 whitespace-separated columns, got {len(parts)}: {line!r}"
            )
        name, lean_rel, blueprint_rel = parts
        lean_abs = (lists_base / lean_rel).resolve()
        blueprint_abs = (lists_base / blueprint_rel).resolve()
        if not lean_abs.is_dir():
            raise FileNotFoundError(f"{lists_file}:{lineno}: lean folder not found: {lean_abs}")
        if not blueprint_abs.is_file():
            raise FileNotFoundError(f"{lists_file}:{lineno}: blueprint not found: {blueprint_abs}")
        rows.append((name, lean_abs, blueprint_abs))
    return rows


def run_git(args: List[str], cwd: Path, dry_run: bool, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in cwd. Print it; skip execution in dry-run."""
    print(f"[git] ({cwd}) git {' '.join(args)}")
    if dry_run:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=check,
        text=True,
        capture_output=True,
    )


def branch_exists(lean_repo: Path, branch: str) -> bool:
    res = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=str(lean_repo),
        capture_output=True,
        text=True,
    )
    return res.returncode == 0


def has_staged_or_unstaged_changes(lean_repo: Path) -> bool:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(lean_repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(res.stdout.strip())


def build_prompt(template: str, blueprint_abs: Path, target_folder_abs: Path) -> str:
    return (
        template
        .replace("__BLUEPRINT_PATH__", str(blueprint_abs))
        .replace("__TARGET_FOLDER__", str(target_folder_abs))
    )


def resolve_runner_path(runner_cfg: dict, key: str) -> Path:
    """Resolve a runner path relative to runner.cwd if not already absolute."""
    raw = Path(runner_cfg[key])
    if raw.is_absolute():
        return raw
    return (Path(runner_cfg["cwd"]) / raw).resolve()


def append_summary(summary_path: Path, row: dict) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["timestamp", "nn", "name", "end_reason", "success", "rounds", "duration_s", "cost_usd", "branch"]
    write_header = not summary_path.exists()
    with open(summary_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if write_header:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in header})


def process_row(
    nn: str,
    name: str,
    lean_folder: Path,
    blueprint: Path,
    cfg: dict,
    template_text: str,
    dry_run: bool,
) -> Optional[TaskResult]:
    lean_repo = Path(cfg["lean_repo"])
    base_branch = cfg.get("base_branch", "main")
    runner_cfg = cfg["runner"]
    git_cfg = cfg.get("git", {})
    branch = f"{nn}_{name}"

    print("=" * 72)
    print(f"[{nn}] {name}")
    print(f"  lean_folder: {lean_folder}")
    print(f"  blueprint:   {blueprint}")
    print(f"  branch:      {branch}")
    print("=" * 72)

    # 1. git: checkout main, then branch
    run_git(["checkout", base_branch], lean_repo, dry_run)
    if dry_run:
        print(f"[git] (dry-run) would ensure branch {branch} exists and check it out")
    else:
        if branch_exists(lean_repo, branch):
            if git_cfg.get("skip_if_branch_exists", True):
                print(f"[info] branch {branch} already exists, checking out")
                run_git(["checkout", branch], lean_repo, dry_run=False)
            else:
                raise RuntimeError(f"branch {branch} already exists and skip_if_branch_exists=false")
        else:
            run_git(["checkout", "-b", branch], lean_repo, dry_run=False)

    # 1b. lake build the freshly-checked-out branch
    lake_cfg = cfg.get("lake_build", {}) or {}
    if lake_cfg.get("enabled", False):
        cmd = list(lake_cfg.get("cmd", ["lake", "build"]))
        timeout = int(lake_cfg.get("timeout_seconds", 1800))
        print(f"[lake] ({lean_repo}) {' '.join(cmd)}  (timeout {timeout}s)")
        if not dry_run:
            res = subprocess.run(cmd, cwd=str(lean_repo), timeout=timeout)
            if res.returncode != 0:
                raise RuntimeError(f"lake build failed on branch {branch} (rc={res.returncode})")

    # 2. Build prompt
    tmp_prompt_dir = resolve_runner_path(runner_cfg, "tmp_prompt_dir")
    tmp_prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = tmp_prompt_dir / f"{branch}.txt"
    prompt_text = build_prompt(template_text, blueprint, lean_folder)
    prompt_path.write_text(prompt_text, encoding="utf-8")
    print(f"[info] wrote prompt to {prompt_path} ({len(prompt_text)} chars)")

    # 3. Build and run task
    result_dir = resolve_runner_path(runner_cfg, "result_dir")
    mcp_log_dir = resolve_runner_path(runner_cfg, "mcp_log_dir")

    task = TaskMetadata(
        task_type=runner_cfg.get("task_type", "folder"),
        target_path=lean_folder,
        prompt_file=prompt_path,
        cwd=Path(runner_cfg["cwd"]),
        max_rounds=int(runner_cfg.get("max_rounds", 10)),
        permission_mode=runner_cfg.get("permission_mode", "bypassPermissions"),
        result_dir=result_dir,
        mcp_log_dir=mcp_log_dir,
        mcp_log_name=branch,
    )

    if dry_run:
        print(f"[dry-run] would run_task with:")
        print(f"  target_path  = {task.target_path}")
        print(f"  prompt_file  = {task.prompt_file}")
        print(f"  cwd          = {task.cwd}")
        print(f"  max_rounds   = {task.max_rounds}")
        print(f"  result_dir   = {task.result_dir}")
        print(f"  mcp_log_dir  = {task.mcp_log_dir}")
        print(f"  mcp_log_name = {task.mcp_log_name}")
        return None

    result = run_task(task)

    # 4. Optional commit on the problem branch
    if git_cfg.get("commit_after", True):
        if has_staged_or_unstaged_changes(lean_repo):
            msg = git_cfg.get("commit_message_template", "run {nn}_{name}").format(nn=nn, name=name)
            run_git(["add", "-A"], lean_repo, dry_run=False)
            run_git(["commit", "-m", msg], lean_repo, dry_run=False)
        else:
            print(f"[info] no changes to commit on {branch}")

    # 5. Append summary row
    summary_path = result_dir / "summary.csv"
    append_summary(
        summary_path,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "nn": nn,
            "name": name,
            "end_reason": result.end_reason or "",
            "success": str(result.success),
            "rounds": result.rounds_used,
            "duration_s": f"{result.duration_seconds:.1f}",
            "cost_usd": f"{result.total_cost_usd:.4f}",
            "branch": branch,
        },
    )

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Run numina-lean-agent across LiveProveBench problems.")
    ap.add_argument("--config", default=str(REPO_ROOT / "config" / "config_liveprovebench.yaml"),
                    help="Path to YAML config (default: config/config_liveprovebench.yaml)")
    ap.add_argument("--only", action="append", default=[], help="Only run these problem names (repeatable)")
    ap.add_argument("--skip", action="append", default=[], help="Skip these problem names (repeatable)")
    ap.add_argument("--from", dest="from_", default=None,
                    help="Start at this row: either a 1-based index (e.g. 5) or a ProblemName (e.g. Dilworth). "
                         "Numbering continues from lists.txt so NN stays stable across resumes.")
    ap.add_argument("--count", type=int, default=None, help="Run at most this many problems after --from")
    ap.add_argument("--sleep-between", type=float, default=None,
                    help="Minutes to sleep between problems (overrides runner.sleep_between_tasks_minutes). "
                         "Useful to avoid hitting rate / quota limits. 0 disables.")
    ap.add_argument("--dry-run", action="store_true", help="Print planned actions without executing")
    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    lists_file = Path(cfg["lists_file"]).resolve()
    lists_base = Path(cfg["lists_base"]).resolve()
    lean_repo = Path(cfg["lean_repo"]).resolve()
    if not lean_repo.is_dir():
        print(f"[error] lean_repo not found: {lean_repo}", file=sys.stderr)
        return 1

    rows = parse_lists(lists_file, lists_base)
    if not rows:
        print(f"[error] no rows in {lists_file}", file=sys.stderr)
        return 1

    # Load prompt template once
    template_path = Path(cfg["prompt_template"])
    if not template_path.is_absolute():
        template_path = Path(cfg["runner"]["cwd"]) / template_path
    template_text = template_path.read_text(encoding="utf-8")

    only_set = set(args.only)
    skip_set = set(args.skip)

    # Resolve --from: accept int or problem name
    from_idx = 1
    if args.from_:
        if args.from_.isdigit():
            from_idx = int(args.from_)
        else:
            name_to_idx = {n: i for i, (n, *_rest) in enumerate(rows, start=1)}
            if args.from_ not in name_to_idx:
                print(f"[error] --from {args.from_!r} not found in lists.txt", file=sys.stderr)
                return 1
            from_idx = name_to_idx[args.from_]
        print(f"[info] starting from row {from_idx} ({rows[from_idx - 1][0]})")

    # Resolve inter-task sleep (minutes → seconds)
    sleep_minutes = args.sleep_between
    if sleep_minutes is None:
        sleep_minutes = float(cfg.get("runner", {}).get("sleep_between_tasks_minutes", 0) or 0)
    sleep_seconds = max(0.0, sleep_minutes * 60.0)

    ran_count = 0
    results: List[Tuple[str, str, Optional[TaskResult]]] = []
    planned = [
        (idx, name, lf, bp) for idx, (name, lf, bp) in enumerate(rows, start=1)
        if idx >= from_idx and (not only_set or name in only_set) and name not in skip_set
    ]
    if args.count is not None:
        planned = planned[: args.count]

    for k, (idx, name, lean_folder, blueprint) in enumerate(planned):
        nn = f"{idx:02d}"
        try:
            result = process_row(nn, name, lean_folder, blueprint, cfg, template_text, args.dry_run)
        except subprocess.CalledProcessError as e:
            print(f"[error] {nn} {name}: git command failed: {e}\n{e.stderr}", file=sys.stderr)
            results.append((nn, name, None))
            result = None
        except Exception as e:
            print(f"[error] {nn} {name}: {e}", file=sys.stderr)
            results.append((nn, name, None))
            result = None
        else:
            results.append((nn, name, result))
        ran_count += 1

        # Sleep between problems (not after the last one)
        if sleep_seconds > 0 and k < len(planned) - 1:
            if args.dry_run:
                print(f"[dry-run] would sleep {sleep_minutes:g} min before next problem")
            else:
                print(f"[info] sleeping {sleep_minutes:g} min before next problem...")
                time.sleep(sleep_seconds)

    # Final summary
    print("\n" + "=" * 72)
    print("OVERALL SUMMARY")
    print("=" * 72)
    for nn, name, r in results:
        if r is None:
            status = "SKIPPED/ERROR" if not args.dry_run else "DRY-RUN"
        else:
            status = f"{r.end_reason or '-'} ({r.rounds_used} rounds, {r.duration_seconds:.0f}s)"
        print(f"  [{nn}] {name}: {status}")

    if args.dry_run:
        return 0
    any_failed = any(r is None or not r.success for _, _, r in results)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
