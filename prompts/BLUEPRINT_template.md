# Project Blueprint

> Single source of truth for this theorem's progress. Update IMMEDIATELY after
> any lemma status change. Do not batch updates.

## Progress Summary
- **Total items**: <N>
- **Status**: done: <a> | partial: <b> | todo: <c>

Status legend (from `prompts/docs/prompts/common.md`):
- `done`     — completely proven, no sorry, compiles
- `partial`  — partially proven, still has sorry
- `todo`     — not started

---

# lemma lem:<label>

## meta
- **label**: `lem:<label>`                    <!-- same as the blueprint .tex `\label{lem:...}` -->
- **lean**: `<Namespace.declaration>`         <!-- same as the blueprint .tex `\lean{...}` -->
- **uses**: [[lem:<other1>], [lem:<other2>]]  <!-- dependency list; mirror the .tex `\uses{...}` -->
- **file**: `LiveProveBench/<Problem>/<File>.lean:<line>`
- **status**: `todo` | `partial` | `done`
- **attempts**: `<current> / <budget>`

## statement
<Informal statement, copied/paraphrased from the blueprint .tex.>

## proof
<Informal proof, detailed enough to formalize step-by-step.
 If still thinking, leave a stub and return after consulting Gemini
 (`skills/cli/informal_prover.py`) or the Blueprint Agent workflow
 in `prompts/docs/prompts/blueprint_agent.md`.>

---

# theorem thm:<main>

## meta
- **label**: `thm:<main>`
- **lean**: `<Namespace.main_theorem>`
- **uses**: [[lem:<sub1>], [lem:<sub2>]]
- **file**: `LiveProveBench/<Problem>/MainTheorem.lean:<line>`
- **status**: `todo` | `partial` | `done`
- **attempts**: `<current> / <budget>`

## statement
<Main theorem statement.>

## proof
<Informal proof: how the sub-lemmas compose into the main theorem.>

---

## Notes

- Each `lemma` / `theorem` / `definition` in the `.tex` blueprint should have
  one entry here, in dependency order (leaves first, main theorem last).
- Keep `meta.file` pointing at the actual Lean declaration (use `file:line`).
- When a lemma becomes `done`, also add a status comment in the Lean source:

  ```lean
  /- (by claude)
  State: done
  Priority: <1-5>
  Attempts: <N> / <M>
  tmp file: <path_or_empty>
  -/
  lemma name : statement := by ...
  ```

  (Format from `prompts/docs/prompts/common.md` §3.)
