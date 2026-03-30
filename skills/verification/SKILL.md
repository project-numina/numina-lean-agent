---
name: verification
description: "Verification tools for compiling, validating, and disproving Lean theorems"
---

# Verification Tools

Tools for verifying Lean code correctness. All scripts use `python skills/cli/axle.py <subcommand>`.

## Available Tools

| Tool | Purpose | When to use |
|------|---------|-------------|
| **axle check** | Compile a Lean file and report errors | First step to validate any proof attempt |
| **axle verify-proof** | Validate a proof matches a formal statement | When you need to confirm a proof proves exactly the right theorem |
| **axle disprove** | Attempt to disprove theorems by proving negation | Before investing effort in a proof, check if the conjecture is false |

For full parameters and examples, read the corresponding `reference-<tool>.md` file in this directory.
