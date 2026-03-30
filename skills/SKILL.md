---
name: numina-lean-agent
description: "Lean 4 theorem proving toolkit: search lemmas, verify proofs, repair/simplify code, and get LLM-assisted informal proofs"
---

# Numina Lean Agent — Skills Index

## Skills

| Skill | Description |
|-------|-------------|
| [search](search/SKILL.md) | Search tools: leandex, loogle, leanfinder, leansearch, state-search, hammer-premise |
| [verification](verification/SKILL.md) | Verification: axle check, verify-proof, disprove |
| [code-transform](code-transform/SKILL.md) | Code transforms: repair-proofs, simplify-theorems, sorry2lemma, extract-theorems |
| [llm](llm/SKILL.md) | LLM tools: informal_prover, discussion_partner, code_golf |

## Environment variables
- `GEMINI_API_KEY` — informal_prover (gemini), code_golf, discussion_partner (gemini)
- `OPENAI_API_KEY` — informal_prover (gpt), discussion_partner (gpt)
- `AXLE_API_KEY` — all axle commands
