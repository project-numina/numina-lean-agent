# Lean Theorem Proving Documentation

> **Purpose**: Unified documentation for the Lean theorem proving system
> **Last Updated**: 2026-01-13

---

## Quick Navigation

| Section | Location | Purpose |
|---------|----------|---------|
| **Prompts** | `docs/prompts/` | Agent instructions (start here!) |
| **Agent Logs** | `docs/agent_logs/raw/` | Execution logs and learnings |
| **Technique** | `docs/technique/` | System design documentation |
| **Blueprint Template** | `/BLUEPRINT_TEMPLATE.md` | Template for new projects |

---

## Getting Started

### For Coordinator Agent

1. **Read common rules**: `docs/prompts/common.md`
2. **Read coordinator prompt**: `docs/prompts/coordinator.md`
3. **Read project blueprint**: `<project>/BLUEPRINT.md`
4. **Start orchestration**: Spawn appropriate subagents

### For Subagents

**All subagents must read**:
1. `docs/prompts/common.md` - Shared rules (no axioms, tool priority, etc.)
2. `docs/prompts/<agent_type>.md` - Agent-specific instructions

**Agent types**:
- `blueprint_agent.md` - Refine blueprint via Gemini
- `sketch_agent.md` - Formalize statements
- `proof_agent.md` - Prove lemmas

### For Humans

- **System overview**: `docs/technique/SYSTEM_DESIGN.md`
- **Workflow diagrams**: `docs/technique/WORKFLOW_DIAGRAM.md`
- **Quick start**: See "Quick Start Guide" below

---

## Directory Structure

```
/
├── docs/                                    # Active documentation (THIS DIRECTORY)
│   ├── prompts/
│   │   ├── common.md                        # Shared rules for all agents
│   │   ├── coordinator.md                   # Orchestration
│   │   ├── blueprint_agent.md               # Blueprint refinement via Gemini
│   │   ├── sketch_agent.md                  # Statement formalization
│   │   └── proof_agent.md                   # Lemma proving
│   │
│   ├── agent_logs/
│   │   ├── raw/                             # Individual agent execution logs
│   │   │   └── <agent>_<YYYYMMDD>_<HHMMSS>.md
│   │   └── README.md                        # Log format specification
│   │
│   ├── technique/
│   │   ├── SYSTEM_DESIGN.md                 # System architecture
│   │   └── WORKFLOW_DIAGRAM.md              # Visual workflows
│   │
│   └── README.md                            # This file
│
├── BLUEPRINT_TEMPLATE.md                    # Template for new projects
├── <project>/BLUEPRINT.md                   # Project-specific blueprint
└── docs_old/                                # Archived (reference only)
```

---

## Quick Start Guide

### Starting a New Session

1. **Read blueprint**:
   ```bash
   cat <project>/BLUEPRINT.md
   ```

2. **Understand state**:
   - What's ✅ done?
   - What's 🔄 partial? (resume that)
   - What's ❌ todo with satisfied dependencies?

3. **Select target**:
   - Choose TODO item where all dependencies (uses field) are done
   - Consider priority if multiple options

4. **Assess complexity**:
   - Simple (formalized, clear) → Proof Agent
   - Medium (needs formalization) → Sketch Agent → Proof Agent
   - Complex (unclear informal proof) → Blueprint Agent → Sketch → Proof

5. **Spawn appropriate subagent(s)**

### During Work

- **Update blueprint immediately** after any progress
- **Create agent logs** for every execution
- **Follow common rules** (no axioms, hint/grind first, leandex before proving)

### Ending a Session

- **Verify blueprint accuracy**
- **Update progress summary**
- **Note next eligible target**

---

## Core Principles

### 1. Common Rules (ALL agents must follow)

From `docs/prompts/common.md`:
- ✅ Use `sorry`, never `axiom`
- ✅ Update BLUEPRINT immediately after progress
- ✅ Tool priority: leandex → loogle, hint → grind → manual
- ✅ Work in tmp files (proof agent)
- ✅ Create agent logs for every execution
- ✅ Status comment format on all lemmas

