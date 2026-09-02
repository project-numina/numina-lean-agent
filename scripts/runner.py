"""
Core runner functions for executing Claude on Lean tasks.
"""

import json
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, List, Literal
import os
import signal

from .task import TaskMetadata, TaskResult
from .lean_checker import find_lean_files, check_lean_files_parallel
from .cli_stats import analyze_cli_log, get_cli_log_path
from .safe_verify import snapshot_target, run_safe_verify, SafeVerifyResult
from .statement_tracker import StatementTracker, RoundResult, extract_claude_usage, StatementChange

# Enable line buffering for real-time output when redirecting to file
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Match END_REASON:{reason} on a single line
PAT_REASON = re.compile(r"(?m)^\s*END_REASON:(LIMIT|COMPLETE|SELECTED_TARGET_COMPLETE)\s*$", re.I)


def get_line_counts(files: List[Path]) -> dict:
    """Get line counts for files. Returns {filename: line_count}."""
    counts = {}
    for f in files:
        try:
            counts[f.name] = sum(1 for _ in open(f, encoding="utf-8"))
        except Exception:
            counts[f.name] = 0
    return counts


def run_claude_once(
    args: List[str],
    env: Optional[dict] = None,
    cwd: Optional[Path] = None,
    json_save_path: Optional[Path] = None,
) -> tuple[Optional[str], int, Optional[dict]]:
    """
    Execute a single claude command with stream-json output.

    Claude output is redirected directly to a file (no stdout pipe forwarding).
    If json_save_path is not provided, a tmp file with random uuid is used.
    Parses the final `type: "result"` line for END_REASON, usage info, and result
    text. Only the result text is printed to stdout.

    Args:
        args: Claude command arguments list
        env: Environment variables for the subprocess
        cwd: Working directory
        json_save_path: Path to save the raw NDJSON stream (.jsonl file)

    Returns:
        (end_reason, returncode, claude_result)
        end_reason: "COMPLETE" | "LIMIT" | "SELECTED_TARGET_COMPLETE" | None
        claude_result: Parsed dict from the final type:"result" JSON line, or None
    """
    if json_save_path is None:
        tmp_name = f"claude_raw_{uuid.uuid4().hex}.jsonl"
        json_save_path = Path(tempfile.gettempdir()) / tmp_name

    json_save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(json_save_path, "w", encoding="utf-8") as stdout_target:
        proc = subprocess.Popen(
            args,
            stdout=stdout_target,
            stderr=subprocess.STDOUT,
            text=True,
            env=env or None,
            cwd=str(cwd) if cwd else None,
        )
        proc.wait()
    current_pid = os.getpid()
    print(
        f"[info] Claude pid={proc.pid}, runner pid={current_pid},\n"
        f"one-click kill command: kill -TERM {current_pid} -- -{proc.pid}"
    )

    last_line = ""
    try:
        with open(json_save_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    last_line = line
    except OSError:
        pass

    claude_result = None
    reason = None
    last_line = last_line.strip()
    if last_line:
        try:
            parsed = json.loads(last_line)
            if parsed.get("type") == "result":
                claude_result = parsed
                result_text = parsed.get("result", "")
                sys.stdout.write(result_text)
                sys.stdout.write("\n")
                sys.stdout.flush()
                m = PAT_REASON.search(result_text)
                reason = m.group(1).upper() if m else None
        except json.JSONDecodeError:
            pass

    time.sleep(0.5)
    return reason, proc.returncode, claude_result


def commit_round(round_num: int, cwd: Optional[Path] = None):
    """Create a git commit after a round."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    msg = f"[{timestamp}]_claude_round_{round_num:02d}"
    kwargs = {"cwd": str(cwd)} if cwd else {}
    try:
        subprocess.run(["git", "add", "-A"], check=True, **kwargs)
        subprocess.run(["git", "commit", "-m", msg], check=True, **kwargs)
        print(f"[info] Committed: {msg}")
    except subprocess.CalledProcessError as e:
        print(f"[warn] Round {round_num}: git commit failed - {e} (possibly no changes to commit)")
    except Exception as e:
        print(f"[error] Round {round_num}: unexpected error during git commit - {e}")


def run_claude_session(
    prompt: str,
    cwd: Optional[Path] = None,
    permission_mode: str = "bypassPermissions",
    output_format: Optional[str] = None,
    max_rounds: int = 20,
    sleep_between_rounds: float = 1.0,
    env: Optional[dict] = None,
    on_complete: Optional[Callable[[], bool]] = None,
    tracker: Optional[StatementTracker] = None,
    on_statement_change: Literal["error", "warn"] = "warn",
    git_commit_dir: Optional[Path] = None,
    result_dir: Optional[Path] = None,
    task_id: Optional[str] = None,
    files_to_track: Optional[List[Path]] = None,
) -> tuple[str, int, List[RoundResult]]:
    """
    Run a complete Claude session with automatic continue logic.

    Args:
        prompt: Initial prompt (provided by user)
        cwd: Working directory
        permission_mode: Permission mode
        output_format: Output format (json / None)
        max_rounds: Maximum rounds
        sleep_between_rounds: Sleep between rounds
        env: Environment variables for the subprocess
        on_complete: Callback when COMPLETE is received, returns False to resend prompt
        tracker: Statement tracker for detecting changes
        on_statement_change: Action on statement change ("error" to stop, "warn" to continue)
        git_commit_dir: Directory to create git commits in (default: None, no commits)
        result_dir: Directory to save round results immediately (default: None, no immediate save)
        task_id: Task ID for organizing result files

    Returns:
        (end_reason, rounds_used, round_results)
    """
    print(f"[info] Using prompt:\n{prompt[:120]}{'...' if len(prompt) > 120 else ''}\n")

    # Build base command (always use --verbose --output-format stream-json)
    base = ["claude", "-p", "--verbose", "--output-format", "stream-json"]
    if permission_mode:
        base += ["--permission-mode", permission_mode]

    round_results: List[RoundResult] = []
    statement_error = False
    needs_statement_restore = False  # Flag to indicate statement needs restoration before next round
    statement_changes_to_restore: List[StatementChange] = []  # Store the specific changes to restore
    initial_line_counts = get_line_counts(files_to_track) if files_to_track else {}
    last_claude_result: Optional[dict] = None

    def _get_json_save_path(round_num: int) -> Optional[Path]:
        """Compute the NDJSON save path for a round."""
        if result_dir and task_id:
            p = result_dir / task_id / "claude_raw"
            p.mkdir(parents=True, exist_ok=True)
            return p / f"round_{round_num}.jsonl"
        return None

    def record_round(round_num: int, reason: Optional[str], returncode: int, duration: float, claude_result: Optional[dict] = None) -> RoundResult:
        """Record a round result and check for statement changes."""
        nonlocal statement_error, needs_statement_restore, statement_changes_to_restore

        changes = tracker.check() if tracker else []
        line_counts = get_line_counts(files_to_track) if files_to_track else {}

        result = RoundResult(
            round_number=round_num,
            end_reason=reason,
            returncode=returncode,
            statement_changes=changes,
            duration_seconds=duration,
            line_counts=line_counts,
            claude_usage=extract_claude_usage(claude_result),
        )
        round_results.append(result)

        # Handle statement changes
        if changes:
            # Separate changes into modified/removed (not allowed) and added (allowed with warn only)
            not_allowed_changes = [c for c in changes if c.change_type in ["modified", "removed"]]
            added_changes = [c for c in changes if c.change_type == "added"]
            
            if on_statement_change == "error":
                print(f"\n[error] Statement changed in round {round_num}! Stopping.")
                for c in changes:
                    print(f"  {c}")
                statement_error = True
            elif not_allowed_changes:
                # In warn mode, modified/removed statements trigger restoration in next round
                print(f"\n[warn] Statement modified/removed in round {round_num}! Will restore in next round.")
                for c in changes:
                    print(f"  {c}")
                needs_statement_restore = True
                statement_changes_to_restore = not_allowed_changes  # Store specific changes to restore
            else:
                # In warn mode, only added statements are allowed
                print(f"\n[warn] New statement(s) added in round {round_num}:")
                for c in changes:
                    print(f"  {c}")

        # Print line count changes
        if line_counts and initial_line_counts:
            # vs initial
            init_changes = []
            for filename, current in line_counts.items():
                if filename in initial_line_counts:
                    diff = current - initial_line_counts[filename]
                    if diff != 0:
                        ratio = diff / initial_line_counts[filename] * 100 if initial_line_counts[filename] > 0 else 0
                        init_changes.append((filename, initial_line_counts[filename], current, diff, ratio))
            # vs previous round
            prev_changes = []
            if round_results:
                prev_counts = round_results[-1].line_counts
                for filename, current in line_counts.items():
                    if filename in prev_counts:
                        diff = current - prev_counts[filename]
                        if diff != 0:
                            ratio = diff / prev_counts[filename] * 100 if prev_counts[filename] > 0 else 0
                            prev_changes.append((filename, prev_counts[filename], current, diff, ratio))

            if init_changes:
                print(f"[info] Line changes (vs initial):")
                for filename, initial, final, diff, ratio in init_changes:
                    sign = "+" if diff > 0 else ""
                    print(f"  {filename}: {initial} -> {final} ({sign}{diff}, {ratio:+.1f}%)")
            if prev_changes:
                print(f"[info] Line changes (vs prev round):")
                for filename, prev, final, diff, ratio in prev_changes:
                    sign = "+" if diff > 0 else ""
                    print(f"  {filename}: {prev} -> {final} ({sign}{diff}, {ratio:+.1f}%)")


        # Save round result immediately if result_dir is specified
        if result_dir and task_id:
            result_path = result_dir / task_id
            result_path.mkdir(parents=True, exist_ok=True)
            round_file = result_path / f"round_{round_num}.json"
            with open(round_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"[info] Round {round_num} completed in {result.duration_seconds:.1f}s, result saved to {round_file}")

        return result

    # First call: new session
    round_start = time.time()
    reason, returncode, claude_result = run_claude_once(
        base + [prompt], env=env, cwd=cwd, json_save_path=_get_json_save_path(1),
    )
    round_duration = time.time() - round_start
    last_claude_result = claude_result
    record_round(1, reason, returncode, round_duration, claude_result)
    if git_commit_dir:
        commit_round(1, git_commit_dir)

    if statement_error:
        return "STATEMENT_CHANGED", 1, round_results

    # Check if we need to restore statements after first round
    if needs_statement_restore:
        print("\n[info] Restoring initial statements after first round...")
        tracker.restore_initial_statements(statement_changes_to_restore)
        needs_statement_restore = False

    rounds = 1
    consecutive_limits = 1 if reason == "LIMIT" else 0  # Track consecutive LIMIT count
    max_consecutive_limits = 2  # Reset session after 2 consecutive LIMITs

    while reason == "LIMIT" or reason is None or reason == "COMPLETE" or reason == "SELECTED_TARGET_COMPLETE":
        print("=" * 60)

        # Check if we need to restore statements before starting the next round
        if needs_statement_restore:
            print("\n[info] Restoring initial statements before next round...")
            tracker.restore_initial_statements(statement_changes_to_restore)
            needs_statement_restore = False

        if rounds >= max_rounds:
            print(
                f"\n[warn] Reached maximum round count {max_rounds}, stopping.",
                file=sys.stderr,
            )
            break

        time.sleep(max(0.0, sleep_between_rounds))

        # If COMPLETE, run verification callback
        if reason == "COMPLETE":
            print("\n[info] Received COMPLETE signal.")
            if on_complete:
                if on_complete():
                    # Verification passed
                    break
                else:
                    # Verification failed, resend prompt
                    print("[info] Verification failed, resending prompt...")
                    rounds += 1
                    round_start = time.time()
                    reason, returncode, claude_result = run_claude_once(
                        base + [prompt], env=env, cwd=cwd, json_save_path=_get_json_save_path(rounds),
                    )
                    round_duration = time.time() - round_start
                    last_claude_result = claude_result
                    record_round(rounds, reason, returncode, round_duration, claude_result)
                    if git_commit_dir:
                        commit_round(rounds, git_commit_dir)
                    if statement_error:
                        return "STATEMENT_CHANGED", rounds, round_results
                    continue
            else:
                # No verification callback, accept COMPLETE
                break

        # If SELECTED_TARGET_COMPLETE, continue to next target
        if reason == "SELECTED_TARGET_COMPLETE":
            print("\n[info] Received SELECTED_TARGET_COMPLETE signal, continuing to next target...")

        rounds += 1

        # Check if we need to reset session due to consecutive LIMITs
        should_reset_session = (reason == "LIMIT" and consecutive_limits >= max_consecutive_limits)

        # Continue with prompt again if reason is None or need to reset session
        round_start = time.time()
        if reason is None:
            print("[info] No END_REASON detected, continuing with prompt...")
            reason, returncode, claude_result = run_claude_once(
                base + [prompt], env=env, cwd=cwd, json_save_path=_get_json_save_path(rounds),
            )
        elif should_reset_session:
            print(f"[info] Resetting session after {consecutive_limits} consecutive LIMITs...")
            reason, returncode, claude_result = run_claude_once(
                base + [prompt], env=env, cwd=cwd, json_save_path=_get_json_save_path(rounds),
            )
            consecutive_limits = 0
        else:
            cmd = ["claude", "-c", "-p", "--verbose", "--output-format", "stream-json"]
            if permission_mode:
                cmd += ["--permission-mode", permission_mode]
            reason, returncode, claude_result = run_claude_once(
                cmd + ["continue"], env=env, cwd=cwd, json_save_path=_get_json_save_path(rounds),
            )
        round_duration = time.time() - round_start
        last_claude_result = claude_result
        record_round(rounds, reason, returncode, round_duration, claude_result)
        if git_commit_dir:
            commit_round(rounds, git_commit_dir)
        if statement_error:
            return "STATEMENT_CHANGED", rounds, round_results

        # Update consecutive_limits counter
        if reason == "LIMIT":
            consecutive_limits += 1
        else:
            consecutive_limits = 0

    return reason, rounds, round_results


def run_task(task: TaskMetadata) -> TaskResult:
    """
    Execute a single task.

    Args:
        task: Task metadata

    Returns:
        Task result
    """
    start_time = datetime.now()
    error_message = None
    cli_stats = None
    round_results: List[RoundResult] = []
    statement_changed = False
    safe_verify_result: Optional[SafeVerifyResult] = None
    sv_target_path: Optional[Path] = None  # Snapshot of original .lean (with sorry)

    try:
        # Get prompt
        prompt = task.get_prompt()

        # Build environment for the subprocess (sets CLI_LOG_PATH when result_dir is set)
        env = task.build_env()

        # Per-task CLI log (isolated from other tasks). Falls back to the shared
        # default when result_dir is not set.
        cli_log_path = Path(env["CLI_LOG_PATH"]) if "CLI_LOG_PATH" in env else get_cli_log_path()

        # Get files to track
        if task.task_type == "file":
            files_to_track = [task.target_path]
        else:
            files_to_track = find_lean_files(task.target_path)

        # Snapshot the original file for SafeVerify (before the agent modifies it).
        # Must be inside the project directory so lake env lean accepts it.
        if task.safe_verify_path and task.task_type == "file":
            sv_target_path = task.target_path.parent / f"{task.target_path.stem}__sv_target{task.target_path.suffix}"
            snapshot_target(task.target_path, sv_target_path)
            print(f"[info] SafeVerify: snapshotted target to {sv_target_path}")

        # Initialize statement tracker if enabled
        tracker = None
        if task.track_statements and files_to_track:
            tracker = StatementTracker(files_to_track)
            print(f"[info] Tracking statements in {len(files_to_track)} file(s)")

        # Build verification callback
        def on_complete_callback() -> bool:
            if not task.check_after_complete:
                return True

            check_path = task.get_check_path()

            # Determine files to check based on task_type
            if task.task_type == "file":
                lean_files = [check_path] if check_path.suffix == ".lean" else []
            else:
                lean_files = find_lean_files(check_path)

            if not lean_files:
                return True

            print(f"[info] Verifying {len(lean_files)} .lean files...")
            results = check_lean_files_parallel(lean_files)

            # Filter errors based on allow_sorry setting
            if task.allow_sorry:
                errors = [f for f, e, _, _, _ in results if e]
                print(f"[info] allow_sorry=True, ignoring sorry warnings")
            else:
                errors = [f for f, e, s, _, _ in results if e or s]

            if errors:
                print(f"\n[error] {len(errors)} files have errors{'' if task.allow_sorry else '/sorry'}:")
                for f in errors:
                    print(f"  - {f}")
                return False

            print(f"[info] All {len(lean_files)} files verified successfully!")
            return True

        # Run Claude session
        git_commit_dir = None
        if task.git_commit:
            git_commit_dir = task.target_path if task.task_type == "folder" else task.target_path.parent

        # Prepare result_dir for immediate round saving
        result_dir_path = Path(task.result_dir) if task.result_dir else None

        end_reason, rounds_used, round_results = run_claude_session(
            prompt=prompt,
            cwd=task.cwd,
            permission_mode=task.permission_mode,
            output_format=task.output_format,
            max_rounds=task.max_rounds,
            sleep_between_rounds=task.sleep_between_rounds,
            env=env,
            on_complete=on_complete_callback if task.check_after_complete else None,
            tracker=tracker,
            on_statement_change=task.on_statement_change,
            git_commit_dir=git_commit_dir,
            result_dir=result_dir_path,
            task_id=task.task_id,
            files_to_track=files_to_track,
        )

        # Check if any statement was changed
        statement_changed = any(rr.has_statement_changes() for rr in round_results)

        # Final check if reached limit (not COMPLETE)
        if task.check_after_complete and end_reason != "COMPLETE":
            check_path = task.get_check_path()

            # Determine files to check based on task_type
            if task.task_type == "file":
                lean_files = [check_path] if check_path.suffix == ".lean" else []
            else:
                lean_files = find_lean_files(check_path)

            if lean_files:
                print(f"\n[info] Reached limit, performing final verification on {len(lean_files)} .lean files...")
                results = check_lean_files_parallel(lean_files)

                # Filter errors based on allow_sorry setting
                if task.allow_sorry:
                    errors = [f for f, e, _, _, _ in results if e]
                    print(f"[info] allow_sorry=True, ignoring sorry warnings")
                else:
                    errors = [f for f, e, s, _, _ in results if e or s]

                if errors:
                    print(f"[error] {len(errors)} files have errors{'' if task.allow_sorry else '/sorry'}:")
                    for f in errors:
                        print(f"  - {f}")
                else:
                    print(f"[info] All {len(lean_files)} files verified successfully!")
                    # Update end_reason to COMPLETE if verification passed
                    if not task.allow_sorry: # Only set to COMPLETE if allow_sorry is False (which means the file is indeed done)
                        end_reason = "COMPLETE"

        # Analyze CLI skill call stats if result_dir is specified
        if task.result_dir and cli_log_path.exists():
            stats_dir = Path(task.result_dir) / task.task_id
            stats_dir.mkdir(parents=True, exist_ok=True)
            print(f"[info] Generating CLI skill stats from {cli_log_path} to {stats_dir}")
            cli_stats = analyze_cli_log(str(cli_log_path), str(stats_dir))

        # Run SafeVerify if configured (file tasks only) and if the proof compiled
        if task.safe_verify_path and task.task_type == "file" and sv_target_path:
            if end_reason == "COMPLETE":
                print(f"\n[info] Running SafeVerify.")
                sv_cwd = task.safe_verify_cwd or task.cwd
                if sv_cwd is None:
                    sv_cwd = task.target_path.parent
                try:
                    safe_verify_result = run_safe_verify(
                        target_lean=sv_target_path,
                        submission_lean=task.target_path,
                        safe_verify_bin=Path(task.safe_verify_path),
                        cwd=Path(sv_cwd),
                    )
                finally:
                    # Always clean up the snapshot file
                    try:
                        sv_target_path.unlink(missing_ok=True)
                    except Exception:
                        pass

                _sv_status = "PASSED" if safe_verify_result.success else "FAILED"
                print(f"[info] SafeVerify: {_sv_status} (exit {safe_verify_result.returncode})")
                if safe_verify_result.error_message:
                    print(f"[warn] SafeVerify error: {safe_verify_result.error_message}")
                if safe_verify_result.output.strip():
                    print(safe_verify_result.output)
                # SafeVerify is the kernel-level integrity gate: a failed check must
                # flip the task outcome. Leaving success=True on FAILED would report
                # false positives in result.json / LiveProveBench summary.csv.
                if safe_verify_result.ran and not safe_verify_result.success:
                    end_reason = "SAFE_VERIFY_FAILED"
                    print(f"[error] SafeVerify failed; marking task unsuccessful")
            else:
                # Proof didn't compile: skip SafeVerify, just clean up snapshot
                print(f"\n[info] SafeVerify: skipped (end_reason={end_reason}, proof did not compile)")
                try:
                    sv_target_path.unlink(missing_ok=True)
                except Exception:
                    pass

        success = end_reason == "COMPLETE"

    except Exception as e:
        end_reason = "ERROR"
        rounds_used = 0
        success = False
        error_message = str(e)
        print(f"[error] Task failed: {e}", file=sys.stderr)

    end_time = datetime.now()

    result = TaskResult(
        task_id=task.task_id,
        success=success,
        end_reason=end_reason,
        rounds_used=rounds_used,
        start_time=start_time,
        end_time=end_time,
        error_message=error_message,
        cli_stats=cli_stats,
        round_results=round_results,
        statement_changed=statement_changed,
        safe_verify_result=safe_verify_result,
    )

    print(f"\n[info] Task {task.task_id} completed:")
    print(f"  Success: {result.success}")
    print(f"  End reason: {result.end_reason}")
    print(f"  Rounds used: {result.rounds_used}")
    if safe_verify_result and safe_verify_result.ran:
        sv_status = "PASSED" if safe_verify_result.success else "FAILED"
        print(f"  SafeVerify: {sv_status}")
    print(f"  Duration: {result.duration_seconds:.1f}s")
    if statement_changed:
        print(f"  Statement changed: Yes")
    if result.total_cost_usd > 0:
        usage = result.total_usage
        print(f"  Total cost: ${result.total_cost_usd:.4f}")
        print(f"  Tokens: {usage['input_tokens']} in / {usage['output_tokens']} out / {usage['cache_read_input_tokens']} cache_read / {usage['cache_creation_input_tokens']} cache_create")

    # Save final result to JSON if result_dir is specified
    # (Individual round results are already saved immediately during execution)
    if task.result_dir:
        result_path = Path(task.result_dir) / task.task_id
        result_path.mkdir(parents=True, exist_ok=True)

        # Save final result summary
        result_file = result_path / "result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"[info] Final result saved to {result_file}")

    return result


def run_tasks(
    tasks: List[TaskMetadata],
    parallel: bool = False,
    max_workers: int = 1,
) -> List[TaskResult]:
    """
    Execute multiple tasks.

    Args:
        tasks: List of task metadata
        parallel: Whether to run in parallel
        max_workers: Maximum parallel workers

    Returns:
        List of results (in same order as tasks)
    """
    if not tasks:
        return []

    if not parallel or max_workers <= 1:
        # Sequential execution
        results = []
        for i, task in enumerate(tasks, 1):
            print(f"\n{'=' * 60}")
            print(f"[{i}/{len(tasks)}] Running task: {task.task_id}")
            print("=" * 60)
            result = run_task(task)
            results.append(result)
        return results

    # Parallel execution
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(run_task, task): idx for idx, task in enumerate(tasks)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                # Create error result
                task = tasks[idx]
                results[idx] = TaskResult(
                    task_id=task.task_id,
                    success=False,
                    end_reason="ERROR",
                    rounds_used=0,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(e),
                )

    return results
