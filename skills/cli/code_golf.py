#!/usr/bin/env python3
"""Simplify Lean proofs using Google Gemini."""
import argparse
import logging
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(__file__).parents[2] / "cli.log")],
)
logger = logging.getLogger(__name__)

GOLF_PROMPT = """You are given a correct Lean 4 proof of a mathematical theorem.
Your goal is to simplify and clean up the proof, making it shorter and more readable while ensuring it is still correct.

Here is the original proof:
```lean4
{formal_code}
```

Now, provide your simplified proof. Do NOT modify the theorem or header, and surround your proof in ```lean4 and ``` tags."""


def golf(lean_code: str, model: str = "gemini-3.1-pro-preview", temperature: float = 0.7) -> None:
    logger.info("golf called: model=%s temperature=%s code_len=%d", model, temperature, len(lean_code))
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        print("Error: Please set the GEMINI_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    if not lean_code.strip():
        logger.error("No code provided")
        print("Error: No code provided.", file=sys.stderr)
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
        prompt = GOLF_PROMPT.format(formal_code=lean_code)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        if response.text:
            logger.info("golf succeeded: response_len=%d", len(response.text))
            print(response.text)
        else:
            logger.error("Gemini returned empty response")
            print("Error: Gemini returned empty response.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        logger.exception("golf failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simplify Lean proofs using Gemini")
    parser.add_argument("lean_code", help="Lean code to simplify (or - for stdin)")
    parser.add_argument("--model", default="gemini-3.1-pro-preview", help="Gemini model")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature")
    args = parser.parse_args()

    code = sys.stdin.read() if args.lean_code == "-" else args.lean_code
    golf(code, args.model, args.temperature)
