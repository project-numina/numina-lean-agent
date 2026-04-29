# Numina Lean Agent

You are a Lean 4 theorem proving agent with access to search, verification, repair, and LLM-assisted tools.

For the full tool reference (all parameters, examples, usage), read `skills/SKILL.md`.

## Lean Environment

Current environment: `lean-4.28.0`

Available environments: `lean-4.26.0`, `lean-4.27.0`, `lean-4.28.0`

Use this value for all `--environment` flags in axle commands.

## Environment Variables
- `GEMINI_API_KEY` — Gemini-based tools
- `OPENAI_API_KEY` — GPT-based tools
- `ANTHROPIC_API_KEY` — Claude-based tools (informal_prover verifier panel)
- `AXLE_API_KEY` — all axle commands
- `LEANEXPLORE_API_KEY` — leanexplore search (required; falls back to leandex if unset or on error)
