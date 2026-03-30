---
name: search
description: "Search tools for finding Lean theorems, lemmas, and definitions in Mathlib"
---

# Search Tools

Tools for finding relevant Lean theorems, lemmas, and definitions. All scripts are in `skills/cli/`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **leandex** | Semantic search by natural language or Lean terms | First choice for any search; **max 5 parallel queries** |
| **loogle** | Pattern-based search by type shape | When you know the type signature pattern |
| **leanfinder** | Mathlib semantic search | Alternative semantic search |
| **leansearch** | Natural language + Lean term search | Alternative to leandex |
| **state-search** | Search by proof goal/state | When you have a specific proof state to match |
| **hammer-premise** | Premise retrieval for automation | When looking for premises for automated tactics |

For full parameters and examples, read the corresponding `reference-<tool>.md` file in this directory.
