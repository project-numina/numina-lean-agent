#!/usr/bin/env python3
"""Search Lean theorems using LeanSearch (natural language + Lean terms)."""
import argparse
import json
import logging
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


def search(query: str, num_results: int = 5) -> None:
    logger.info("leansearch.search called: num_results=%d query=%r", num_results, query)
    try:
        encoded = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"https://leansearch.net/api/search?query={encoded}&num_results={num_results}",
            headers={"User-Agent": "numina-lean-agent/0.1"},
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            results = json.loads(response.read())

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
