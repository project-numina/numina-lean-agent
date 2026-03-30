# axle disprove — Try to Disprove a Theorem

Attempts to prove the negation of theorems. Useful for checking whether a conjecture is false before investing effort in proving it.

## CLI Invocation

```bash
python skills/cli/axle.py disprove CONTENT --environment ENV [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT` | yes | — | Lean file path or code string |
| `--environment` | yes | — | Lean environment, e.g. `lean-4.28.0` |
| `--names` | no | all | Comma-separated theorem names to try |
| `--indices` | no | all | Comma-separated theorem indices (0-based, supports negative) |
| `--terminal-tactics` | no | `grind` | Tactics to try for proving negation, comma-separated |
| `--ignore-imports` | no | off | Ignore imports |
| `--timeout-seconds` | no | 120 | Max execution time (max 300) |

## Output

Returns:
- `disproved_theorems` — list of theorem names successfully disproved
- Per-theorem `results` with details of what tactic worked

## Examples

```bash
python skills/cli/axle.py disprove conjecture.lean --environment lean-4.28.0
python skills/cli/axle.py disprove conjecture.lean --environment lean-4.28.0 --names my_conjecture --terminal-tactics "grind,omega,decide"
```

## Notes

- If a theorem is disproved, it is definitely false — do not attempt to prove it.
- If disprove fails, the theorem may still be false (the tactic may just not be strong enough).
- `AXLE_API_KEY` environment variable is required.