### 2. Dependency-Topology Blueprint

From `BLUEPRINT_TEMPLATE.md`:
- ✅ Order by dependencies (dependencies before dependents)
- ✅ Use label/uses fields for tracking
- ✅ Detailed informal proofs for lemmas/theorems
- ✅ Blueprint agent splits complex lemmas
- ✅ Single source of truth

### 3. Agent Specialization

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| **Coordinator** | Orchestrate work | Always (top level) |
| **Blueprint Agent** | Refine blueprint via Gemini | Complex lemmas, unclear proofs, >40/50 attempts |
| **Sketch Agent** | Formalize statements | Need to translate informal → Lean |
| **Proof Agent** | Prove lemmas | Formalized lemmas ready for proof |

### 4. Tmp File Workflow

From `docs/prompts/proof_agent.md`:
1. Note tmp file in original status comment
2. Create `tmp/tmp_<lemma>.lean` in a `tmp/` subfolder alongside the original file
3. Work in tmp file (all attempts)
4. Copy back when proven
5. Delete tmp file

### 5. Agent Logs

From `docs/agent_logs/README.md`:
- **Format**: `<agent>_<YYYYMMDD>_<HHMMSS>.md`
- **Sections**: Meta, TODO List, Chronological Log, Summary, Learnings
- **Purpose**: Replace old experience/ and gemini/ sections
- **Benefit**: Unified, timestamped, searchable

---

## Prompt Organization

### Common Prompt (common.md)

**All agents must read this first.**

Contains shared rules:
- No axioms policy
- Blueprint synchronization
- Status comment format
- Tool priority order (leandex → loogle, hint → grind)
- Tmp file workflow
- Error response protocol
- Agent log recording
- NOT TO DO | WHY | HOW table

### Agent-Specific Prompts

Each agent has specialized instructions:

**coordinator.md**:
- Orchestration only (no direct work)
- Blueprint reading and target selection
- Complexity assessment (simple/medium/complex)
- Subagent spawning patterns

**blueprint_agent.md** (NEW):
- Call Gemini for detailed informal proofs
- Split complex lemmas (3+ steps → split)
- Update blueprint with sub-lemmas
- Manage dependencies

**sketch_agent.md** (REFACTORED):
- Formalize informal statements
- Add status comments
- Leave sorries (no proving)
- Update blueprint with file:line

**proof_agent.md** (REFACTORED):
- Work in tmp files (PRIMARY workflow)
- hint/grind FIRST (always)
- leandex BEFORE proving (search first)
- 5 method categories (20-50 attempts)
- Create agent logs

---

## Blueprint Format

### Structure

```markdown
# [type] [label]

## meta
- **label**: [label]
- **uses**: [[dep1], [dep2], ...]
- **file**: `path:line` or (to be created)
- **status**: done | partial | todo
- **attempts**: N / M (if applicable)

## statement
[Detailed informal statement]

## proof
[Detailed informal proof - for lemmas/theorems]
```

### Key Concepts

**Dependency topology**:
- Items ordered so dependencies come first
- Uses field tracks dependencies
- Dependency graph visualizes structure

**Splitting protocol**:
- Blueprint agent calls Gemini
- Creates sub-lemmas with detailed proofs
- Updates dependencies
- Reorders blueprint

**Status tracking**:
- done (✅): Completely proven
- partial (🔄): Work in progress
- todo (❌): Not started or budget exhausted

---

## Tool Priority Reference

### Search Tools (Use in Order)

1. **leandex** (FIRST) - Semantic search, natural language
   - "factorial of zero equals one"
   - "bijection preserves cardinality"

2. **loogle** (SECOND) - Type pattern matching
   - `?f (?x + ?y) = ?f ?x + ?f ?y`
   - `(-1 : ?R) ^ (?n + 1)`

3. **local_search** (THIRD) - Fast confirmation
   - "pow_succ"
   - "Finset.card"

### Automation Tools (Use in Order)

