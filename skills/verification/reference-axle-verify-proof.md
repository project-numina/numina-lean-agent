# axle verify-proof — Verify Proof Matches Statement

Validates a candidate proof against a formal statement specification. Checks that the proof proves exactly the stated theorem (not a different, weaker, or sorry-based version).

## CLI Invocation

```bash
python skills/cli/axle.py verify-proof FORMAL_STATEMENT CONTENT --environment ENV [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `FORMAL_STATEMENT` | yes | — | Sorried theorem to verify against |
| `CONTENT` | yes | — | Candidate proof code |
| `--environment` | yes | — | Lean environment, e.g. `lean-4.28.0` |
| `--permitted-sorries` | no | none | Comma-separated theorem names allowed to contain sorry |
| `--mathlib-linter` | no | off | Enable Mathlib linters |
| `--use-def-eq` | no | on | Use definitional equality for type comparison |
| `--ignore-imports` | no | off | Ignore import mismatches |
| `--timeout-seconds` | no | 120 | Max execution time (max 300) |

## Output

Returns:
- `okay` (bool) — whether the proof is valid and matches the statement
- `failed_declarations` — names of declarations that failed verification
- `tool_messages` — detailed verification messages

## Examples

```bash
python skills/cli/axle.py verify-proof "theorem foo : 1 + 1 = 2 := by sorry" proof.lean --environment lean-4.28.0
python skills/cli/axle.py verify-proof formal_stmt.lean candidate.lean --environment lean-4.28.0 --permitted-sorries helper_lemma
```

## Notes

- The `FORMAL_STATEMENT` should be a sorried version of the theorem you want to prove.
- Use `--permitted-sorries` to allow helper lemmas to contain sorry while still verifying the main theorem.
- `AXLE_API_KEY` environment variable is required.
