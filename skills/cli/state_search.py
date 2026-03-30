#!/usr/bin/env python3
"""Search theorems by proof state using premise-search.com."""
import argparse
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(__file__).parents[2] / "cli.log")],
)
logger = logging.getLogger(__name__)


def search(goal: str, num_results: int = 5) -> None:
    logger.info("state_search.search called: num_results=%d goal_len=%d", num_results, len(goal))
    try:
        encoded = urllib.parse.quote(goal)
        base_url = os.getenv("LEAN_STATE_SEARCH_URL", "https://premise-search.com")
        req = urllib.request.Request(
            f"{base_url}/api/search?query={encoded}&results={num_results}&rev=v4.22.0",
            headers={"User-Agent": "numina-lean-agent/0.1"},
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            results = json.loads(response.read())

        for result in results:
            result.pop("rev", None)

        logger.info("state_search.search succeeded: %d results", len(results))
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("state_search.search failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search theorems by proof state")
    parser.add_argument("goal", help="Proof state / goal text")
    parser.add_argument("-n", "--num-results", type=int, default=5, help="Max results (default: 5)")
    args = parser.parse_args()
    search(args.goal, args.num_results)
