# Skill Creator

A Claude Code skill for building, testing, and iterating on skills — with built-in knowledge accumulation inspired by [Karpathy's LLM Wiki](https://github.com/karpathy/llm-wiki) pattern.

## The Problem This Solves

Coding Agents (Claude Code, Cursor, Codex) have a memory problem. You ask an Agent to run a workflow, it produces useful insights, and then it forgets everything. Next time you run the same workflow, it starts from zero. RAG doesn't help — it re-derives knowledge on every query, nothing compounds.

Karpathy proposed a different architecture: instead of retrieving from raw documents at query time, have the LLM **incrementally build and maintain a persistent wiki**. Knowledge is compiled once and kept current, not re-derived on every query.

This project takes that idea further — applying it to a multi-skill Agent system where **knowledge compounds across independent workflows**, not just within a single domain.

## Core Architecture

Three layers, mapped from Karpathy's LLM Wiki to Claude Code Skills:

```
┌─────────────────────────────────────────────────────┐
│  Schema Layer — SKILL.md                            │
│  Defines how the LLM runs the skill + forces        │
│  archival as the final workflow step                 │
├─────────────────────────────────────────────────────┤
│  Wiki Layer — wiki.md                               │
│  LLM-compiled execution index + cross-run           │
│  pattern accumulation (never manually edited)        │
├─────────────────────────────────────────────────────┤
│  Raw Layer — raw/YYYY-MM-DD/                        │
│  Immutable per-execution archives                   │
│  (input.md + summary.md, append-only)               │
├─────────────────────────────────────────────────────┤
│  Graph Layer — meta.md + _discover.py  [NEW]        │
│  Declarative data dependencies → automatic          │
│  cross-skill knowledge graph + context injection    │
└─────────────────────────────────────────────────────┘
```

### What's Different From Karpathy's Original

| Karpathy LLM Wiki | This System |
|---|---|
| Single-domain wiki | Multi-skill, each with its own wiki |
| Manual ingest of documents | Automatic archival embedded in workflow |
| No cross-domain linking | `meta.md` declares data dependencies, `_discover.py` auto-computes relevance |
| Query-time wiki search | Pre-execution context injection of related skills' accumulated knowledge |

## The Key Innovation: Cross-Skill Knowledge Graph

Each skill declares what it produces and consumes in `meta.md`:

```yaml
skill: hv-analysis
topics: [深度研究, 竞品分析]
product_scope: [ProductA, ProductB]
data_produces: [PDF研究报告, 竞品对比]
data_consumes: [用户行为数据, query日志分析]
```

`_discover.py` scans all skills' metadata and computes a weighted relevance score:

- `topics` overlap × 2 (thematic similarity)
- `product_scope` overlap × 3 (same product line)
- `data_produces ∩ data_consumes` × 4 (data flow dependency — highest weight)

Before executing a skill, the system discovers related skills and loads their `wiki.md` into context. The LLM starts with cross-domain knowledge already available — not from scratch.

**Example:** Running a competitive analysis skill automatically pulls in accumulated user behavior patterns from a query analysis skill, because one produces data the other consumes. No manual configuration needed.

## How It Compares to Existing Solutions

After surveying 400+ related repos (LLM Wiki implementations, Agent memory systems, Claude Code skill frameworks):

- **LLM Wiki three-layer pattern** — well-implemented by atomicstrata/llm-wiki-compiler, SwarmVault, Pratiyush/llm-wiki
- **Agent persistent memory** — competitive space (Graphiti, Mem0, OpenLore, Mnemon, PAR)
- **Claude Code skill frameworks** — Brain-AI, MemStack, PFAA-Agents

**No existing project implements declarative cross-skill data dependency discovery.** All knowledge-sharing approaches either use a shared memory pool (passive query) or code-level static analysis. None compute "which workflows are related based on what they produce/consume" and inject relevant context before execution.

## Features

### Skill Lifecycle Management
- Create skills following a standardized spec (frontmatter with bilingual triggers, file manifest with Obsidian wiki-links, mandatory archival step)
- Iterative improvement loop: run evals → user reviews in HTML viewer → refine → repeat
- A/B blind testing between skill versions

### Knowledge Accumulation
- **Automatic archival**: every skill execution creates `raw/YYYY-MM-DD/` with input summary + core conclusions
- **LLM-compiled wiki**: after archival, the LLM updates `wiki.md` — maintaining an execution index and accumulating cross-run observations
- **Cross-skill discovery**: `_discover.py` computes relevance between skills based on declared metadata

### Description Optimization
- `scripts/run_eval.py` — test trigger accuracy via `claude -p` subprocess
- `scripts/improve_description.py` — LLM-powered description rewriting
- `scripts/run_loop.py` — automated eval+improve loop with train/test split (40% holdout)
- `scripts/generate_report.py` — HTML report with training/test score visualization

### Eval Viewer
- `eval-viewer/viewer.html` — keyboard-navigable single-page app, renders PDF/images/xlsx inline, cross-iteration comparison
- `eval-viewer/generate_review.py` — zero-dependency HTTP server, supports `--static` for offline use
- Feedback written to `feedback.json`, consumed by the iteration loop

## Directory Structure

```
skill-creator/
├── SKILL.md                  # Main skill file — complete workflow definition
├── meta.md                   # Dependency declarations for cross-skill discovery
├── wiki.md                   # Execution index (LLM-maintained)
├── agents/
│   ├── analyzer.md           # Sub-agent: analyze benchmark results
│   ├── comparator.md         # Sub-agent: blind A/B comparison
│   └── grader.md             # Sub-agent: grade assertions
├── assets/
│   └── eval_review.html      # Browser UI for editing eval cases
├── eval-viewer/
│   ├── generate_review.py    # Eval viewer HTTP server
│   └── viewer.html           # Eval viewer frontend
├── references/
│   └── schemas.md            # JSON schema definitions (evals, grading, benchmark)
└── scripts/
    ├── aggregate_benchmark.py
    ├── discover.py           # Cross-skill relevance computation
    ├── generate_report.py
    ├── improve_description.py
    ├── package_skill.py
    ├── quick_validate.py
    ├── run_eval.py
    ├── run_loop.py
    └── utils.py
```

## Quick Start

1. Copy this skill to `~/.claude/skills/skill-creator/`
2. Tell Claude Code: "创建一个新 skill" or "create a new skill"
3. The skill guides you through intent capture → drafting → eval → iteration → archival

### Adding Knowledge Accumulation to Any Skill

Minimal setup for any existing skill:

```bash
mkdir -p ~/.claude/skills/your-skill/raw
touch ~/.claude/skills/your-skill/wiki.md
```

Add to your SKILL.md's final step:
```markdown
## Final Step: Archive and compile wiki
1. Create `raw/YYYY-MM-DD/` with input.md + summary.md
2. Read and update wiki.md index
```

For cross-skill discovery, add `meta.md`:
```yaml
---
skill: your-skill
topics: [topic1, topic2]
product_scope: [Product]
data_produces: [what this skill outputs]
data_consumes: [what this skill needs]
---
```

Then run: `python3 ~/.claude/skills/_discover.py your-skill`

## Requirements

- Claude Code CLI (`claude` command available)
- `gh` CLI (for GitHub repo creation during skill packaging)
- Python 3.10+ (for eval scripts)
- Obsidian (optional, for wiki-link navigation and graph view)

## Credits

- Architecture inspired by [Karpathy's LLM Wiki](https://github.com/karpathy/llm-wiki) pattern
- Built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill system
