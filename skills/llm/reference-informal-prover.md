# informal-prover — Solve Math Problems with LLM + Verification

Generates a step-by-step solution to a math problem using an LLM backend, then auto-verifies and refines it in a loop until correct or the attempt limit is reached.

## CLI Invocation

```bash
python skills/cli/informal_prover.py PROBLEM [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROBLEM` | yes | — | Math problem text. Use `-` to read from stdin |
| `--backend` | no | `gemini` | LLM backend: `gemini` or `gpt` |
| `--model` | no | auto | Model name. Default: `gemini-3.1-pro-preview` (gemini) or `gpt-5.2-pro` (gpt) |
| `--temperature` | no | 0.7 | Generation temperature |
| `--max-attempts` | no | 10 | Max generate+verify+refine cycles |
| `--log-dir` | no | none | Directory to save results as JSONL |

## Output

JSON with:
- `solution` — the final solution text
- `verification` — `"correct"` or feedback on what was wrong
- `attempts` — number of generate/verify cycles used

## Examples

```bash
python skills/cli/informal_prover.py "Prove that sqrt(2) is irrational" --backend gemini
python skills/cli/informal_prover.py "Prove the AM-GM inequality" --backend gpt --max-attempts 5
echo "Prove Fermat's little theorem" | python skills/cli/informal_prover.py - --backend gemini --model gemini-2.5-pro
```

## Notes

- `GEMINI_API_KEY` is required when using `--backend gemini`.
- `OPENAI_API_KEY` is required when using `--backend gpt`.
- Increase `--max-attempts` for harder problems; decrease it if you just need a quick first-pass idea.
- Use `--log-dir` to persist results for review or debugging.
