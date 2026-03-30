#!/usr/bin/env python3
"""Search Lean theorems/definitions using Leandex semantic search."""
import argparse
import json
import logging
import sys
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(__file__).parents[2] / "cli.log")],
)
logger = logging.getLogger(__name__)


def search(query: str, num_results: int = 5) -> None:
    logger.info("leandex.search called: num_results=%d query=%r", num_results, query)
    url = "https://leandex.projectnumina.ai/api/v1/search"
    params = {
        "q": query,
        "limit": num_results,
        "generate_query": False,
        "analyze_result": False,
    }
    headers = {
        "accept": "text/event-stream",
        "user-agent": "numina-lean-agent/0.1",
    }

    try:
        data = None
        with requests.get(url, headers=headers, params=params, stream=True) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line.removeprefix("data:").strip()

        if data is None:
            logger.error("No data received from Leandex")
            print("Error: No data received from Leandex", file=sys.stderr)
            sys.exit(1)

        parsed = json.loads(data)
        results = parsed["data"]["search_results"]
        for r in results:
            r["primary_declaration"] = r["primary_declaration"]["lean_name"]

        logger.info("leandex.search succeeded: %d results", len(results))
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("leandex.search failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Lean theorems using Leandex")
    parser.add_argument("query", help="Search query (natural language, Lean terms, etc.)")
    parser.add_argument("-n", "--num-results", type=int, default=5, help="Max results (default: 5)")
    args = parser.parse_args()
    search(args.query, args.num_results)
