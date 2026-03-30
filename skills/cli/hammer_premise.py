#!/usr/bin/env python3
"""Search premises by proof state using Lean Hammer premise search."""
import argparse
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(__file__).parents[2] / "cli.log")],
)
logger = logging.getLogger(__name__)


def search(goal: str, num_results: int = 32) -> None:
    logger.info("hammer_premise.search called: num_results=%d goal_len=%d", num_results, len(goal))
    try:
        base_url = os.getenv("LEAN_HAMMER_URL", "http://leanpremise.net")
        data = json.dumps({
            "state": goal,
            "new_premises": [],
            "k": num_results,
        }).encode()

        req = urllib.request.Request(
            base_url + "/retrieve",
            headers={
                "User-Agent": "numina-lean-agent/0.1",
                "Content-Type": "application/json",
            },
            method="POST",
            data=data,
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            results = json.loads(response.read())

        names = [result["name"] for result in results]
        logger.info("hammer_premise.search succeeded: %d results", len(names))
        print(json.dumps(names, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("hammer_premise.search failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search premises by proof state (Lean Hammer)")
    parser.add_argument("goal", help="Proof state / goal text")
    parser.add_argument("-n", "--num-results", type=int, default=32, help="Max results (default: 32)")
    args = parser.parse_args()
    search(args.goal, args.num_results)
