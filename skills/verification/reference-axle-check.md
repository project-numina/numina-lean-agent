# axle check — Compile Check

Check if Lean code compiles without errors. This is the primary tool for confirming that a proof attempt is syntactically and logically valid.

## CLI Invocation

```bash
python skills/cli/axle.py check CONTENT --environment ENV [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT` | yes | — | Lean file path or code string |
| `--environment` | yes | — | Lean environment, e.g. `lean-4.28.0` |
| `--mathlib-linter` | no | off | Enable Mathlib linter checks |
| `--ignore-imports` | no | off | Ignore imports, use environment defaults |
| `--timeout-seconds` | no | 120 | Max execution time (max 300) |

## Output

Returns:
- `okay` (bool) — whether the file compiled without errors
- `lean_messages` — list of errors, warnings, and infos with line numbers
- `failed_declarations` — list of theorem/definition names that failed

## Examples

```bash
python skills/cli/axle.py check proof.lean --environment lean-4.28.0
python skills/cli/axle.py check "theorem foo : 1 + 1 = 2 := by norm_num" --environment lean-4.28.0
python skills/cli/axle.py check proof.lean --environment lean-4.28.0 --timeout-seconds 300
```

## Notes

- Always specify `--environment` with the correct Lean version (currently `lean-4.28.0`).
- Use `--mathlib-linter` to catch style issues after a proof is working.
- `AXLE_API_KEY` environment variable is required.
