# loogle — Pattern Matching Search

Searches by constant name, name substring, subexpression pattern, type shape, or conclusion.

## CLI Invocation

```bash
python skills/cli/loogle.py QUERY [-n NUM_RESULTS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUERY` | yes | — | Loogle query pattern |
| `-n, --num-results` | no | 8 | Maximum number of results |

## Query Patterns

| Pattern type | Example |
|---|---|
| By constant name | `Real.sin` |
| By name substring | `"differ"` |
| By subexpression | `_ * (_ ^ _)` |
| Non-linear subexpression | `Real.sqrt ?a * Real.sqrt ?a` |
| By type shape | `(?a -> ?b) -> List ?a -> List ?b` |
| By conclusion | `\|- tsum _ = _ * tsum _` |
| By conclusion with hypotheses | `\|- _ < _ → tsum _ < tsum _` |

## Examples

```bash
python skills/cli/loogle.py "Real.sin"
python skills/cli/loogle.py "_ * (_ ^ _)" -n 10
python skills/cli/loogle.py "|- _ < _ → tsum _ < tsum _"
```

## Notes

- Use `?a`, `?b`, etc. for named metavariables that must match the same expression in multiple positions (non-linear patterns).
- Use `_` for anonymous wildcards.
- Prefix the conclusion with `|-` to anchor the search to the return type.
