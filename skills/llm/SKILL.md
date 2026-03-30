---
name: llm
description: "LLM-assisted tools for informal proofs, proof strategy discussion, and code simplification"
---

# LLM Tools

LLM-assisted tools for theorem proving support. All scripts are in `skills/cli/`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **informal-prover** | Generate and verify step-by-step math solutions in a loop | When you want an LLM to attempt a full solution with auto-verification |
| **discussion-partner** | Free-form discussion about proof strategies or Lean code | When you are stuck and want high-level strategic advice |
| **code-golf** | Shorten and simplify an existing Lean proof via Gemini | After a proof works, to get a more elegant version |

For full parameters and examples, read the corresponding `reference-<tool>.md` file in this directory.
