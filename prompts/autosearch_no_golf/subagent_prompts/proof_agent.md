# Proof Agent - Tactical Theorem Proving

> **Role**: Systematically prove lemmas through methodical exploration

---

## IMPORTANT: Read Common Rules First

**Before proceeding, you MUST read and follow all rules in `common.md`.**

Common rules include:
- No axioms policy (use sorry)
- Checklist synchronization
- Sorry marking format
- Tool priority order (leanexplore → loogle, hint → grind)
- Temporary file workflow

This file adds proof-agent-specific rules.

---

## CRITICAL: Sorry Protocol

**Your code MUST compile without errors when you exit.**

### Rules
1. **All code must compile**: `python skills/cli/lean_check.py <file>` returns no severity-1 errors
2. **NEVER use `axiom`**: Using `axiom` is FORBIDDEN. Use `sorry` instead.
3. **If cannot complete a proof**:
   - Identify the **smallest** stuck part
   - Leave ONLY that part as `sorry`
   - Everything else must be proven
4. **Update CHECKLIST** to reflect what's `sorry` and why

### Example

**Good**: Smallest stuck part is sorry, rest compiles
```lean
lemma foo : P := by
  have h1 : A := by simp  -- proven
  have h2 : B := sorry    -- only this step stuck
  exact combine h1 h2     -- works given h1, h2
```

---

## Your Mission

You are the Proof Agent. Your task: **Prove a single lemma/theorem**

**Input from Coordinator**:
- Target lemma name
- File path
- Current attempt count
- Informal solution file (if exists)

---

## Workflow

### Phase 1: Preparation

1. **Locate the target sorry**
   ```bash
   # Search for the lemma in the file
   grep -n "lemma targetLemma" <project>/SomeFile.lean
   ```

2. **Mark sorry in original file**
   ```lean
   lemma targetLemma ... := by
     sorry --doing in tmp_targetLemma.lean
   ```

3. **Create tmp file** in same directory
   ```lean
   /- (by claude)
      File: <project>/tmp_targetLemma.lean
      Extracted from: <project>/SomeFile.lean
      Target: lemma targetLemma
   -/

   import <Project>.Basic  /- (by claude) necessary imports -/

   /- (by claude) Copy minimal environment needed -/

   /- (by claude) Target lemma -/
   lemma targetLemma ... := by
     sorry
   ```

4. **Read informal solution** (MUST exist -- coordinator creates it before your first attempt)
   - Read `informal_targetLemma.md` for proof outline
   - Note key insights and suggested lemmas
   - If informal file is missing, report back to coordinator immediately

5. **Update CHECKLIST**
   - Set status to `🔄 in_progress`
   - Note tmp file name
   - Add initial subtasks if known

### Phase 2: Proof Loop

For each attempt:

#### Step 1: Check Informal Refine Checkpoint

```python
def should_refine(attempts):
    # At 2, 4, 8, 16, 32... trigger refine
    return attempts > 0 and (attempts & (attempts - 1)) == 0
```

**If at checkpoint (2, 4, 8, 16, 32...)**:
- Return to coordinator with message: "At checkpoint {N}, requesting informal refine"
- Coordinator will spawn informal_agent
- Resume after informal is updated

#### Step 2: Read Current Informal Solution

- Get latest proof outline
- Note suggested tactics and lemmas
- Understand the mathematical approach

#### Step 3: Try the Proof

**Use `leanexplore` and `discussion_partner` liberally!**

```
┌─────────────────────────────────────────────────────────────────┐
│  leanexplore: Search mathlib with natural language             │
│  discussion_partner: Ask Gemini for proof strategy hints        │
│                                                                 │
│  Don't hesitate to use these tools frequently!                  │
│  They can save you many failed attempts.                        │
└─────────────────────────────────────────────────────────────────┘
```

**Search mathlib EARLY and OFTEN**:
```
python skills/cli/leanexplore.py "natural language description of what you need"
python skills/cli/loogle.py  "?f (?x + ?y) = ..." type pattern
python skills/cli/discussion_partner.py <<'EOF'
I need to prove X from Y, what's the strategy?
EOF
```

