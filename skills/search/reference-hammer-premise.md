# hammer-premise — Premise Search by Proof Goal

Searches for relevant premises using the Lean Hammer premise retrieval service at leanpremise.net.

## CLI Invocation

```bash
python skills/cli/hammer_premise.py GOAL [-n NUM_RESULTS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOAL` | yes | — | Proof state / goal text |
| `-n, --num-results` | no | 32 | Maximum number of premises to return |

## Examples

```bash
python skills/cli/hammer_premise.py "⊢ ∀ n : ℕ, 0 ≤ n"
python skills/cli/hammer_premise.py "⊢ Real.exp x > 0" -n 20
```

## Notes

- Returns a larger set of candidates (default 32) compared to other search tools — useful for feeding into a hammer tactic.
- Environment variable: `LEAN_HAMMER_URL` overrides the default endpoint (`http://leanpremise.net`).
- Best used when you have a concrete goal and want a broad list of potentially applicable lemmas.
