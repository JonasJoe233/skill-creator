# skill-creator

*[中文说明](README.zh-CN.md)*

**A workbench for building agent skills that get better every time they run.**

Most agent setups treat each run as disposable. The agent does the work, you correct it,
the correction lives in a chat log nobody reads again, and three weeks later you correct
the same thing. This repo is my answer to that: a four-layer loop where raw execution
traces are archived, distilled into a persistent knowledge base, compiled back into the
executable skill, and gated by evaluation before anything ships.

The mechanism has been running in this repo since `2026-06-08` —
`git log --reverse` is the receipt. In August 2026, Google Research published
[WikiSkill](https://arxiv.org/abs/2608.27454), which formalises a very similar
separation. The [comparison section](#how-this-relates-to-wikiskill-google-research-2026)
below maps the two layer by layer, including the one place they meaningfully differ.

---

## Install

This repo is both a Claude Code plugin and its own marketplace. From inside Claude Code:

```
/plugin marketplace add JonasJoe233/skill-creator
/plugin install skill-creator@skill-creator-marketplace
```

Once installed, the `skill-creator` skill is available and the (optional) sync
hooks are registered. The sync layer is **off by default** — see
[The sync layer](#the-sync-layer-optional-off-by-default) to turn it on.

---

## The problem it solves

Three failure modes, all of which I hit before building this:

1. **Lessons evaporate.** A skill run discovers something non-obvious — an API quirk, a
   threshold that actually works, a prompt phrasing that stops the model hedging. Without
   somewhere to put it, that finding dies with the session.
2. **Instructions rot upward.** Every lesson gets appended to the skill file until it is
   900 lines of accumulated scar tissue, and the model stops reading the parts that matter.
3. **No idea if a change helped.** You rewrite a skill, it feels better, and you have no
   evidence. The next rewrite undoes the last one.

The four layers exist to separate concerns that get conflated when you only have one file.

---

## The four layers

```
skill-name/
├── raw/                    # Layer 1 — append-only execution archive
│   └── YYYY-MM-DD_topic/
│       ├── input.md        #   what was asked
│       ├── summary.md      #   3–5 findings from this run
│       └── <outputs>       #   copies of what was produced
├── wiki.md                 # Layer 2 — distilled knowledge, LLM-maintained, never hand-edited
├── SKILL.md                # Layer 3 — the executable skill the agent actually loads
└── <workspace>/            # Layer 4 — eval runs, benchmarks, A/B comparisons
    └── iteration-N/
        └── eval-<name>/
            ├── with_skill/ | old_skill/
            └── without_skill/
```

| Layer | Write policy | Who maintains it | Why it is separate |
|---|---|---|---|
| `raw/` | append-only, never edited | the run itself | evidence must stay immutable or you cannot audit a regression |
| `wiki.md` | rewritten as understanding improves | the model, across runs | knowledge needs to be *consolidated*, which means overwriting — the opposite policy from evidence |
| `SKILL.md` | edited deliberately, kept under ~500 lines | me, with the model drafting | the executable layer is a budget, not a landfill |
| eval gate | per-iteration, disposable | subagents + a human reading the diff | a change without a comparison is a guess |

The load order matters as much as the layers. `SKILL.md` metadata is always in context
(~100 words), the skill body loads on trigger, and bundled resources load only when the
workflow reaches them. `raw/` is never loaded into context at all — it is there for the
model to *consult* when compiling the wiki, not to carry around.

---

## How this relates to WikiSkill (Google Research, 2026)

[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://arxiv.org/abs/2608.27454)
(Tang, Rashtchian, Ferng, Tomkins, Juan, Vu — Google Research, August 2026) argues that
skill evolution works better when raw experience, accumulated knowledge, and executable
skills are kept apart, and that the persistent wiki is the component doing the heavy
lifting — their ablations show removing it degrades results.

That is the same bet this repo makes, arrived at independently from the practical
direction: I was trying to stop re-teaching the same lessons, not to beat a benchmark.

| WikiSkill | this repo | match |
|---|---|---|
| raw execution experience | `raw/YYYY-MM-DD_topic/` archives | direct |
| persistent knowledge base (wiki) | `wiki.md`, model-maintained, cross-run index + accumulated observations | direct |
| executable skills | `SKILL.md` + `scripts/` + `references/` | direct |
| continuous consolidation of experience into the wiki | archiving is the mandatory last step of every skill's workflow | direct |
| skill update gated by validation-set score | skill update gated by eval assertions **plus my judgement** | **differs** |

**The honest difference:** WikiSkill closes the loop automatically — a validation score
decides whether an updated skill replaces the incumbent. My gate has a person in it. That
is not because automation is unnecessary; it is because my per-skill sample size is single
digits and I have no labelled validation set, so an automated score would be noise
dressed as evidence. So this is the front half of self-evolution running in production,
with the back half deliberately left manual until the data supports closing it.

The other difference worth naming: the paper optimises skills for benchmark tasks with
checkable answers. Most of my skills produce documents, spreadsheets and diagrams where
"correct" is partly taste. The eval harness here therefore measures the objective parts
(structure, formula errors, template fidelity, trigger accuracy) and routes the rest to a
side-by-side viewer for a human read, rather than pretending a grader can score prose.

---

## The loop

1. **Capture intent.** Usually the workflow already happened in the conversation — extract
   the tools used, the step order, and every place the user corrected the agent, then
   confirm the gaps rather than inventing them.
2. **Draft the skill** against a fixed house spec: frontmatter with bilingual trigger
   words and an explicit split between *act immediately* and *confirm first*; a file-index
   table as the first section; the archive step wired into the workflow's last step.
3. **Run evals in parallel.** For each test case, one subagent with the skill and one
   without (or against a snapshot of the previous version), launched in the same turn so
   they finish together. Assertions get drafted while the runs are in flight.
4. **Grade, aggregate, and show the diff** in a local viewer. Objective assertions get
   scored by a grader subagent; an analyst pass looks for patterns the aggregate hides.
5. **Improve by generalising from feedback** — not by patching the specific test case.
   `ALWAYS` and `NEVER` in a skill file are treated as a yellow flag, usually meaning the
   underlying reason wasn't explained.
6. **Archive and compile.** `raw/` gets this run's input and findings; `wiki.md` gets
   rewritten to absorb them. This is mandatory, not a nice-to-have — it is the step that
   makes the next run start smarter.
7. **Optimise the description** last, since the description is the only thing deciding
   whether the skill triggers at all: 20 should-trigger / should-not-trigger queries, then
   an optimisation loop against the same model that will run in production.

## Quick start

```bash
# the helper scripts live with the skill
cd skills/skill-creator

# structural sanity check on a skill
python -m scripts.quick_validate <path/to/skill>

# see how related skills overlap by topic (defaults to ~/.claude/skills)
python3 scripts/discover.py <skill-name> --skills-dir ~/.claude/skills

# aggregate one eval iteration into a benchmark
python -m scripts.aggregate_benchmark <workspace>/iteration-1 --skill-name <name>

# open the review viewer for that iteration
python eval-viewer/generate_review.py <workspace>/iteration-1 \
  --skill-name <name> --benchmark <workspace>/iteration-1/benchmark.json
```

Requires Python 3.10+ and the `claude` CLI for the description-optimisation loop. Subagents
are needed for the parallel eval step; without them the loop degrades gracefully to
sequential runs with no baseline.

## Layout

```
skill-creator/                       # the repo = plugin + its own marketplace
├── .claude-plugin/
│   ├── plugin.json                  # manifest + userConfig (sync options)
│   └── marketplace.json             # makes this repo installable as a marketplace
├── skills/
│   └── skill-creator/               # the skill itself
│       ├── SKILL.md                 # the spec every skill in the system is held to
│       ├── meta.md                  # topic/data declarations for cross-skill discovery
│       ├── wiki.md                  # accumulated lessons (starter template)
│       ├── agents/                  # grader / comparator / analyzer subagent prompts
│       ├── scripts/                 # quick_validate, discover, run_eval, run_loop, ...
│       ├── references/schemas.md    # evals.json / grading.json contracts
│       └── eval-viewer/             # local HTML review UI
├── hooks/hooks.json                 # registers the (opt-in) sync hooks
└── scripts/                         # the sync layer (off by default)
    ├── _synclib.py                  # shared config/git/credential helpers
    ├── skill-autopush.py            # PostToolUse: commit+push edited skills
    ├── skill-sweep.py               # SessionStart worker: archive raw/ catch-up
    └── skill-sweep-launch.py        # SessionStart entry: surface + detach worker
```

## The sync layer (optional, off by default)

Layer 1 (`raw/`) is only durable if it actually leaves your laptop. The plugin
ships a small automation layer that commits skill changes to git and pushes them
for you — closing the gap where a run archives a finding locally and it never
reaches a remote.

Two hooks, both **disabled until you opt in**:

- **PostToolUse (`Write|Edit`)** — when you edit a file under your skills dir,
  commit it in the nearest git repo and push if that branch has an upstream.
- **SessionStart** — a fast, detached sweep that catches files a skill produced
  via scripts (which never trigger the edit hook). Conservative rule: it only
  auto-commits changes under a skill's `raw/` dir; anything else is reported, not
  touched.

Enable and configure it in `/plugin` → this plugin → config, or via the
`userConfig` fields in the manifest:

| Option | Default | Meaning |
|---|---|---|
| `syncEnabled` | `false` | Master switch. Off = hooks self-exit, zero side effects. |
| `skillsDir` | `~/.claude/skills` | The only directory the sync layer ever touches. |
| `proxy` | `""` | Optional HTTP(S) proxy for git network ops. |
| `keychainItem` | `""` | macOS Keychain item to read `GH_TOKEN` from, if not already in the environment. |

**Git layout is auto-detected** — no strategy flag. If `skillsDir` itself is a
git repo, everything lives in one repo; if each skill subdirectory is its own
repo, each is synced independently. Credentials come from the `GH_TOKEN`
environment variable first (works on any OS); the Keychain item is an optional
macOS fallback. Tokens are only ever passed through the subprocess environment,
never written into command arguments or logs.

> **Security note.** Plugin hooks run on your machine for every matching event as
> soon as the plugin is enabled — not only when the skill is invoked. That is why
> the sync layer is off by default and its `matcher` is scoped to `Write|Edit`.
> Read `scripts/*.py` before enabling; it is deliberately small.

## Design notes

**Why the wiki is model-maintained and hand-editing is banned.** The moment I edit it by
hand, it becomes my notes rather than the agent's memory, and the model stops trusting it
as a source. Consolidation is the model's job; my job is the gate.

**Why `raw/` is append-only.** It is the only layer that can prove a regression. If runs
can be rewritten, the audit trail is decorative.

**Why every skill declares topics in `meta.md`.** Skills that share topics tend to be
edited together; the discovery script surfaces those pairs so a change in one prompts a
check of the other, instead of the two drifting apart silently.

**What I would change.** The gate is the interesting frontier: building enough labelled
cases per skill to let a score decide, at least for the skills whose output is objectively
checkable. That is the step that turns this from assisted evolution into the automatic
kind.

## Adding archiving to an existing skill

Retrofitting a skill that already exists takes two files and one paragraph. Create a `raw/`
directory and an empty `wiki.md`, then append a closing step to that skill's `SKILL.md`
instructing it to create the dated archive folder with its two notes — `input.md` for what
was asked, `summary.md` for the 3-5 findings — and then read `wiki.md` back to update the
index and the cross-run accumulation.

To join cross-skill discovery as well, add a `meta.md` declaring the skill's topics,
product scope, and the data it produces and consumes. Keep the topics specific: generic
words like "report" or "document" inflate the overlap score and drag unrelated skills into
context. Then run discovery once to inspect the result, followed by the validation script —
exit code zero is the pass mark, not a suggestion.

## Credits

The four-layer separation was influenced by Andrej Karpathy's public thinking on agents
accumulating durable knowledge rather than restarting cold each session, and converges
with [WikiSkill](https://arxiv.org/abs/2608.27454) (Google Research, 2026), which arrived
at the same separation from the research side and supplies the empirical case for it.

The original design sketch (in Chinese, drawn 2026-06-08) mapping the LLM-wiki idea onto
a coding-agent skill system is in
[README.zh-CN.md](README.zh-CN.md#与-wikiskillgoogle-research2026的关系).

## License

MIT
