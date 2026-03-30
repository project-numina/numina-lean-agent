# leanfinder — Mathlib Semantic Search

Searches Mathlib theorems/definitions semantically by mathematical concept or proof state.

## CLI Invocation

```bash
python skills/cli/leanfinder.py QUERY [-n NUM_RESULTS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUERY` | yes | — | Mathematical concept, proof state, or statement definition |
| `-n, --num-results` | no | 5 | Maximum number of results |

## Examples

```bash
python skills/cli/leanfinder.py "sum of squares is non-negative"
python skills/cli/leanfinder.py "injectivity of composition"
python skills/cli/leanfinder.py "⊢ Finset.sum s f ≤ Finset.sum s g" -n 8
```

## Notes

- Best for: natural language math statements, proof states, statement fragments.
- Multiple targeted queries beat one complex query.
- For exact pattern matching, prefer `loogle`. For identifier search, prefer `leandex`.
