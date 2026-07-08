Carefully read the prompts under `prompts/autosearch_no_golf/subagent_prompts/` (common.md, coordinator.md, proof_agent.md, informal_agent.md).
Also read `skills/SKILL.md` and each sub-skill's `SKILL.md` (search, verification, llm, code-transform, sorrifier) so you know which local CLI tools are available and how to invoke them.

> **NO-GOLF MODE (HARD RULE).** This is a no-golf run. Do **NOT** spawn any golfer
> agent and do **NOT** perform any proof-golfing / simplification / redundancy-removal
> pass, regardless of proof size. If any subagent prompt mentions golfing, ignore that
> instruction. Once a lemma compiles with no `sorry`, mark it done and move on — never
> run a follow-up "simplify" or "golf" step on it.

You should act as coordinator agent to complete the target folder / file.

When you launch a subagent, you MUST:

1. **Describe the assigned task clearly** in the prompt
2. **Include the absolute path** to its corresponding prompt file and instruct it to read and follow that prompt
3. **Include the absolute path** to the reference resources (listed below) and instruct it to read them -- they are written by expert mathematicians and are critical for the proof
4. **Instruct the subagent** to update its own target entry in CHECKLIST.md after making any progress
5. Tell the subagent to make good use of the local CLI skills in `skills/cli/` — in particular `leanexplore.py` (semantic mathlib search, invoked as `python skills/cli/leanexplore.py QUERY`) and `discussion_partner.py` (ask Gemini / GPT for proof strategy hints). All verification must go through `lean_check.py` (never `lake build` for per-file checks).

After a subagent returns, you MUST update CHECKLIST.md to reflect the result.

You can spawn multiple subagents simultaneously to complete the tasks. (at most 2 subagent in parallel). But MAKE SURE each subagent is working on EXACTLY ONE task.

reference resources:

Read the environment variable `REFERENCE_RESOURCES` to get the absolute path(s) of the reference material. Run:

```bash
echo "$REFERENCE_RESOURCES"
```

(or in Python: `os.environ.get("REFERENCE_RESOURCES")`). The value may be a single path or a colon-separated list of paths. If the variable is empty/unset, proceed without external references.

You should give the resolved path(s) in the prompt to the subagent.

# END SIGNAL (MANDATORY)

The driver loop only stops when it detects an end-reason line in your output. If
you do not emit one, it will resend this prompt and re-run you until the maximum
round count is reached — even when the target is already fully proved. So you
**MUST** finish every session by deciding one of the following and emitting the
corresponding line:

* **COMPLETE**: `lean_check.py` on the target file/folder returns okay with zero
  `sorry`/`admit`/`axiom` and zero errors across all target declarations -> end with COMPLETE.
* **SELECTED_TARGET_COMPLETE**: You finished some targets and, for the remaining
  ones, either made meaningful partial progress (a compiling skeleton with
  structured `sorry` placeholders) or determined they need a fresh session. Run
  `lean_check.py` one final time to confirm the file still compiles, then end.
* **LIMIT**: You are stuck on all remaining targets, out of tokens, or the file
  has unrecoverable compilation errors -> end with LIMIT.

At the very end of your response, include exactly one line:

```
END_REASON:{reason}
```

where `{reason}` is `COMPLETE`, `SELECTED_TARGET_COMPLETE`, or `LIMIT`. Put it on
its own line, as the last line, with **no** other text, markdown, backticks, or
formatting around it.
