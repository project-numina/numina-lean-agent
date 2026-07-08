# Common Agent Rules

> **Purpose**: Shared rules and conventions for ALL agents in the Lean theorem proving system

---

## 1. No Axioms / No Admit Policy

**NEVER use `axiom` or `admit`. ALWAYS use `sorry` instead.**

### Why
- `axiom` creates unfounded assumptions that invalidate proofs
- `sorry` explicitly marks gaps while allowing compilation
- `axiom` and `admit` hide incompleteness, `sorry` makes it visible

### Rules
1. If you cannot prove something, use `sorry`
2. Leave ONLY the smallest stuck part as `sorry`
3. Everything else must be proven
4. Code MUST compile cleanly (no severity-1 errors)
5. **NEVER write `admit`** - only humans can use `admit`

### About `admit` in Existing Code

```
┌─────────────────────────────────────────────────────────────────┐
│  `admit` in existing code = HUMAN-DESIGNATED, TREAT AS PROVEN   │
│                                                                 │
│  - Treat `admit` as if it were a completed proof                │
│  - You MUST USE lemmas/theorems that have `admit`               │
│  - Do NOT try to prove or replace `admit`                       │
│  - Do NOT add new `admit` yourself (use `sorry` instead)        │
│                                                                 │
│  ⚠️  COMMON MISTAKE - DO NOT DO THIS:                           │
│  "Since X uses admit, I'll leave this as sorry"                 │
│  This is WRONG! You should USE X, not skip the proof!           │
└─────────────────────────────────────────────────────────────────┘
```

### Critical Clarification

```
┌─────────────────────────────────────────────────────────────────┐
│  "Depends on admit" ≠ "Can leave as sorry"                      │
│                                                                 │
│  If theorem A uses admit, and you need A to prove B:            │
│    ❌ WRONG: "A has admit, so I leave B as sorry"               │
│    ✅ RIGHT: Use A directly to prove B completely               │
│                                                                 │
│  The admit is the HUMAN's responsibility, not yours.            │
│  Your job is to prove everything EXCEPT the admit itself.       │
└─────────────────────────────────────────────────────────────────┘
```

### Example

**Bad**: Using axiom or admit
```lean
axiom foo : P        /- (by claude) FORBIDDEN -/
theorem bar : Q := by admit   /- (by claude) FORBIDDEN for agents -/
```

**Bad**: Leaving sorry because something depends on admit
```lean
/- Human wrote this with admit -/
theorem pinched_by_prisms : ∃ C, ... := by admit

/- (by claude) WRONG - don't skip proof just because it uses admit! -/
theorem dims_nonneg : 0 ≤ dims i := by
  have h : P.Nonempty := sorry  -- "since pinched_by_prisms has admit"
  ...
```

**Good**: Using sorry for stuck part
```lean
lemma foo : P := by
  have h1 : A := by simp  /- (by claude) proven -/
  have h2 : B := sorry    /- (by claude) only this step stuck -/
  exact combine h1 h2
```

**Good**: Using existing admit (human-designated) to complete proof
```lean
/- Human wrote this with admit - treat as proven -/
theorem pinched_by_prisms : ∃ C, ∀ K, ∃ dims, ... := by admit

/- (by claude) CORRECT - use pinched_by_prisms to prove completely -/
theorem dims_nonneg : 0 ≤ dims i := by
  have h := pinched_by_prisms  -- USE IT!
  obtain ⟨C, hC⟩ := h
  ... -- complete the proof using hC
```

---

## 2. Checklist Synchronization

**CHECKLIST.md is the SINGLE SOURCE OF TRUTH. Update it immediately after any progress.**

### Rules
```
┌─────────────────────────────────────────────────────────────────┐
│  UPDATE CHECKLIST.md IMMEDIATELY AFTER ANY PROGRESS.            │
│                                                                 │
│  Do NOT batch updates. Do NOT delay. Do NOT forget.             │
│                                                                 │
│  If out of sync, next session will have WRONG information.      │
└─────────────────────────────────────────────────────────────────┘
```

### Status Rules - CRITICAL

