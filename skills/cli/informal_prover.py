#!/usr/bin/env python3
"""Solve math problems with LLM (Gemini/GPT) and verify the solution."""
import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(__file__).parents[2] / "cli.log")],
)
logger = logging.getLogger(__name__)

SOLUTION_PROMPT = """You are a Formal Logic Expert and Mathematical Proof Engine. Your goal is to derive proofs that are rigorously structured, formalization-ready, and devoid of ambiguity.

Core Constraints:

- Purely Algebraic/Symbolic: Do NOT use geometric intuition, visual symmetry, or graphical interpretations as proof. All geometric concepts must be translated into their precise algebraic or analytic definitions.

- Atomic Steps: Decompose reasoning into the smallest possible logical units. Do not combine multiple deductive steps into one.

- No Hand-waving: Forbidden phrases include 'obviously,' 'it is clear that,' 'by inspection,' or 'intuitively.'

Instructions:

- Definitions: Explicitly state all variable types, definitions, and assumptions at the start.

- Step-by-Step Derivation: Number every step (1, 2, 3...).

- Explicit Justification: For EACH step, you must explicitly state the rule of inference, algebraic identity, axiom, or theorem used (e.g., "Distributive Property," "Triangle Inequality," "Definition of Continuity").

- Formal Structure: Present the proof in a format that could easily be translated into a proof assistant language (like Lean or Coq).

- Calculations: Show every intermediate stage of simplification or substitution. Do not skip algebraic manipulation steps.

Problem Statement: {problem}"""

VERIFY_PROMPT = """Your task is to evaluate the quality of a solution to a problem. The problem may ask for a proof of a statement, or ask for an answer. If finding an answer is required, the solution should present the answer, and it should also be a rigorous proof of that answer being valid.

Please evaluate the solution and score it according to the following criteria:

- If the solution is completely correct, with all steps executed properly and clearly demonstrated, then the score is 1

- If the solution is generally correct, but with some details omitted or minor errors, then the score is 0.5

- If the solution does not actually address the required problem, contains fatal errors, or has severe omissions, then the score is 0

- Additionally, referencing anything from any paper does not save the need to prove the reference. It's okay IF AND ONLY IF the solution also presents a valid proof of the reference argument(s); otherwise, if the solution omits the proof or if the proof provided is not completely correct, the solution should be scored according to the criteria above, and definitely not with a score of 1

Please carefully reason out and analyze the quality of the solution below, and in your final response present a detailed evaluation of the solution's quality followed by your score.

Therefore, your response should be in the following format:

Here is my evaluation of the solution:

[Your evaluation here. You are required to present in detail the key steps of the solution or the steps for which you had doubts regarding their correctness, and explicitly analyze whether each step is accurate: for correct steps, explain why you initially doubted their correctness and why they are indeed correct; for erroneous steps, explain the reason for the error and the impact of that error on the solution.]

Based on my evaluation, the final overall score should be: \\boxed{{...}}

[where ... should be the final overall score (0, 0.5, or 1, and nothing else) based on the above criteria]

---

Here is your task input:

## Problem
{problem}

## Solution
{student_solution}"""

REFINEMENT_PROMPT = """You are given a mathematical problem, an existing solution, and feedback on that solution.

Your task is to produce a **revised solution** that is more complete, rigorous, and clearly justified.

---

### Problem
{problem}

---

### Previous Solution
{solution}

---

### Feedback
{feedback}

---

### Instructions

- Carefully read the feedback and determine which points are **valid** and which may be due to **misunderstanding or evaluator error**.
- If you **agree** with a feedback item:
  - Revise the solution to fix the issue.
  - Add missing steps, clarify logical transitions, or strengthen rigor as needed.
- If you **disagree** with a feedback item:
  - Keep the original reasoning if it is correct.
  - Add **explicit explanations or clarifications** to prevent future misunderstandings.
- Do **not** simply restate the feedback.
- The final solution should be:
  - Self-contained
  - Logically coherent
  - Mathematically rigorous
  - Easy to follow for a careful reader

---

### Output Format

Provide **only** the revised solution below.

### Revised Solution
"""