1. **hint** (FIRST) - Shows 🎉 for successful tactics
2. **grind** (SECOND) - General automation
3. **Manual analysis** (THIRD) - Only if both fail

---

## Migration Notes

**From old structure** (`docs_old/`) **to new**:

| Old | New | Notes |
|-----|-----|-------|
| experience/* | agent_logs/raw/ | Unified format |
| gemini/* | agent_logs/raw/ + blueprint agent | Embedded |
| Priority-based blueprint | Dependency-topology blueprint | BLUEPRINT_TEMPLATE.md |
| Separate prompts | common.md + specialized | Reduced duplication |

**See**: `docs_old/README.md` for full migration details

---

## Agent Log Format

**File naming**: `<agent>_<YYYYMMDD>_<HHMMSS>.md`

**Required sections**:
1. **Meta Information** - Agent type, timestamps, goal, target
2. **TODO List** - Task tracking (updated in place)
3. **Chronological Log** - Timestamped actions (append-only)
4. **Summary** - Result, attempts, key approach
5. **Learnings** - Extracted insights (numbered list)

**See**: `docs/agent_logs/README.md` for full specification and examples

---

## Troubleshooting

### Agent Not Following Common Rules?

Check that prompt includes:
```
Read docs/prompts/common.md for shared rules.
```

### Blueprint Out of Sync?

- Update immediately after any status change
- Don't batch updates
- Verify after each subagent completion

### Tmp Files Left Behind?

- Proof agent should delete after success
- Check status comment for tmp file path
- Manual cleanup: `rm -r <project>/tmp/`

### Dependencies Unclear?

- Check uses field in blueprint meta
- View dependency graph section
- Ensure all dependencies are done before starting

---

## Examples

### Example 1: Simple Lemma (Proof Agent Only)

```
Blueprint: [lem:foo] (status: todo, formalized, clear statement)
→ Coordinator spawns Proof Agent
→ Proof Agent:
  1. Creates tmp/tmp_foo.lean
  2. Tries hint/grind
  3. Searches leandex
  4. Proves in 14/20 attempts
  5. Copies to original
  6. Updates blueprint
  7. Creates agent log
→ Done! ✅
```

### Example 2: Medium Lemma (Sketch + Proof)

```
Blueprint: [lem:bar] (status: todo, NOT formalized)
→ Coordinator spawns Sketch Agent
→ Sketch Agent:
  1. Reads informal statement from blueprint
  2. Formalizes to Lean
  3. Adds status comment
  4. Updates blueprint with file:line
  5. Creates agent log
→ Coordinator spawns Proof Agent
→ Proof Agent proves it
→ Done! ✅
```

### Example 3: Complex Lemma (Blueprint + Sketch + Proof)

```
Blueprint: [lem:complex] (status: partial, 45/50 attempts exhausted)
→ Coordinator spawns Blueprint Agent
→ Blueprint Agent:
  1. Calls Gemini for detailed proof
  2. Gemini returns 3-step proof
  3. Splits into [lem:complex_step1], [lem:complex_step2], [lem:complex_step3]
  4. Updates blueprint with sub-lemmas
  5. Creates agent log
→ Coordinator spawns Sketch Agent for step1
→ Sketch Agent formalizes step1
→ Coordinator spawns Proof Agent for step1
→ Proof Agent proves step1 ✅
→ Repeat for step2, step3
→ Finally prove original [lem:complex] using step3
→ Done! ✅
```

---

## Summary

This documentation system provides:
- ✅ **Unified structure** (agent logs replace experience/gemini)
- ✅ **Common prompt base** (reduces duplication)
- ✅ **Dependency-topology blueprints** (clearer ordering)
- ✅ **Specialized agents** (blueprint agent for Gemini integration)
- ✅ **Tmp file workflow** (keeps code clean)
- ✅ **Tool priorities** (leandex → loogle, hint → grind)

**Start here**: `docs/prompts/common.md`
**Then read**: Agent-specific prompt for your role
**Reference**: This README for navigation and examples

Happy theorem proving!