```
┌─────────────────────────────────────────────────────────────────┐
│  ✅ done = FULLY COMPLETED, NO REMAINING SORRY                  │
│                                                                 │
│  Only mark ✅ done when:                                        │
│  - ALL subtasks are [x] checked                                 │
│  - NO sorry remains in the proof                                │
│  - The proof compiles without errors                            │
│                                                                 │
│  ❌ WRONG:                                                      │
│    - "✅ done (with minor sorry)"                               │
│    - "✅ done (conditional)"                                    │
│    - "✅ done" with Progress: 5/6                               │
│                                                                 │
│  ✅ CORRECT:                                                    │
│    - Use 🔄 in_progress if any sorry remains                    │
│    - Use ❌ blocked if stuck and needs help                     │
│    - Only use ✅ done when 100% complete                        │
└─────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────┐
│  ❌ blocked requires AT LEAST 30 ATTEMPTS                       │
│                                                                 │
│  Do NOT mark a task as ❌ blocked until:                        │
│  - Attempts >= 30                                               │
│  - Multiple informal refine cycles have occurred                │
│                                                                 │
│  Before 30 attempts: keep status as 🔄 in_progress              │
│  and continue trying with fresh informal refinements.           │
│                                                                 │
│  Do NOT give up easily. Exhaust all strategies first.           │
└─────────────────────────────────────────────────────────────────┘
```

| Status | When to Use |
|--------|-------------|
| ✅ done | 100% complete, no sorry, all subtasks checked |
| 🔄 in_progress | Working on it, some progress made, sorry remains |
| ⬜ todo | Not started yet |
| ❌ blocked | Stuck after >= 30 attempts, needs help, cannot proceed |

### When to Update
- After completing/failing a lemma → update NOW
- Task status changes (todo → in_progress → done) → update NOW
- Attempt count increases → update NOW
- Before ending session → VERIFY CHECKLIST matches reality

### Timestamp Update Rule

```
┌─────────────────────────────────────────────────────────────────┐
│  ALWAYS update "Last updated" timestamp when modifying CHECKLIST │
│                                                                 │
│  Use bash command: date '+%Y-%m-%d %H:%M:%S'                    │
│                                                                 │
│  Example header:                                                │
│  > Auto-generated: 2026-02-19 14:30:45                          │
│  > Last updated: 2026-02-19 16:42:18                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Sorry Marking Format

**When working on a sorry, mark it in the original file.**

### Format
```lean
lemma foo : P := by
  sorry --doing in tmp_foo.lean
```

### Rules
1. Add `--doing in tmp_xxx.lean` comment right after the sorry
2. This indicates which tmp file is working on this lemma
3. Remove the comment after proof is complete and copied back

---

## 4. Temporary File Workflow

**Proof agents work in temporary files to avoid cluttering original code.**

### Protocol
1. **Mark sorry in original file**
   ```lean
   sorry --doing in tmp_foo.lean
   ```

2. **Create tmp file** in same directory as original
   ```bash
   # If original is <project>/SomeFile.lean
   # Create <project>/tmp_foo.lean
   ```

3. **Work in tmp file**
   - Import necessary modules
   - Copy lemma statement
   - Attempt proof
   - Iterate until proven or budget exhausted

4. **Copy back when proven**
   - Replace sorry in original with working proof
   - Remove the `--doing in tmp_xxx.lean` comment

5. **Clean up**
   - Delete tmp file after successful proof
   - Keep informal solution file for reference

### Example Tmp File
```lean
/- (by claude)
   File: <project>/tmp_targetLemma.lean
   Extracted from: <project>/SomeFile.lean
   Target: lemma targetLemma
-/

import <Project>.Basic

/- (by claude) Minimal environment needed -/

/- (by claude) Target lemma -/
lemma targetLemma ... := by
  sorry
