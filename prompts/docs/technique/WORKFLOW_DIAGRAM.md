# System Workflow Diagram

> Visual representation of the Lean theorem proving system

---

## Critical Rules (Summary)

| Rule | Enforcement |
|------|-------------|
| **Subagent Mandatory** | Coordinator NEVER does proof work directly |
| **Sorry Protocol** | Code must compile; sorry only smallest stuck part |
| **No Axiom** | NEVER use `axiom`, ALWAYS use `sorry` |
| **Blueprint Sync** | Update BLUEPRINT immediately after any progress |
| **Gemini First** | Proof agent MUST consult Gemini at checkpoint 0 before any code |

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     SESSION START                                │
│                                                                  │
│  1. Read BLUEPRINT.md (single source of truth)                  │
│  2. Find target: partial (resume) or todo (new)                 │
│  3. Check dependencies satisfied (uses field)                   │
│  4. Assess complexity → choose subagent flow                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Assess Complexity    │
                │                       │
                │  Simple: Formalized   │
                │  Medium: Not formal   │
                │  Complex: >40 attempts│
                │          or unclear   │
                └───────┬───────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
         ▼              ▼              ▼
┌────────────┐  ┌────────────┐  ┌────────────────┐
│   SIMPLE   │  │   MEDIUM   │  │    COMPLEX     │
│            │  │            │  │                │
│  Proof     │  │  Sketch    │  │  Blueprint     │
│  Agent     │  │  Agent     │  │  Agent         │
│  only      │  │  → Proof   │  │  → Sketch      │
│            │  │    Agent   │  │  → Proof       │
└────────────┘  └────────────┘  └────────────────┘
```

---

## Agent Orchestration Patterns

```
Pattern A: Simple (already formalized)
┌────────────────────────────────────────────────────────┐
│  Coordinator                                            │
│       │                                                 │
│       │  spawn via Task tool                           │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Proof Agent                                     │   │
│  │  • Work in tmp file                              │   │
│  │  • Gemini at checkpoint 0,2,4,8,16,32            │   │
│  │  • Try all 5 categories                          │   │
│  │  • 20-50 attempts                                │   │
│  │  • Return: SUCCESS | PARTIAL | BUDGET_EXHAUSTED  │   │
│  └─────────────────────────────────────────────────┘   │
│       │                                                 │
│       ▼                                                 │
│  Update BLUEPRINT immediately                           │
└────────────────────────────────────────────────────────┘


Pattern B: Medium (needs formalization)
┌────────────────────────────────────────────────────────┐
│  Coordinator                                            │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Sketch Agent                                    │   │
│  │  • Read blueprint informal statement             │   │
│  │  • Verify informal proof is detailed             │   │
│  │  • Call Gemini if proof has gaps                 │   │
│  │  • Formalize statement → Lean code               │   │
│  │  • Add status comment, leave sorry               │   │
│  │  • Update BLUEPRINT with file:line               │   │
│  │  • Return: SUCCESS | NEEDS_SPLITTING             │   │
│  └─────────────────────────────────────────────────┘   │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Proof Agent (same as Pattern A)                 │   │
│  └─────────────────────────────────────────────────┘   │
│       │                                                 │
│       ▼                                                 │
│  Update BLUEPRINT immediately                           │
└────────────────────────────────────────────────────────┘


