# axle sorry2lemma — Extract Sorry into Standalone Lemmas

Lifts `sorry` placeholders (and optionally errors) inside a proof into separate, standalone lemma declarations. This makes it easier to tackle each sub-goal independently.

## CLI Invocation

```bash
python skills/cli/axle.py sorry2lemma CONTENT --environment ENV [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT` | yes | — | Lean file path or code string |
| `--environment` | yes | — | Lean environment, e.g. `lean-4.28.0` |
| `--names` | no | all | Comma-separated theorem names |
| `--indices` | no | all | Comma-separated theorem indices |
| `--no-extract-sorries` | no | on | Disable lifting sorries into standalone lemmas |
| `--no-extract-errors` | no | on | Disable lifting errors into standalone lemmas |
| `--no-include-whole-context` | no | on | Don't include all context variables when extracting |
| `--reconstruct-callsite` | no | off | Replace sorry with extracted lemma call |
| `--verbosity` | no | 0 | Pretty-printer verbosity (0=default, 1=robust, 2=extra robust) |
| `--ignore-imports` | no | off | Ignore imports |
| `--timeout-seconds` | no | 120 | Max execution time (max 300) |

## Examples

```bash
python skills/cli/axle.py sorry2lemma proof.lean --environment lean-4.28.0
python skills/cli/axle.py sorry2lemma proof.lean --environment lean-4.28.0 --reconstruct-callsite
python skills/cli/axle.py sorry2lemma proof.lean --environment lean-4.28.0 --verbosity 1
```

## Notes

- Use `--reconstruct-callsite` to get a version of the file where each sorry is replaced by a call to the extracted lemma — this keeps the main proof structure intact while isolating sub-goals.
- Increase `--verbosity` if the default pretty-printing produces unreadable output.
- `AXLE_API_KEY` environment variable is required.