```

### File Naming Rules (CRITICAL)

```
┌─────────────────────────────────────────────────────────────────┐
│  ONLY create files with these naming patterns:                   │
│                                                                 │
│  ✅ ALLOWED:                                                     │
│    - tmp_<lemma>.lean     (temporary proof attempts)             │
│    - informal_<lemma>.md  (informal solution / Gemini notes)     │
│                                                                 │
│  ❌ FORBIDDEN (do NOT create these):                             │
│    - INVESTIGATION_xxx.md                                        │
│    - ANALYSIS_xxx.md                                             │
│    - SUMMARY_xxx.md                                              │
│    - README_xxx.md                                               │
│    - Any other random documentation files                        │
│                                                                 │
│  All notes, analysis, investigation results go into:             │
│    - informal_<lemma>.md  (for proof-related insights)           │
│    - CHECKLIST.md Notes field (for status/blockers)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Task Location

**Use lemma/theorem names + structural position for locating tasks, NEVER line numbers.**

### Why
- Line numbers change when other parts of the file are modified
- Lemma names alone may be ambiguous (multiple sorries in one lemma)
- Structural descriptions are stable and precise

### Location Format

```
┌─────────────────────────────────────────────────────────────────┐
│  Format: <lemma_name>: <structural_position>                    │
│                                                                 │
│  ❌ BAD:                                                        │
│    - "line 24"                                                  │
│    - "sorry at line 98"                                         │
│    - "hδ₁ : δ ≤ 1"  (ambiguous without lemma context)           │
│                                                                 │
│  ✅ GOOD:                                                       │
│    - "dyadic_pigeonhole: have hb (first sorry)"                 │
│    - "nonempty_factorization: have hδ₁ : δ ≤ 1"                 │
│    - "exists_greedy_partition: induction base case"             │
│    - "exists_greedy_partition: induction step, ht subset"       │
│    - "fourpointone: final sorry after constructor"              │
│                                                                 │
│  For nested structures:                                         │
│    - "lemma foo: match case .inl: have h1"                      │
│    - "theorem bar: induction n: succ case: rcases h: left"      │
└─────────────────────────────────────────────────────────────────┘
```

### How to Locate in Code
```bash
# Search for the lemma in the file
grep -n "lemma targetLemma" <project>/SomeFile.lean
# Then read the lemma structure to find the specific sorry
```

---

## 6. Tool Priority Order

**Use tools in this specific order to maximize efficiency.**

### Tool Invocation (Local CLI Skills)

All tools are local CLI scripts under `skills/cli/`. Invoke them as:

```bash
python skills/cli/<tool>.py <args>
```

For exact parameters of any tool, read `skills/<skill>/SKILL.md` and the corresponding `reference-<tool>.md` in the same directory.

| Logical name | CLI invocation |
|---|---|
| `leanexplore` | `python skills/cli/leanexplore.py QUERY` |
| `loogle` | `python skills/cli/loogle.py` |
| `leanfinder` / `leansearch` | `python skills/cli/leanfinder.py` / `leansearch.py` |
| `state-search` | `python skills/cli/state_search.py` |
| `hammer-premise` | `python skills/cli/hammer_premise.py` |
| `lean-check` (compile + diagnostics) | `python skills/cli/lean_check.py <FILE>` |
| `discussion_partner` | `python skills/cli/discussion_partner.py` |
| `informal_prover` | `python skills/cli/informal_prover.py` |

Do NOT use `lake build` for per-file validation — always use `lean_check.py`.

### Search Tools (Library Lemmas)

**ALWAYS search in this order:**

```
1. leanexplore  (semantic search - natural language)
   ↓ (if not found)
2. loogle        (type pattern matching)
   ↓ (if not found)
3. leanfinder / leansearch  (alternative semantic search)
```

### Why This Order
- **leanexplore**: Understands natural language, finds lemmas by concept
  - Example: "factorial of zero equals one"
- **loogle**: Requires exact type patterns, more precise but harder
  - Example: `?f (?x + ?y) = ?f ?x + ?f ?y`
- **leanfinder / leansearch**: Alternative semantic search if leanexplore doesn't find it

### CRITICAL: Don't Give Up If Mathlib Doesn't Have It

```
┌─────────────────────────────────────────────────────────────────┐
│  "Mathlib doesn't have this lemma" is NOT an excuse to give up! │
│                                                                 │
│  If you searched and didn't find it:                            │
│  1. Build it yourself, step by step                             │
│  2. Break down into smaller intermediate lemmas                 │
│  3. Use have/suffices to construct the proof gradually          │
│  4. Create helper lemmas if needed                              │
│                                                                 │
│  Mathlib is a SHORTCUT, not a REQUIREMENT.                      │
│  You are capable of proving things from first principles.       │
└─────────────────────────────────────────────────────────────────┘
```

