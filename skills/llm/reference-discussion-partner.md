# discussion-partner — Discuss with Gemini/GPT

Free-form discussion about proof strategies, Lean code, math problems, or anything else related to theorem proving.

## CLI Invocation

```bash
python skills/cli/discussion_partner.py QUESTION [OPTIONS]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `QUESTION` | yes | — | Question or context to discuss. Use `-` to read from stdin |
| `--backend` | no | `gemini` | LLM backend: `gemini` or `gpt` |
| `--model` | no | auto | Model name. Default: `gemini-3.1-pro-preview` (gemini) or `gpt-5.2-pro` (gpt) |

## Examples

```bash
python skills/cli/discussion_partner.py "How should I approach this induction proof?" --backend gemini
python skills/cli/discussion_partner.py "What tactic should I use for this goal: ⊢ n + 0 = n" --backend gpt
cat stuck_proof.lean | python skills/cli/discussion_partner.py - --backend gemini
```

## Notes

- `GEMINI_API_KEY` is required when using `--backend gemini`.
- `OPENAI_API_KEY` is required when using `--backend gpt`.
- Pipe in a `.lean` file via stdin (`-`) to give the model full context about your current proof state.
- Use this tool when you are stuck and want high-level strategic advice before searching for specific lemmas.