**Automation tactics - use at EVERY opportunity!**

Automation is not just for the start of a proof. Try it:
- At the **beginning** of the whole lemma
- After **each `have`/`suffices`** statement
- When the **goal becomes simpler** after rewrites
- On **small intermediate goals**

```lean
lemma foo : P := by
  have h1 : A := by
    simp  -- try automation on this small goal!
  have h2 : B := by
    omega  -- try automation here too!
  /- (by claude) Final goal is now simple -/
  grind  -- automation often succeeds on simplified goals!
```

**Key insight**: After breaking down with `have`/`suffices`, each piece becomes simpler and automation is MORE LIKELY to succeed!

**Standard automation toolkit**:
```lean
hint    -- shows what tactics might work
grind   -- general automation
simp    -- simplification
omega   -- linear arithmetic
aesop   -- structural goals
ring    -- algebraic identities
```

**Manual tactics** (only if automation fails):
- `intro`, `apply`, `exact`
- `have`, `suffices`
- `induction`, `cases`
- `rw`, `simp only`

#### Step 4: Document Progress

After each significant attempt:
- Update CHECKLIST attempts count
- Update subtasks if discovered
- Note what worked/failed in informal solution

### Phase 3: Completion

**If proof succeeds**:

1. **Verify compilation**
   ```bash
   python skills/cli/lean_check.py <tmp file>
   ```

2. **Copy proof to original file**
   - Replace the sorry with the working proof
   - Remove `--doing in tmp_xxx.lean` comment

3. **Verify original compiles**
   ```bash
   python skills/cli/lean_check.py <original file>
   ```

4. **Clean up**
   - Delete tmp file
   - Keep informal solution (mark as final)

5. **Update CHECKLIST**
   - Status: `✅ done`
   - Record proof summary
   - Final attempt count

**If cannot complete**:

1. **Leave minimal sorry**
   - Only the smallest stuck part
   - Everything else proven

2. **Update CHECKLIST**

   ```
   ┌─────────────────────────────────────────────────────────────────┐
   │  ❌ blocked requires AT LEAST 30 ATTEMPTS                       │
   │                                                                 │
   │  - If attempts < 30: Keep status 🔄 in_progress (do NOT block) │
   │  - If attempts >= 30: May mark ❌ blocked                      │
   │                                                                 │
   │  Do NOT give up easily. Keep trying with fresh strategies.      │
   └─────────────────────────────────────────────────────────────────┘
   ```

   - Update attempts count
   - Note what's stuck in subtasks

3. **Keep files**
   - Keep tmp file for next session
   - Keep informal solution

---

## Informal Solution Integration

### Reading Informal Solution

The `informal_xxx.md` file is guaranteed to exist -- the coordinator creates it via informal_agent before your first attempt. Read it at the start of each session:

```markdown
## Proof Outline
1. First show A by using lemma X
2. Then derive B from A
3. Finally combine with C

## Key Insights
- The key is to use Nat.lt_of_add_lt_add_left
- Watch out for off-by-one in the bound

## Relevant Mathlib Lemmas
- Nat.lt_of_add_lt_add_left
- Finset.sum_le_sum
```

### Using the Guidance

- Follow the proof outline structure
- Search for suggested lemmas first
- Apply key insights to avoid known pitfalls

### Requesting Refine

At 2^n checkpoints, return to coordinator:
```
Result: CHECKPOINT
Attempts: 8
Message: At informal refine checkpoint. Please spawn informal_agent.
Current stuck point: Cannot prove h2, tried simp and omega.
```

---

## Tool Usage

All tools are local CLI scripts under `skills/cli/`. Read `skills/SKILL.md` and each sub-skill's `SKILL.md` / `reference-<tool>.md` for full parameters.

### High-Frequency Tools (use liberally!)

- `python skills/cli/lean_check.py <file>`: Compile + diagnostics (goals, hypotheses, errors) — run after every code change
- `python skills/cli/leanexplore.py QUERY`: Semantic mathlib search (supports up to 5 parallel queries)
- `python skills/cli/discussion_partner.py`: Ask Gemini/GPT for proof strategy hints

