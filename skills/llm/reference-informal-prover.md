# informal-prover — Solve Math Problems with LLM + 3-Model Verification

Generates a step-by-step solution to a math problem using an LLM backend, then auto-verifies it with a panel of three models (Claude, GPT, Gemini) and refines via Gemini until all three score 1 or the attempt limit is reached.

## CLI Invocation

```bash
python skills/cli/informal_prover.py PROBLEM [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROBLEM` | yes | — | Math problem text. Use `-` to read from stdin |
| `--backend` | no | `gemini` | LLM backend for solution **generation**: `gemini` or `gpt` |
| `--model` | no | auto | Override generator model. Default: `gemini-3.1-pro-preview` (gemini) or `gpt-5.4-pro` (gpt) |
| `--temperature` | no | 0.7 | Generation/verification temperature |
| `--max-attempts` | no | 10 | Max generate+verify+refine cycles |
| `--log-dir` | no | none | Directory to save results as JSONL |
| `--claude-verify-model` | no | `claude-opus-4-7` | Claude model used in the verification panel |
| `--gpt-verify-model` | no | `gpt-5.4-pro` | GPT model used in the verification panel |
| `--gemini-verify-model` | no | `gemini-3.1-pro-preview` | Gemini model used in the verification panel |
| `--refine-model` | no | `gemini-3.1-pro-preview` | Gemini model used to refine the solution |

## Verification & Refinement Loop

1. Generate an initial solution using `--backend`.
2. Send the solution to **all three** verifiers (Claude, GPT, Gemini) in parallel. Each returns a detailed evaluation ending with `\boxed{0}`, `\boxed{0.5}`, or `\boxed{1}`.
3. If every verifier returns `1`, the solution is accepted.
4. Otherwise, every non-`1` evaluation is concatenated (without model attribution) and passed to Gemini as "Issues We Found". Gemini produces a revised solution and the loop repeats.

## Output

JSON with:
- `solution` — the final solution text
- `verification` — `"correct"` or `"incorrect\n<combined non-1 evaluations>"`
- `attempts` — number of generate/verify cycles used

## Examples

```bash
python skills/cli/informal_prover.py "Prove that sqrt(2) is irrational" --backend gemini
python skills/cli/informal_prover.py "Prove the AM-GM inequality" --backend gpt --max-attempts 5
echo "Prove Fermat's little theorem" | python skills/cli/informal_prover.py - --backend gemini --model gemini-2.5-pro
```

## Notes

- `GEMINI_API_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` are **all** required — the verification panel always queries the three models in parallel.
- `GEMINI_API_KEY` is additionally used for refinement and (when `--backend gemini`) for generation.
- Increase `--max-attempts` for harder problems; decrease it if you just need a quick first-pass idea.
- Use `--log-dir` to persist results for review or debugging.
