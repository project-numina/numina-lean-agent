---
name: code-transform
description: "Code transformation tools for repairing, simplifying, and extracting Lean proofs"
---

# Code Transform Tools

Tools for automatically transforming and improving Lean proof code. All scripts use `python skills/cli/axle.py <subcommand>`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **axle repair-proofs** | Auto-fix broken proofs using configurable repair strategies | When a proof fails and you want automated repair before manual editing |
| **axle simplify-theorems** | Clean up proofs by removing unused tactics and bindings | As a final cleanup step after a proof is verified |
| **axle sorry2lemma** | Lift sorry placeholders into standalone named lemmas | When a proof has multiple sorry sub-goals you want to tackle independently |
| **axle extract-theorems** | Split a Lean file into structured per-theorem records | For analysis, dataset construction, or understanding file structure |

For full parameters and examples, read the corresponding `reference-<tool>.md` file in this directory.
