#!/usr/bin/env python3
"""Wrapper around the axle CLI that adds logging to cli.log."""
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


def _extract_flag(args: list[str], flag: str) -> str | None:
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(f"{flag}="):
            return a.split("=", 1)[1]
    return None


def main() -> None:
    args = sys.argv[1:]
    subcmd = args[0] if args else "(no subcommand)"

    env = _extract_flag(args, "--environment")
    names = _extract_flag(args, "--names")

    # Second positional arg (after subcommand) is CONTENT
    positional = [a for a in args[1:] if not a.startswith("-")]
    content_arg = positional[0] if positional else None
    if content_arg:
        is_file = Path(content_arg).exists()
        content_desc = f"file:{content_arg}" if is_file else f"inline({len(content_arg)} chars)"
    else:
        content_desc = "none"

    logger.info(
        "axle.%s called: environment=%s names=%s content=%s",
        subcmd, env, names, content_desc,
    )

    result = subprocess.run(["axle"] + args, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            output = json.loads(result.stdout)
            okay = output.get("okay", "?")
            failed = output.get("failed_declarations", [])
            logger.info(
                "axle.%s succeeded: okay=%s failed_declarations=%s",
                subcmd, okay, failed,
            )
        except (json.JSONDecodeError, AttributeError):
            logger.info("axle.%s succeeded (exit 0)", subcmd)
    else:
        logger.warning(
            "axle.%s failed: exit=%d stderr=%r",
            subcmd, result.returncode, result.stderr[:300],
        )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
