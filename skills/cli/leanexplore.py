#!/usr/bin/env python3
"""Search Lean definitions/theorems using Leandex semantic search."""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(
            Path(os.environ.get("CLI_LOG_PATH", Path(__file__).parents[2] / "cli.log"))
        )
    ],
)
logger = logging.getLogger(__name__)


def _leandex_headers() -> dict[str, str]:
    headers = {
        "accept": "text/event-stream",
        "user-agent": "numina-lean-agent/0.1",
    }
    api_key = os.environ.get("LEAN_LEANDEX_API_KEY") or os.environ.get(
        "LEANDEX_API_KEY"
    )
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def search(query: str, num_results: int = 5) -> None:
    logger.info(
        "leandex.search called: num_results=%d query=%r", num_results, query
    )
    url = "https://leandex.projectnumina.ai/api/v1/search"
    params = {
        "q": query,
        "limit": num_results,
        "generate_query": False,
        "analyze_result": False,
    }
    headers = _leandex_headers()

    try:
        data = None
        with requests.get(
            url, headers=headers, params=params, stream=True, timeout=30
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line.removeprefix("data:").strip()

        if data is None:
            raise RuntimeError("No data received from Leandex")

        parsed = json.loads(data)
        results = parsed["data"]["search_results"]
        for result in results:
            primary_declaration = result.get("primary_declaration")
            if isinstance(primary_declaration, dict):
                result["primary_declaration"] = primary_declaration.get("lean_name")

        logger.info("leandex search succeeded: %d results", len(results))
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.exception("leandex search failed: %s", e)
        print(f"Error: leandex search failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Lean theorems using Leandex")
    parser.add_argument(
        "query", help="Search query (natural language, Lean terms, identifiers)"
    )
    parser.add_argument(
        "-n",
        "--num-results",
        type=int,
        default=5,
        help="Max results (default: 5)",
    )
    args = parser.parse_args()
    search(args.query, args.num_results)