### Automation Tools (Tactics)

**First response to ANY goal or error:**

```
1. hint      (shows suggestions for successful tactics)
   ↓ (if hint doesn't help)
2. grind     (general automation for complex goals)
   ↓ (if automation fails)
3. Manual    (analyze and choose tactic manually)
```

### Standard Tactic Toolkit

| Tactic | Purpose | When to Use |
|--------|---------|-------------|
| `hint` | Discovery | Don't know what works |
| `grind` | General automation | Complex goals |
| `omega` | Linear arithmetic | ℕ/ℤ inequalities |
| `aesop` | Goal search | Structural proofs |
| `simp` | Simplification | Reduce complexity |
| `rfl` | Definitional equality | By definition |
| `ring` | Ring identities | Algebraic equality |

---

## 7. Error Response Protocol

**When compilation errors occur, follow this protocol:**

### Step 1: Try Automation FIRST
```lean
-- Error occurs
theorem foo : P := by
  hint   -- try hint first
  sorry  -- temporarily replace with sorry
```

If `hint` shows suggestions, use suggested tactic.

### Step 2: Try grind
```lean
theorem foo : P := by
  grind  -- general automation
```

### Step 3: Manual Analysis
Only if both hint and grind fail:
1. Read error message carefully
2. Inspect diagnostics with `python skills/cli/lean_check.py <file>` (shows goals, hypotheses, and errors)
3. Search for lemmas (leanexplore → loogle)
4. Choose appropriate tactic manually

---

## 8. Informal Solution Integration

**Each task has an associated informal solution file that evolves over time.**

### Informal Solution File Format
File: `informal_xxx.md`

```markdown
# Informal Solution: lemma_name

## Version: v3 (refined at attempt 8)

## Statement
[lemma statement in natural language]

## Proof Outline
1. First we show...
2. Then by...
3. Finally...

## Key Insights
- insight 1
- insight 2

## Relevant Mathlib Lemmas
- Lemma1
- Lemma2

## Previous Attempts Summary
- v1 (attempt 2): Tried direct simp, failed
- v2 (attempt 4): Found need for intermediate step
- v3 (attempt 8): Found key lemma Nat.xxx
```

### Trigger Rule

```
┌─────────────────────────────────────────────────────────────────┐
│  Call informal_agent at:                                         │
│                                                                 │
│  - attempts = 0  (INITIAL CREATION, before first proof attempt) │
│  - attempts = 2, 4, 8, 16, 32, ...  (refinement at powers of 2)│
│                                                                 │
│  Every new task MUST have an informal_xxx.md created BEFORE      │
│  any proof_agent is spawned. The coordinator handles this.       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Comments Guidelines (CRITICAL)

### Human Comments - DO NOT DELETE

```
┌─────────────────────────────────────────────────────────────────┐
│  Human comments are VALUABLE PROOF STRATEGY HINTS.               │
│  They use BOTH formats: `-- comment` AND `/- comment -/`         │
│                                                                 │
│  YOU MUST:                                                       │
│  - READ and UNDERSTAND all human comments near target lemma      │
│  - FOLLOW the proof strategy outlined in comments               │
│  - USE suggested theorems (marked with "-- Use :" or "-- Try :") │
│  - NEVER DELETE human comments (unless proof is 100% complete)   │
│                                                                 │
│  Human comments often contain crucial hints like:                │
│    -- base on the proof of Lemma 4.1 in [GWZ].                  │
│    -- use `Real.dyadic_pigeonhole₁` on ...                      │
│    -- use `one_le_maxDensity`                                   │
│    -- use `Partition.from_subset` if useful                     │
└─────────────────────────────────────────────────────────────────┘
```

### Your Comments - MUST BE DISTINGUISHABLE

**All comments written by Claude MUST use the block comment format with marker:**

### Format
```lean
/- (by claude) Your comment content here -/
```

### Rules
1. **Always use block comments with marker**: `/- (by claude) ... -/`
2. **Never use line comments**: `-- ...` (reserved for human comments, except `--doing in tmp_xxx.lean`)
3. **Never use unmarked block comments**: `/- comment -/` without "(by claude)" is indistinguishable from human
4. Keep comments minimal - max 1-2 per logical block
5. Detailed notes → informal solution file or CHECKLIST

### Correct vs Incorrect

| ✅ CORRECT | ❌ INCORRECT |
|------------|--------------|
| `/- (by claude) Using ring to simplify -/` | `-- Using ring here` (looks like human) |
| `/- (by claude) This follows from IH -/` | `/- Using ring to simplify -/` (no marker) |

### Example

**Bad**: Using line comments (looks like human comment)
```lean
lemma foo : P := by
  -- Alternative approach using alternating sequence
  -- This reduces to showing alternating is better
  unfold isAlternating at hna
  push_neg at hna
  use fun i => (-1 : ℤˣ) ^ (i.val + 1)
  sorry