def _call_gemini(prompt: str, model: str, temperature: float) -> str | None:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        print("Error: Please set GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        return response.text if response.text else None
    except Exception as e:
        logger.exception("_call_gemini failed: %s", e)
        print(f"LLM error: {e}", file=sys.stderr)
        return None


def _call_gpt(prompt: str, model: str, temperature: float) -> str | None:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        print("Error: Please set OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)
    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={"effort": "high"},
            text={"verbosity": "high"},
        )
        if response.output:
            return response.output[-1].content[0].text
        return None
    except Exception as e:
        logger.exception("_call_gpt failed: %s", e)
        print(f"LLM error: {e}", file=sys.stderr)
        return None


def prove(
    math_problem: str,
    backend: str = "gemini",
    model: str | None = None,
    temperature: float = 0.7,
    max_attempts: int = 10,
    log_dir: str | None = None,
) -> None:
    logger.info("prove called: backend=%s model=%s max_attempts=%d problem_len=%d", backend, model, max_attempts, len(math_problem))
    if backend == "gemini":
        model = model or "gemini-3.1-pro-preview"
        call_llm = lambda p: _call_gemini(p, model, temperature)
    elif backend == "gpt":
        model = model or "gpt-5.2-pro"
        call_llm = lambda p: _call_gpt(p, model, temperature)
    else:
        print(f"Error: backend must be 'gemini' or 'gpt', got '{backend}'", file=sys.stderr)
        sys.exit(1)

    solution = None
    verification = None

    for attempt in range(1, max_attempts + 1):
        # Generate solution
        if attempt == 1:
            prompt = SOLUTION_PROMPT.format(problem=math_problem)
        else:
            if not verification:
                break
            prompt = REFINEMENT_PROMPT.format(
                problem=math_problem, solution=solution, feedback=verification
            )

        solution = call_llm(prompt)
        if not solution:
            if attempt == max_attempts:
                print(json.dumps({"solution": None, "verification": "Failed to generate solution"}))
                return
            continue

        # Verify
        verify_prompt = VERIFY_PROMPT.format(problem=math_problem, student_solution=solution)
        verification = call_llm(verify_prompt)
        if not verification:
            if attempt == max_attempts:
                print(json.dumps({"solution": solution, "verification": "Verification failed (API error)"}))
                return
            continue

        # Check score
        match = re.search(r"\\boxed\{(.*?)\}", verification)
        score = match.group(1).strip() if match else None

        if score == "1":
            logger.info("prove succeeded on attempt %d", attempt)
            result = {"solution": solution, "verification": "correct", "attempts": attempt}
            print(json.dumps(result, ensure_ascii=False))
            _log(log_dir, math_problem, solution, "correct")
            return

        if attempt == max_attempts:
            logger.warning("prove exhausted attempts (%d), final score=%s", max_attempts, score)
            result = {"solution": solution, "verification": f"incorrect\n{verification}", "attempts": attempt}
            print(json.dumps(result, ensure_ascii=False))
            _log(log_dir, math_problem, solution, f"incorrect\n{verification}")
            return


def _log(log_dir: str | None, problem: str, solution: str, verification: str) -> None:
    if not log_dir:
        return
    try:
        log_path = os.path.join(log_dir, "informal_prover_history.jsonl")
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "math_problem": problem,
            "solution": solution,
            "verification": verification,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solve math problems with LLM + verification")
    parser.add_argument("problem", help="Math problem text (or - for stdin)")
    parser.add_argument("--backend", choices=["gemini", "gpt"], default="gemini", help="LLM backend")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-attempts", type=int, default=10, help="Max generate+verify attempts")
    parser.add_argument("--log-dir", default=None, help="Directory for logging results")
    args = parser.parse_args()

    problem = sys.stdin.read() if args.problem == "-" else args.problem
    prove(problem, args.backend, args.model, args.temperature, args.max_attempts, args.log_dir)
