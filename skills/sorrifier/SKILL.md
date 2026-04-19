---
name: sorrifier
description: "Isolates failing proof steps by replacing them with `sorry` and extracting them into standalone lemmas to modularize and decouple complex Lean 4 proofs."
---

# Sorrifier — Proof Isolation Workflow

Structural refactoring workflow for isolating broken proof steps. Replaces failing logic with `sorry`, extracts it into a standalone lemma, and reconstructs the call site so the main theorem compiles cleanly.

## Tools Used

This workflow uses two tools from other skills. All commands go through the logging wrapper.

| Tool | Skill | Purpose |
|------|-------|---------|
| `python skills/cli/lean_check.py FILE` | [verification](../verification/SKILL.md) | Diagnose compilation errors and pinpoint failing lines |
| `python skills/cli/axle.py sorry2lemma` | [code-transform](../code-transform/SKILL.md) | Extract sorry into standalone lemma with `--reconstruct-callsite` |

For full parameter reference, see `verification/reference-lean-check.md` and `code-transform/reference-axle-sorry2lemma.md`.

## Execution Workflow

Follow these steps sequentially:

### Step 1: Diagnose
Run `python skills/cli/lean_check.py FILE` to identify failing lines.
- Read `lean_messages` for entries with `severity: "error"`.

### Step 2: Inject `sorry`
Edit the Lean code: replace the failing tactic/expression with `sorry`.
- Scope the `sorry` to the smallest failing block, not the entire theorem.

### Step 3: Verify sorrified state
Run `python skills/cli/lean_check.py FILE` again.
- Acceptance: zero errors. Warnings about `declaration uses 'sorry'` are expected.
- If errors persist, adjust sorry placement and repeat.

### Step 4: Extract to lemma
Run `python skills/cli/axle.py sorry2lemma` with:
- `--reconstruct-callsite` (required) — replaces sorry with the extracted lemma call
- `--names <theorem>` — target only the specific theorem
- Omit `--no-include-whole-context` if local context variables need capturing

### Step 5: Final verification
Run `python skills/cli/lean_check.py FILE` one last time.
- Acceptance: main theorem compiles by calling the new lemma. Unresolved logic is isolated in the extracted lemma.

## Example

**Broken state:**
```lean
import Mathlib.Tactic

theorem sum_of_squares_helper (n : ℕ) : (n + 1)^2 = n^2 + 2*n + 1 := by
  have h1 : (n + 1)^2 = (n + 1) * (n + 1) := by ring
  rw [h1]
  exact magic_solve n  -- error: unknown identifier
```

**After sorrify + extract:**
```bash
python skills/cli/axle.py sorry2lemma file.lean --environment lean-4.28.0 --names sum_of_squares_helper --reconstruct-callsite
```

```lean
import Mathlib.Tactic

lemma sum_of_squares_helper_lemma_1 (n : ℕ) (h1 : (n + 1) ^ 2 = (n + 1) * (n + 1)) :
  (n + 1) * (n + 1) = n ^ 2 + 2 * n + 1 := by
  sorry

theorem sum_of_squares_helper (n : ℕ) : (n + 1)^2 = n^2 + 2*n + 1 := by
  have h1 : (n + 1)^2 = (n + 1) * (n + 1) := by ring
  rw [h1]
  exact sum_of_squares_helper_lemma_1 n h1
```

## Best Practices

- **Scope narrowly:** Sorry the specific subgoal or `have` statement, not the entire theorem.
- **Rename:** The tool generates generic names (e.g., `lemma_1`). Rename to something meaningful.
- **Next step:** Once extracted, solve the lemma independently using `informal_prover` or manual proof.