Pattern C: Complex (needs decomposition)
┌────────────────────────────────────────────────────────┐
│  Coordinator                                            │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Blueprint Agent                                 │   │
│  │  • Analyze lemma complexity                      │   │
│  │  • Call Gemini for detailed informal proof       │   │
│  │  • Decide: 3+ steps → SPLIT                      │   │
│  │  • Create sub-lemmas with dependencies           │   │
│  │  • Update BLUEPRINT with topology                │   │
│  │  • Return: SPLIT | REFINED                       │   │
│  └─────────────────────────────────────────────────┘   │
│       │                                                 │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  For each sub-lemma (in dependency order):       │   │
│  │    Sketch Agent → Proof Agent                    │   │
│  └─────────────────────────────────────────────────┘   │
│       │                                                 │
│       ▼                                                 │
│  Update BLUEPRINT immediately                           │
└────────────────────────────────────────────────────────┘
```

---

## Proof Agent: Detailed Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                      PROOF AGENT WORKFLOW                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 0: Note tmp file in original (FIRST!)               │   │
│  │                                                            │   │
│  │  /- (by claude)                                            │   │
│  │  State: todo                                               │   │
│  │  Priority: 1                                               │   │
│  │  Attempts: 0 / 20                                          │   │
│  │  tmp file: path/tmp/tmp_lemma.lean  ← ADD THIS FIRST!       │   │
│  │  -/                                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 1: Create tmp file                                  │   │
│  │                                                            │   │
│  │  -- File: path/tmp/tmp_lemma.lean                           │   │
│  │  import OriginalFile                                       │   │
│  │  lemma name : statement := by                              │   │
│  │    sorry                                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 2: Gemini Checkpoint 0 (MANDATORY before any code)  │   │
│  │                                                            │   │
│  │  Call: discussion_partner or gemini_informal_prover        │   │
│  │  Ask for: proof strategy, key insights, mathlib lemmas     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STEP 3: Attempt Loop (1 to budget)                       │   │
│  │                                                            │   │
│  │  For each attempt:                                         │   │
│  │  • Display: **Attempt N/budget**                           │   │
│  │  • Check Gemini checkpoint (2,4,8,16,32)                   │   │
│  │  • Choose from 5 categories based on deficiency            │   │
│  │  • Try approach, use lean_multi_attempt                    │   │
│  │  • Document result                                         │   │
│  │                                                            │   │
│  │  Every 10 attempts:                                        │   │
│  │  • Update state comment in original                        │   │
│  │  • Update BLUEPRINT                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│               ┌────────────┴────────────┐                        │
│               │ Result?                 │                        │
│               └────────────┬────────────┘                        │
│                            │                                     │
│       ┌────────────────────┼────────────────────┐                │
│       │ SUCCESS            │ BUDGET_EXHAUSTED   │                │
│       ▼                    ▼                    │                │
│  ┌──────────┐        ┌──────────────────┐       │                │
│  │ Copy back│        │ Verify:           │       │                │
│  │ to orig  │        │ • All categories │       │                │
│  │ Delete   │        │   tried (≥5 each)│       │                │
│  │ tmp file │        │ • Budget reached │       │                │
│  │ State:   │        │                  │       │                │
│  │ done     │        │ Mark as HARD     │       │                │
│  └──────────┘        └──────────────────┘       │                │
│                                                  │                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Five Method Categories

```
┌─────────────────────────────────────────────────────────────────┐
│  CATEGORY 1: LIBRARY SEARCH (10 attempts minimum)                │
│                                                                  │
│  Tools (in order):                                               │
│  1. lean_leandex  (semantic search - natural language)           │
│  2. lean_loogle   (type pattern matching)                        │
│  3. lean_local_search (fast confirmation)                        │
│                                                                  │
│  Pattern:                                                        │
│  • Attempts 1-4: leandex with different phrasings                │
│  • Attempts 5-6: leandex focusing on operation names             │
│  • Attempts 7-8: loogle with type patterns                       │
│  • Attempts 9-10: Re-search with Gemini hints                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CATEGORY 2: DIRECT TACTICS (10 attempts minimum)                │
│                                                                  │
│  ALWAYS try hint → grind FIRST!                                  │
│                                                                  │
│  Group A: Arithmetic    → omega, linarith, ring                  │
│  Group B: Automation    → grind, aesop, hint, norm_num           │
│  Group C: Simplification → simp, simp_rw, norm_cast              │
│                                                                  │
│  Use lean_multi_attempt for parallel testing                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CATEGORY 3: STRUCTURAL APPROACHES (10 attempts minimum)         │
│                                                                  │
│  Approach A: Induction (different variables, strong induction)   │
│  Approach B: Case Splits (by_cases, rcases, obtain, match)       │
│  Approach C: Contradiction (by_contra, contrapose, push_neg)     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CATEGORY 4: TERM MODE (10 attempts minimum)                     │
│                                                                  │
│  exact fun x => [term]                                           │
│  exact ⟨witness, proof⟩  (for exists)                            │
│  exact lemma arg1 arg2   (direct application)                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CATEGORY 5: DECOMPOSITION (10 attempts minimum)                 │
│                                                                  │
│  Approach A: have h : [claim] := by [proof]                      │
│  Approach B: suffices [stronger] by [derive]                     │
│  Approach C: Extract helper lemma                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Gemini Checkpoint System