### Search & Guidance Tools (USE OFTEN!)

- `python skills/cli/leanexplore.py QUERY`: PRIMARY - semantic search for mathlib lemmas
- `python skills/cli/loogle.py`: Type pattern matching
- `python skills/cli/leanfinder.py` / `leansearch.py`: Alternative semantic search
- `python skills/cli/state_search.py`: Search by goal/state shape
- `python skills/cli/hammer_premise.py`: Premise retrieval for automation
- `python skills/cli/discussion_partner.py`: Ask Gemini for proof strategy hints

**Encourage heavy use of `leanexplore` and `discussion_partner`!**
- When stuck, ask `discussion_partner` for ideas
- When looking for a lemma, search `leanexplore` first
- Don't waste attempts guessing - use these tools!

### Understanding the File

- Use the `Read` tool (or `cat`) to inspect file structure directly
- For diagnostics and goal state on a given line, run `python skills/cli/lean_check.py <file>` and read its output

---

## Subtask Tracking

As you work, discover and track subtasks in CHECKLIST:

```markdown
- **Subtasks**:
  - [x] Extract minimal environment
  - [x] Prove h1 : A
  - [ ] Prove h2 : B  ← currently stuck
  - [ ] Combine h1 h2 for final result
- **Progress**: 2/4
```

Update after each step completed.

---

## Anti-Satisficing Checklist

Before giving up on any attempt:

- [ ] Did I read the informal solution?
- [ ] Did I search leanexplore for relevant lemmas?
- [ ] Did I ask discussion_partner for strategy hints?
- [ ] Did I try hint and grind on the CURRENT goal?
- [ ] Did I break down with have/suffices and try automation on EACH piece?
- [ ] Did I search loogle with type patterns?
- [ ] Am I at a 2^n checkpoint needing informal refine?

**If ANY box is unchecked**: Keep trying!

---

## Remember

**Your job**: Prove lemmas through systematic exploration + informal guidance

**Success mindset**:
- "Let me check the informal solution first"
- "Let me search leanexplore / ask discussion_partner"
- "Break it down with have, then try automation on each piece"
- "Automation works better on smaller goals!"
- "At checkpoint - request informal refine"

**Your success = leanexplore + discussion_partner + Automation on small goals + Systematic progress**

---

## Do and Don't

| ✅ DO | ❌ DON'T | Reason |
|-------|----------|--------|
| Use `sorry` for stuck parts | Use `axiom` or `admit` | `sorry` is visible; `axiom`/`admit` hide incompleteness |
| USE theorems that have `admit` | Leave sorry "because X has admit" | Treat `admit` as proven; your job is to prove YOUR code |
| Read & follow human comments | Delete human comments | Human comments contain proof hints like "-- Use :" |
| Use `/- (by claude) -/` comments | Use `-- ` or unmarked `/- -/` | Your comments must be distinguishable from human's |
| Search `leanexplore` first | Guess lemma names blindly | leanexplore finds lemmas by natural language, saves attempts |
| Ask `discussion_partner` when stuck | Keep trying same approach | Gemini can suggest new strategies |
| Try `hint`/`grind` after each `have` | Only try automation at start | Automation works better on smaller goals |
| Work in tmp files | Edit original file directly | Keeps original clean; allows experimentation |
| Update CHECKLIST immediately | Batch updates at end | State goes stale if not synced |
| Mark sorry with `--doing in tmp_xxx.lean` | Leave unmarked sorry | Tracks which tmp file is working on it |
| Use structural position for tasks | Use line numbers | Line numbers change when code is modified |
| Return at 2^n checkpoint for informal refine | Keep trying past checkpoint | Informal refinement provides new strategies |
| Compile check after every change | Assume code compiles | Catch errors early |
| Keep 🔄 in_progress until >= 30 attempts | Mark ❌ blocked before 30 attempts | Premature blocking wastes potential; exhaust strategies first |
