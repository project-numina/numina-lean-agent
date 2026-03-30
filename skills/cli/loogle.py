#!/usr/bin/env python3
"""Search Lean definitions/theorems using Loogle (pattern matching)."""
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


def search(query: str, num_results: int = 8) -> None:
    logger.info("loogle.search called: num_results=%d query=%r", num_results, query)
    try:
        encoded = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"https://loogle.lean-lang.org/json?q={encoded}",
            headers={"User-Agent": "numina-lean-agent/0.1"},
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            results = json.loads(response.read())

        if "hits" not in results:
            if "error" in results:
                logger.error("Loogle error: %s", results["error"])
                print(f"Loogle error: {results['error']}", file=sys.stderr)
            else:
                logger.info("loogle.search: no results found")
                print("No results found.")
            return

        hits = results["hits"][:num_results]
        for hit in hits:
            hit.pop("doc", None)
        logger.info("loogle.search succeeded: %d hits", len(hits))
        print(json.dumps(hits, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("loogle.search failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Lean theorems using Loogle")
    parser.add_argument("query", help="Loogle query (constants, name patterns, type shapes, etc.)")
    parser.add_argument("-n", "--num-results", type=int, default=8, help="Max results (default: 8)")
    args = parser.parse_args()
    search(args.query, args.num_results)
