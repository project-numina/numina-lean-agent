# Numina-Lean-Agent

<div align="center">
  <a href="https://arxiv.org/abs/2601.14027"><b>Paper</b></a> |
  <a href="https://leandex.projectnumina.ai"><b>Leandex</b></a> |
  <a href="https://demo.projectnumina.ai/"><b>Demo</b></a> |
  <a href="https://github.com/project-numina/Numina-Putnam2025"><b>Putnam 2025</b></a>
</div>

<br>

An agent built on Claude Code for formal theorem proving tasks. We used this system to prove all 12 problems from Putnam 2025, and completed a paper-level formalization of [Effective Brascamp-Lieb inequalities](https://arxiv.org/abs/2511.11091).

## System Overview

<p align="center">
  <a href="assets/Numina-LeanAgent-v3.png">
    <img src="assets/Numina-LeanAgent-v3.png" alt="Numina-Lean-Agent system overview" width="900" />
  </a>
</p>


## Quick Start

### 1. Environment Setup

Run the following command to set up Lean, Claude Code, and the local CLI skills (code-transform, llm, search, sorrifier, verification):

```bash
git clone https://github.com/project-numina/numina-lean-agent
cd numina-lean-agent/tutorial
./setup.sh YOUR_PROJECT_NAME
```

Feel free to replace `YOUR_PROJECT_NAME` with any name you like (e.g. `myproofs`, `putnam2025`).


If you prefer a manual installation or encounter any issues with the automatic script, please refer to the **[Tutorial: Setup Guide](tutorial/setup.md)** for detailed step-by-step instructions.

Next, set up the Python environment:
```bash
cd ..
uv python install
uv sync
```


Before running any scripts, activate the Python environment:
```bash
source .venv/bin/activate
```

### 2. Run Our Agent

After following the setup instructions, your project will be located at `projects/YOUR_PROJECT_NAME`. Place your Lean code here and start experimenting!

> **Note:** The target `.lean` file or folder you pass to `run` / `batch` / `from-folder` must live **inside a Lean project** (an ancestor directory contains `lean-toolchain` and `lakefile.{lean,toml}`). The CLI skills walk up from the target to find the project root and invoke `lake env lean` there — a standalone `.lean` file outside any project will fail to compile.

#### Quick Examples

Before running the examples, you need to configure Claude Code. Choose one of the following options:

- **Option 1: Claude Account Login**  
  Run `Claude` in the terminal and follow the interactive login instructions.

- **Option 2: API Key Configuration**  
  Set the following environment variables with your API credentials:

```bash
export ANTHROPIC_BASE_URL=xxx      # Optional: custom API endpoint
export ANTHROPIC_AUTH_TOKEN=xxx    # Your API key
export ANTHROPIC_MODEL=xxx         # Model name (e.g., claude-opus-4-7)
```

#### Skill API Keys

The CLI skills under `skills/cli/` call external services and need their own credentials. These are **separate from Claude's auth above** — the agent will fail at the corresponding skill invocation if they are missing.

```bash
export GEMINI_API_KEY=xxx          # Required: discussion_partner, informal_prover (gemini), code_golf
export LEAN_LEANDEX_API_KEY=xxx    # Optional: Leandex semantic Mathlib search
                                   # (Leandex still works without an API key, but it limits the number of concurrent queries.)
export OPENAI_API_KEY=xxx          # Required only if you use informal_prover / discussion_partner with the gpt backend
export AXLE_API_KEY=xxx            # Optional: only needed for axle commands (verify-proof, disprove, sorry2lemma, ...)
```

Once configured, the quickest way to try it out is:

```bash
bash ./example_run.sh [target_folder]
```

Before running, open `example_run.sh` and set the two variables at the top:

| Variable | What it is | Example |
|---|---|---|
| `TARGET_FOLDER` | Path to the `.lean` file or folder you want the agent to work on. Overridden by the `[target_folder]` CLI argument. | `projects/myproofs/Foo.lean` |
| `REFERENCE_RESOURCES` | Colon-separated path(s) to reference documents (papers, notes, prior proofs) that the agent can read for context. **Optional — leave it empty or unset if you have no reference files.** | `references/my_paper.pdf` |

This runs `from-folder` with the autosearch coordinator prompt, a timestamped `--result-dir`, and `--max-rounds 10`. Edit the script to tweak defaults or switch between `run` / `batch` / `from-folder`.

> [!IMPORTANT]
> Feel free to point `[target_folder]` at any `.lean` file or directory of your choice. However, the target **must live inside a buildable Lean project**: an ancestor directory must contain a `lakefile.lean` or `lakefile.toml`, and the project must have been successfully built with `lake build`. Passing a standalone `.lean` file outside a Lake project will cause a `lake=fail` error.

Per-task outputs (including an isolated `cli.log`, `cli_stats.json`, per-round JSON, and the raw Claude stream) land under `results/<run_id>/<task_id>/`. See the [Usage Guide](tutorial/usage.md#output) for the full layout.

#### Detailed Docs
For comprehensive instructions on using our agent, check out:

**[Tutorial: Usage Guide](tutorial/usage.md)**

## Related Projects

- [lean4-skills](https://github.com/cameronfreer/lean4-skills) - Claude Code skills for Lean 4
- [Leandex](https://leandex.projectnumina.ai) - Semantic search for Lean codebases

## Citation
If you find the content of this project helpful, please cite our paper as follows:

```
@article{liu2026numina,
  title={Numina-Lean-Agent: An Open and General Agentic Reasoning System for Formal Mathematics},
  author={Junqi Liu and Zihao Zhou and Zekai Zhu and Marco Dos Santos and Weikun He and Jiawei Liu and Ran Wang and Yunzhou Xie and Junqiao Zhao and Qiufeng Wang and Lihong Zhi and Jia Li and Wenda Li},
  journal={arXiv preprint arXiv:2601.14027},
  year={2026}
}
```

## License

MIT License
