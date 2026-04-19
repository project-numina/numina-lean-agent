#!/usr/bin/env python3
"""Local Lean file compile check using `lake env lean`.

Drop-in alternative to `axle check` that runs locally — no API key needed.
Output format mirrors axle check: { okay, lean_messages, failed_declarations }.
"""
import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(__file__).parents[2] / "cli.log")],
)
logger = logging.getLogger(__name__)

# Pattern: /path/file.lean:10:4: error: msg  OR  /path/file.lean:10:4: error(code): msg
DIAG_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*(?P<sev>error|warning|info)(?:\([^)]*\))?:\s*(?P<msg>.+)",
    re.MULTILINE,
)


def find_project_root(file_path: Path) -> Path:
    """Walk up from file to find directory containing lean-toolchain."""
    current = file_path.parent if file_path.is_file() else file_path
    while current != current.parent:
        if (current / "lean-toolchain").exists():
            return current
        current = current.parent
    return file_path.parent if file_path.is_file() else file_path


def parse_diagnostics(output: str) -> list[dict]:
    """Parse Lean compiler output into structured diagnostics.

    Each diagnostic may span multiple lines (e.g. omega goal state, unsolved goals).
    We capture everything between consecutive header lines as the full message body.
    """
    messages = []
    matches = list(DIAG_RE.finditer(output))
    for i, m in enumerate(matches):
        # Text between this header's end and the next header (or EOF) is the detail body.
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(output)
        extra = output[body_start:body_end].strip()

        first_line = m.group("msg").strip()
        full_data = (first_line + "\n" + extra) if extra else first_line

        messages.append({
            "file_name": m.group("file"),
            "line": int(m.group("line")),
            "column": int(m.group("col")),
            "severity": m.group("sev"),
            "data": full_data,
        })
    return messages


def extract_failed_declarations(messages: list[dict]) -> list[str]:
    """Extract declaration names from error messages when possible."""
    failed = set()
    # Pattern: "declaration 'Foo.bar' ..." or similar
    decl_re = re.compile(r"'([A-Za-z_][\w.]*)'")
    for msg in messages:
        if msg["severity"] == "error":
            match = decl_re.search(msg["data"])
            if match:
                failed.add(match.group(1))
    return sorted(failed)


def check(file_path: Path, timeout: int = 120) -> dict:
    """Run `lake env lean` on a file and return axle-compatible result."""
    project_root = find_project_root(file_path)

    try:
        result = subprocess.run(
            ["lake", "env", "lean", str(file_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        return {
            "okay": False,
            "lean_messages": [{"severity": "error", "data": f"Timed out after {timeout}s", "line": 0, "column": 0}],
            "failed_declarations": [],
        }
    except Exception as e:
        return {
            "okay": False,
            "lean_messages": [{"severity": "error", "data": str(e), "line": 0, "column": 0}],
            "failed_declarations": [],
        }

    combined = result.stdout + "\n" + result.stderr
    messages = parse_diagnostics(combined)
    has_error = any(m["severity"] == "error" for m in messages) or result.returncode != 0
    failed = extract_failed_declarations(messages)

    return {
        "okay": not has_error,
        "lean_messages": messages,
        "failed_declarations": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Lean compile check (lake env lean)")
    parser.add_argument("file", type=Path, help="Lean file path to check")
    parser.add_argument("--timeout-seconds", type=int, default=300, help="Max execution time (default: 120)")
    args = parser.parse_args()

    file_path = args.file.resolve()
    if not file_path.exists():
        print(json.dumps({"okay": False, "lean_messages": [{"severity": "error", "data": f"File not found: {file_path}", "line": 0, "column": 0}], "failed_declarations": []}), flush=True)
        sys.exit(1)

    logger.info("lean_check called: file=%s timeout=%d", file_path, args.timeout_seconds)
    result = check(file_path, timeout=args.timeout_seconds)
    logger.info("lean_check result: okay=%s errors=%d", result["okay"], len([m for m in result["lean_messages"] if m["severity"] == "error"]))

    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    sys.exit(0 if result["okay"] else 1)


if __name__ == "__main__":
    main()