```
┌─────────────────────────────────────────────────────────────────┐
│                    MANDATORY GEMINI CHECKPOINTS                  │
│                                                                  │
│  Checkpoint 0:  BEFORE ANY CODE                                  │
│                 → Initial strategy, key insights, mathlib hints  │
│                                                                  │
│  Checkpoint 2:  After 2 attempts                                 │
│                 → Early guidance, hints                          │
│                                                                  │
│  Checkpoint 4:  After 4 attempts                                 │
│                 → Alternative approaches                         │
│                                                                  │
│  Checkpoint 8:  After 8 attempts                                 │
│                 → Decomposition ideas (sub-lemmas?)              │
│                                                                  │
│  Checkpoint 16: After 16 attempts                                │
│                 → Library search help, mathlib module hints      │
│                                                                  │
│  Checkpoint 32: After 32 attempts                                │
│                 → Optimization, simplification via code_golf     │
│                                                                  │
│  These are MANDATORY. You MUST consult Gemini at each checkpoint.│
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
BLUEPRINT.md ────────┐
  ↑                  │
  │ updates          │ reads
  │                  ▼
  │            Coordinator ────→ selects target (dependency order)
  │                  │
  │                  │ spawns via Task tool
  │                  ▼
  │         ┌─────────────────┐
  │         │  Blueprint Agent│  (if complex/stuck)
  │         │  • Gemini call  │
  │         │  • Split lemmas │
  │         └────────┬────────┘
  │                  │
  │                  ▼
  │         ┌─────────────────┐
  │         │  Sketch Agent   │  (if needs formalization)
  │         │  • Informal→Lean│
  │         │  • Status comment│
  │         │  • Verify compile│
  │         └────────┬────────┘
  │                  │
  │                  ▼
  │         ┌─────────────────┐
  │         │  Proof Agent    │
  │         │  • tmp file     │
  │         │  • Gemini calls │
  │         │  • 5 categories │
  │         │  • 20-50 attempts│
  │         └────────┬────────┘
  │                  │
  │                  │ updates immediately
  └──────────────────┘

Files Updated:
• BLUEPRINT.md (status, attempts, file:line)
• <target>.lean (proof code, status comment)
• docs/agent_logs/raw/<agent>_<timestamp>.md (agent logs)
```

---

## State Transitions

```
Lemma State Machine:

   todo
      │
      │ (Sketch Agent formalizes OR Proof Agent starts)
      ▼
   partial ──────────┐
      │              │
      │ (success)    │ (budget exhausted)
      │              │
      ▼              ▼
   done          todo | HARD
                     │
                     │ (Blueprint Agent refines/splits)
                     ▼
                  [back to queue with sub-lemmas]
```

**Status meanings**:
- `todo`: Ready to work on
- `partial`: Work in progress (has attempt count)
- `done`: Successfully proven
- `todo | HARD`: Budget exhausted, needs splitting/refinement

---

## Status Comment Format

```lean
/- (by claude)
State: todo | partial | done
Priority: 1-5
Attempts: N / M
tmp file: <path_or_empty>
-/
lemma name : statement := by
  ...
```

---

## Blueprint Entry Format

```markdown
# [type] [label]

## meta
- **label**: [label]
- **uses**: [[dep1], [dep2], ...]
- **file**: `path:line` or (to be created)
- **status**: done | partial | todo
- **attempts**: N / M (if applicable)

## statement
[Informal statement]

## proof
[Informal proof - detailed for lemmas/theorems]
```

