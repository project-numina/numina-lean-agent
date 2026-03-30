# axle extract-theorems — Split File into Individual Theorems

Parses a Lean file and returns structured metadata for each theorem/definition, including its signature, type, dependencies, and proof statistics.

## CLI Invocation

```bash
python skills/cli/axle.py extract-theorems CONTENT --environment ENV [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT` | yes | — | Lean file path or code string |
| `--environment` | yes | — | Lean environment, e.g. `lean-4.28.0` |
| `--ignore-imports` | no | off | Ignore imports |
| `--timeout-seconds` | no | 120 | Max execution time (max 300) |

## Output

Returns per-theorem records containing:
- `declaration` — full declaration text
- `signature` — theorem signature
- `type` — elaborated type
- `type_hash` — hash of the type (for deduplication)
- `is_sorry` — whether the proof contains sorry
- `dependencies` — list of referenced declarations
- `tactic_counts` — frequency of each tactic used
- `proof_length` — number of proof steps

## Examples

```bash
python skills/cli/axle.py extract-theorems mathlib_file.lean --environment lean-4.28.0
python skills/cli/axle.py extract-theorems "theorem foo : 1 + 1 = 2 := by norm_num" --environment lean-4.28.0
```

## Notes

- Useful for analysis, dataset construction, or understanding a file's structure before modifying it.
- `is_sorry` can be used to quickly identify which theorems still need proofs.
- `AXLE_API_KEY` environment variable is required.
