#!/usr/bin/env python3
"""Search Mathlib theorems semantically using Lean Finder."""
import argparse
import json
import logging
import re
import sys
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(__file__).parents[2] / "cli.log")],
)
logger = logging.getLogger(__name__)


def search(query: str, num_results: int = 5) -> None:
    logger.info("leanfinder.search called: num_results=%d query=%r", num_results, query)
    try:
        headers = {
            "User-Agent": "numina-lean-agent/0.1",
            "Content-Type": "application/json",
        }
        url = "https://bxrituxuhpc70w8w.us-east-1.aws.endpoints.huggingface.cloud"
        payload = json.dumps({"inputs": query, "top_k": num_results}).encode()
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        results = []
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
            for result in data["results"]:
                if "https://leanprover-community.github.io/mathlib4_docs" not in result["url"]:
                    continue
                match = re.search(r"pattern=(.*?)#doc", result["url"])
                if not match:
                    continue
                full_name = match.group(1)
                results.append({
                    "full_name": full_name,
                    "formal_statement": result["formal_statement"],
                    "informal_statement": result["informal_statement"],
                })

        if results:
            logger.info("leanfinder.search succeeded: %d results", len(results))
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            logger.info("leanfinder.search: no mathlib4 results found")
            print("No mathlib4 results found.")
    except Exception as e:
        logger.exception("leanfinder.search failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic search for Mathlib theorems")
    parser.add_argument("query", help="Mathematical concept, proof state, or statement")
    parser.add_argument("-n", "--num-results", type=int, default=5, help="Max results (default: 5)")
    args = parser.parse_args()
    search(args.query, args.num_results)