```

**Good**: Using block comment format
```lean
lemma foo : P := by
  unfold isAlternating at hna
  push_neg at hna
  use fun i => (-1 : ℤˣ) ^ (i.val + 1)
  /- (by claude) Core: non-alternating has fewer valid perms -/
  sorry
```

**Also Good**: Multi-line block comment
```lean
/- (by claude)
   Key insight: We use the alternating sequence as witness.
   The proof reduces to showing alternating is strictly better.
-/
lemma foo : P := by
  ...
```

---

## 10. Do and Don't (Common Rules)

| ✅ DO | ❌ DON'T | Reason |
|-------|----------|--------|
| Use `sorry` for stuck parts | Use `axiom` or `admit` | `sorry` is visible; `axiom`/`admit` hide incompleteness |
| USE theorems that have `admit` | Leave sorry "because X has admit" | Treat existing `admit` as proven; your job is to complete YOUR proof |
| Read & follow human comments | Delete human comments | Human comments contain proof strategy hints |
| Use `/- (by claude) -/` comments | Use `-- comment` or unmarked `/- -/` | Distinguishes your comments from human's |
| Search `leanexplore` first | Search `loogle` first | leanexplore uses natural language, easier syntax |
| Try `hint` → `grind` first | Try manual tactics first | Automation often succeeds, saves time |
| Update CHECKLIST immediately | Batch updates or delay | State goes stale if not synced |
| Use structural position for tasks | Use line numbers | Line numbers change when code is modified |
| Work in tmp files | Edit original file directly | Keeps original clean; allows experimentation |
| Mark sorry with `--doing in tmp_xxx.lean` | Leave unmarked sorry | Tracks which tmp file is working on it |
| Mark `✅ done` only when 100% complete | Mark "✅ done (with minor sorry)" | `✅ done` means NO sorry remains |
| Update timestamp with `date '+%Y-%m-%d %H:%M:%S'` | Use approximate dates | Precise timestamps track exact progress |
| Prove everything except `admit` | Skip proof "because depends on admit" | `admit` is human's responsibility, not excuse to skip |
| Keep trying until >= 30 attempts before blocking | Mark ❌ blocked before 30 attempts | Premature blocking wastes potential; exhaust strategies first |

---

## Quick Reference

All agents must follow these rules:
1. ✅ Use `sorry`, never `axiom` or `admit`
2. ✅ USE theorems with `admit` - don't skip proof because of it
3. ✅ Read & follow human comments - NEVER delete them
4. ✅ Use `/- (by claude) ... -/` comment format (distinguishable from human)
5. ✅ Update CHECKLIST immediately after progress
6. ✅ Mark sorry with `--doing in tmp_xxx.lean`
7. ✅ Work in tmp files for proof attempts
8. ✅ Use lemma names to locate tasks (not line numbers)
9. ✅ Search: leanexplore → loogle → leanfinder/leansearch
10. ✅ Tactics: hint → grind → manual
11. ✅ Maintain informal solution files
12. ✅ Create informal at task start (attempt 0), refine at 2^n attempts
13. ✅ `✅ done` = 100% complete, NO sorry remaining
