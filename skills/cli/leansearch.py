#!/usr/bin/env python3
"""Search Lean theorems using LeanSearch (natural language + Lean terms)."""
import argparse
import json
import os
import logging
import sys
import time
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(os.environ.get("CLI_LOG_PATH", Path(__file__).parents[2] / "cli.log")))],
)
logger = logging.getLogger(__name__)


MAX_ATTEMPTS = 3


def search(query: str, num_results: int = 5) -> None:
    logger.info("leansearch.search called: num_results=%d query=%r", num_results, query)
    try:
        # leansearch.net expects POST /search with JSON body
        # {"query": [<list of query strings>], "num_results": N}.
        # Response is a list-of-lists (one inner list per query).
        body = json.dumps({"query": [query], "num_results": num_results}).encode("utf-8")
        req = urllib.request.Request(
            "https://leansearch.net/search",
            data=body,
            headers={
                "User-Agent": "numina-lean-agent/0.1",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    payload = json.loads(response.read())
                break
            except Exception:
                if attempt == MAX_ATTEMPTS:
                    raise
                logger.warning("leansearch.search attempt %d/%d failed; retrying", attempt, MAX_ATTEMPTS, exc_info=True)
                time.sleep(attempt)

        # Unwrap the outer list (one entry per query — we only send one).
        results = payload[0] if payload and isinstance(payload, list) else []

        if not results:
            logger.info("leansearch.search: no results found")
            print("No results found.")
            return

        logger.info("leansearch.search succeeded: %d results", len(results))
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("leansearch.search failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Lean theorems using LeanSearch")
    parser.add_argument("query", help="Natural language or Lean term query")
    parser.add_argument("-n", "--num-results", type=int, default=5, help="Max results (default: 5)")
    args = parser.parse_args()
    search(args.query, args.num_results)