---

## Temporary File Protocol

```
┌─────────────────────────────────────────────────────────────────┐
│  ORDER MATTERS:                                                  │
│                                                                  │
│  1. FIRST: Edit original file to add tmp file path in comment   │
│  2. THEN:  Create the tmp file in tmp/ subfolder                │
│  3. Work in tmp file (all attempts)                             │
│  4. On success: Copy proof back to original                     │
│  5. Delete tmp file                                             │
│  6. Remove tmp file note from status comment                    │
│                                                                  │
│  WHY: If you create tmp file first and forget to update the     │
│       original, other agents won't know work is in progress.    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tool Priority Order

```
SEARCH TOOLS (Library Lemmas):
  1. leandex      (semantic search - natural language)
     ↓ (if not found)
  2. loogle       (type pattern matching)
     ↓ (if not found)
  3. local_search (fast confirmation in current project)

AUTOMATION TOOLS (Tactics):
  1. hint         (shows successful tactics)
     ↓ (if hint doesn't help)
  2. grind        (general automation)
     ↓ (if automation fails)
  3. Manual       (analyze and choose tactic)

VERIFICATION:
  • lean_diagnostic_messages (NOT lake build)
```

---

## Anti-Satisficing Checklist

Before giving up, verify ALL boxes checked:

```
[ ] Consulted Gemini at checkpoint 0 (BEFORE any code)
[ ] Reached attempt budget (N >= budget)
[ ] Tried all required categories (each ≥5 attempts)
[ ] Consulted Gemini at ALL checkpoints (2, 4, 8, 16, 32)
[ ] Searched mathlib thoroughly (leandex, loogle)
[ ] Tried hint and grind on every goal
[ ] Tried both tactic mode and term mode
[ ] Tried decomposing into helper lemmas
[ ] Analyzed error messages carefully
[ ] No method category under-explored
[ ] Asked Gemini before enumeration/decide

If ANY box unchecked → KEEP TRYING!
```

---

## Session End Protocol

```
┌─────────────────────────────────────────────────────────────────┐
│                       SESSION END                                │
│                                                                  │
│  1. Verify BLUEPRINT matches reality                            │
│     • All status updates applied                                │
│     • All file:line references correct                          │
│     • All attempt counts current                                │
│                                                                  │
│  2. Verify code compiles                                        │
│     • Run lean_diagnostic_messages                              │
│     • Any error → fix or sorry smallest part                    │
│                                                                  │
│  3. Clean up tmp files                                          │
│     • Delete if proven                                          │
│     • Keep if returning later                                   │
│                                                                  │
│  4. Create agent logs                                           │
│     • docs/agent_logs/raw/<agent>_<timestamp>.md                │
│                                                                  │
│  5. Report to Coordinator                                       │
│     • SUCCESS | PARTIAL | BUDGET_EXHAUSTED                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary: Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Coordinator = orchestration only** | All work via Task tool subagents |
| **Gemini = strategic guidance** | Mandatory checkpoints at 0,2,4,8,16,32 |
| **BLUEPRINT = single source of truth** | Update immediately after any progress |
| **5 categories = thorough exploration** | Each needs ≥5 attempts before exit |
| **Sorry = minimal gaps** | Code always compiles, sorry only smallest stuck part |
| **No axiom** | NEVER use axiom, ALWAYS use sorry |
| **Tmp files = clean iteration** | Work in tmp, copy back on success |
| **Agent logs = learning capture** | Every execution creates a log |

---

**Read specific agent docs for detailed instructions:**
- `docs/prompts/coordinator.md` - Orchestration workflow
- `docs/prompts/proof_agent.md` - Proving methodology
- `docs/prompts/sketch_agent.md` - Formalization process
- `docs/prompts/blueprint_agent.md` - Splitting/refinement
- `docs/prompts/common.md` - Shared rules for all agents
