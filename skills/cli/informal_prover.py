#!/usr/bin/env python3
"""Solve math problems with LLM (Gemini/GPT) and verify with Claude+GPT+Gemini."""
import argparse
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(Path(os.environ.get("CLI_LOG_PATH", Path(__file__).parents[2] / "cli.log")))],
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

REFINEMENT_PROMPT = """You are given a mathematical problem, an existing solution, and a set of issues we found in that solution after careful review.

Your task is to produce a **revised solution** that is more complete, rigorous, and clearly justified.

---

### Problem
{problem}

---

### Previous Solution
{solution}

---

### Issues We Found
{issues}

---

### Instructions

- Carefully read each reported issue and decide whether it is **valid** or may be due to a **misunderstanding of the original argument**.
- If you **agree** that an issue is valid:
  - Revise the solution to fix it.
  - Add missing steps, clarify logical transitions, or strengthen rigor as needed.
- If you **disagree** with an issue:
  - Keep the original reasoning if it is correct.
  - Add **explicit explanations or clarifications** to prevent future misunderstandings.
- Do **not** simply restate the issues.
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


def _call_gemini(prompt: str, model: str, temperature: float) -> tuple[str | None, int, int]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        return None, 0, 0
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        usage = response.usage_metadata
        in_tok = getattr(usage, "prompt_token_count", 0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0
        logger.info("_call_gemini: in_tokens=%d out_tokens=%d", in_tok, out_tok)
        return (response.text if response.text else None), in_tok, out_tok
    except Exception as e:
        logger.exception("_call_gemini failed: %s", e)
        print(f"LLM error: {e}", file=sys.stderr)
        return None, 0, 0


def _call_gpt(prompt: str, model: str, temperature: float) -> tuple[str | None, int, int]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return None, 0, 0
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=prompt,
            reasoning={"effort": "high"},
            text={"verbosity": "high"},
        )
        usage = response.usage
        in_tok = getattr(usage, "input_tokens", 0) or 0
        out_tok = getattr(usage, "output_tokens", 0) or 0
        logger.info("_call_gpt: in_tokens=%d out_tokens=%d", in_tok, out_tok)
        if response.output:
            return response.output[-1].content[0].text, in_tok, out_tok
        return None, in_tok, out_tok
    except Exception as e:
        logger.exception("_call_gpt failed: %s", e)
        print(f"LLM error: {e}", file=sys.stderr)
        return None, 0, 0


def _call_claude(prompt: str, model: str, temperature: float) -> tuple[str | None, int, int]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None, 0, 0
    try:
        import anthropic

        del temperature  # Some Claude models reject the temperature parameter.
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=16384,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = response.usage
        in_tok = getattr(usage, "input_tokens", 0) or 0
        out_tok = getattr(usage, "output_tokens", 0) or 0
        logger.info("_call_claude: in_tokens=%d out_tokens=%d", in_tok, out_tok)
        text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        text = "\n".join(text_parts) if text_parts else None
        return text, in_tok, out_tok
    except Exception as e:
        logger.exception("_call_claude failed: %s", e)
        print(f"LLM error: {e}", file=sys.stderr)
        return None, 0, 0


def _extract_score(verification: str | None) -> str | None:
    if not verification:
        return None
    match = re.search(r"\\boxed\{(.*?)\}", verification)
    return match.group(1).strip() if match else None


def _verify_with_panel(
    problem: str,
    solution: str,
    temperature: float,
    claude_model: str,
    gpt_model: str,
    gemini_model: str,
) -> tuple[bool, str | None, dict[str, str | None], bool, int, int]:
    """Run claude/gpt/gemini verifications in parallel.

    Returns:
      (accepted, combined_issues, per_model_verifications,
       has_any_score, in_tokens, out_tokens)
    """
    verify_prompt = VERIFY_PROMPT.format(problem=problem, student_solution=solution)
    callers = {
        "claude": (_call_claude, claude_model),
        "gpt": (_call_gpt, gpt_model),
        "gemini": (_call_gemini, gemini_model),
    }
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            name: executor.submit(fn, verify_prompt, model, temperature)
            for name, (fn, model) in callers.items()
        }
        results: dict[str, tuple[str | None, int, int]] = {}
        for name, future in futures.items():
            try:
                results[name] = future.result()
            except BaseException as e:
                logger.exception("verifier %s crashed: %s", name, e)
                results[name] = (None, 0, 0)

    in_tok_total = 0
    out_tok_total = 0
    issues: list[str] = []
    per_model: dict[str, str | None] = {}
    passing_scores = 0
    scored_evaluations = 0

    for name, (text, in_tok, out_tok) in results.items():
        in_tok_total += in_tok
        out_tok_total += out_tok
        per_model[name] = text
        if not text:
            logger.warning("verify panel %s produced no evaluation; ignoring", name)
            continue
        score = _extract_score(text)
        logger.info("verify panel %s score=%s", name, score)
        if score is None:
            logger.warning("verify panel %s produced no parseable score; ignoring", name)
            continue
        scored_evaluations += 1
        if score == "1":
            passing_scores += 1
            continue
        issues.append(text)

    accepted = passing_scores >= 1 and not issues
    combined = "\n\n---\n\n".join(issues) if issues else None
    return accepted, combined, per_model, scored_evaluations > 0, in_tok_total, out_tok_total


def prove(
    math_problem: str,
    backend: str = "gemini",
    model: str | None = None,
    temperature: float = 0.7,
    max_attempts: int = 10,
    log_dir: str | None = None,
    claude_verify_model: str = "claude-opus-4-7",
    gpt_verify_model: str = "gpt-5.4-pro",
    gemini_verify_model: str = "gemini-3.1-pro-preview",
    refine_model: str = "gemini-3.1-pro-preview",
) -> None:
    logger.info("prove called: backend=%s model=%s max_attempts=%d problem_len=%d", backend, model, max_attempts, len(math_problem))
    if backend == "gemini":
        gen_model = model or "gemini-3.1-pro-preview"
        call_gen = lambda p: _call_gemini(p, gen_model, temperature)
    elif backend == "gpt":
        gen_model = model or "gpt-5.4-pro"
        call_gen = lambda p: _call_gpt(p, gen_model, temperature)
    else:
        print(f"Error: backend must be 'gemini' or 'gpt', got '{backend}'", file=sys.stderr)
        sys.exit(1)

    solution: str | None = None
    issues: str | None = None
    last_panel: dict[str, str | None] = {}
    total_in_tok = 0
    total_out_tok = 0

    for attempt in range(1, max_attempts + 1):
        # Generate (attempt 1) or refine (attempt > 1)
        if attempt == 1:
            prompt = SOLUTION_PROMPT.format(problem=math_problem)
            solution, in_tok, out_tok = call_gen(prompt)
        else:
            if not issues:
                break
            prompt = REFINEMENT_PROMPT.format(
                problem=math_problem, solution=solution, issues=issues
            )
            solution, in_tok, out_tok = _call_gemini(prompt, refine_model, temperature)

        total_in_tok += in_tok
        total_out_tok += out_tok
        if not solution:
            if attempt == max_attempts:
                logger.info("prove done: in_tokens=%d out_tokens=%d", total_in_tok, total_out_tok)
                print(json.dumps({"solution": None, "verification": "Failed to generate solution"}))
                return
            continue

        # Verify with panel of three models in parallel
        accepted, issues, last_panel, has_any_score, in_tok, out_tok = _verify_with_panel(
            math_problem,
            solution,
            temperature,
            claude_verify_model,
            gpt_verify_model,
            gemini_verify_model,
        )
        total_in_tok += in_tok
        total_out_tok += out_tok

        if accepted:
            logger.info("prove succeeded on attempt %d in_tokens=%d out_tokens=%d", attempt, total_in_tok, total_out_tok)
            result = {"solution": solution, "verification": "correct", "attempts": attempt}
            print(json.dumps(result, ensure_ascii=False))
            _log(log_dir, math_problem, solution, "correct")
            return

        if not has_any_score:
            logger.warning("prove stopped on attempt %d — verifier panel did not produce any score", attempt)
            print(json.dumps({
                "solution": solution,
                "verification": "Verification failed (API error)",
                "attempts": attempt,
            }, ensure_ascii=False))
            return

        if issues is None:
            logger.warning("prove stopped on attempt %d — no verifier issues were produced", attempt)
            print(json.dumps({
                "solution": solution,
                "verification": "Verification failed (API error)",
                "attempts": attempt,
            }, ensure_ascii=False))
            return

        if attempt == max_attempts:
            scores = {name: _extract_score(text) for name, text in last_panel.items()}
            logger.warning("prove exhausted attempts (%d) final scores=%s in_tokens=%d out_tokens=%d", max_attempts, scores, total_in_tok, total_out_tok)
            result = {"solution": solution, "verification": f"incorrect\n{issues}", "attempts": attempt}
            print(json.dumps(result, ensure_ascii=False))
            _log(log_dir, math_problem, solution, f"incorrect\n{issues}")
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
    parser = argparse.ArgumentParser(description="Solve math problems with LLM + 3-model verification")
    parser.add_argument("problem", nargs="?", default=None,
                        help="Math problem text, '-' or omit to read from stdin")
    parser.add_argument("--file", "-f", default=None, metavar="PATH",
                        help="Read problem from a file (avoids shell escaping issues)")
    parser.add_argument("--backend", choices=["gemini", "gpt"], default="gemini", help="LLM backend for solution generation")
    parser.add_argument("--model", default=None, help="Override generator model name")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-attempts", type=int, default=10, help="Max generate+verify+refine cycles")
    parser.add_argument("--log-dir", default=None, help="Directory for logging results")
    parser.add_argument("--claude-verify-model", default="claude-opus-4-7", help="Claude model used for verification")
    parser.add_argument("--gpt-verify-model", default="gpt-5.4-pro", help="GPT model used for verification")
    parser.add_argument("--gemini-verify-model", default="gemini-3.1-pro-preview", help="Gemini model used for verification")
    parser.add_argument("--refine-model", default="gemini-3.1-pro-preview", help="Gemini model used for refinement")
    args = parser.parse_args()

    if args.file:
        problem = Path(args.file).read_text(encoding="utf-8")
    elif args.problem is None or args.problem == "-":
        problem = sys.stdin.read()
    else:
        problem = args.problem
    prove(
        problem,
        args.backend,
        args.model,
        args.temperature,
        args.max_attempts,
        args.log_dir,
        args.claude_verify_model,
        args.gpt_verify_model,
        args.gemini_verify_model,
        args.refine_model,
    )
