# axle simplify-theorems — Simplify Proofs

Simplifies working Lean proofs by removing unnecessary code and renaming unused variables, producing cleaner and more readable proofs.

## CLI Invocation

```bash
python skills/cli/axle.py simplify-theorems CONTENT --environment ENV [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT` | yes | — | Lean file path or code string |
| `--environment` | yes | — | Lean environment, e.g. `lean-4.28.0` |
| `--names` | no | all | Comma-separated theorem names |
| `--indices` | no | all | Comma-separated theorem indices |
| `--simplifications` | no | all | Which simplifications to apply (see below) |
| `--ignore-imports` | no | off | Ignore imports |
| `--timeout-seconds` | no | 120 | Max execution time (max 300) |

## Available Simplifications

| Simplification name | What it does |
|---|---|
| `remove_unused_tactics` | Removes tactics that have no effect on the proof state |
| `remove_unused_haves` | Removes `have` bindings that are never referenced |
| `rename_unused_vars` | Renames unused variables to `_` |

## Examples

```bash
python skills/cli/axle.py simplify-theorems proof.lean --environment lean-4.28.0
python skills/cli/axle.py simplify-theorems proof.lean --environment lean-4.28.0 --simplifications remove_unused_tactics,remove_unused_haves
```

## Notes

- Only run on proofs that already compile successfully (use `python skills/cli/lean_check.py FILE` first).
- Best used as a final cleanup step after a proof is verified.
- `AXLE_API_KEY` environment variable is required.
