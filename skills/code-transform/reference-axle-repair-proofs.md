# axle repair-proofs — Auto-Fix Broken Proofs

Attempts to automatically repair failing or incomplete Lean proofs using a set of configurable repair strategies.

## CLI Invocation

```bash
python skills/cli/axle.py repair-proofs CONTENT --environment ENV [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT` | yes | — | Lean file path or code string |
| `--environment` | yes | — | Lean environment, e.g. `lean-4.28.0` |
| `--names` | no | all | Comma-separated theorem names to repair |
| `--indices` | no | all | Comma-separated theorem indices (0-based, supports negative) |
| `--repairs` | no | all | Which repairs to apply (see below) |
| `--terminal-tactics` | no | `grind` | Tactics for closing goals, comma-separated (e.g. `grind,aesop,simp,rfl`) |
| `--ignore-imports` | no | off | Ignore imports |
| `--timeout-seconds` | no | 120 | Max execution time (max 300) |

## Available Repairs

| Repair name | What it does |
|---|---|
| `remove_extraneous_tactics` | Strips unreachable tactics after proof completion |
| `apply_terminal_tactics` | Replaces `sorry` with terminal tactics (e.g. `grind`, `aesop`) |
| `replace_unsafe_tactics` | Converts unsafe tactics (e.g. `native_decide`) to safer alternatives |

## Examples

```bash
python skills/cli/axle.py repair-proofs proof.lean --environment lean-4.28.0
python skills/cli/axle.py repair-proofs proof.lean --environment lean-4.28.0 --repairs apply_terminal_tactics --terminal-tactics "grind,omega,simp,rfl"
python skills/cli/axle.py repair-proofs proof.lean --environment lean-4.28.0 --names my_theorem
```

## Notes

- Run `python skills/cli/lean_check.py FILE` first to identify which theorems are broken before calling repair-proofs.
- `apply_terminal_tactics` is most useful when a proof is almost complete but ends in `sorry`.
- `AXLE_API_KEY` environment variable is required.
