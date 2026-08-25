# Skill Creator

[中文](#中文) · [English](#english)

一个 Claude Code skill，用来创建、评测、迭代其他 skill —— 并让 skill 的执行经验沉淀成可复用的知识，而不是每次跑完就丢。

A Claude Code skill for creating, evaluating, and iterating on other skills — with a built-in mechanism that compounds execution knowledge instead of discarding it after every run.

---

## 中文

### 解决什么问题

写 skill 有两个真实的痛点，市面上的方案基本只解决了第一个。

**第一个：description 写不准，skill 该触发时不触发。** Claude Code 靠 skill 的 `description` 决定要不要加载它。这个字段是纯自然语言，好不好只能实测——但绝大多数人是凭感觉改一版、试两条 query 就上线了。没有 eval set，没有 holdout，改完是变好还是过拟合到自己那两条 query 上，说不清。

**第二个：skill 跑完就失忆。** 你让 Agent 跑一个工作流，它产出了有用的判断（这个数据源口径不对、那个格式客户端解析不了），然后全忘了。下次跑同一个工作流，从零开始。RAG 不解决这个——它每次查询都在重新检索和拼凑原始文档，知识不 compound。

针对第二个问题，Karpathy 提过一个不同的架构：不要在查询时从原始文档检索，让 LLM **主动维护一层持久的 wiki**。知识编译一次，持续积累，不是每次重新推导。

这个项目把两件事合在一起：用可量化的 eval 循环解决触发准确性，用三层归档 + 跨 skill 知识图谱解决知识不沉淀。后者是在 Karpathy 原版单域 wiki 之上做的扩展 —— 让**知识跨独立工作流 compound**，而不只在单一领域内积累。

### 核心架构

四层结构，前三层从 Karpathy 的 LLM Wiki 映射到 Claude Code Skills，第四层是本项目的扩展：

```
┌─────────────────────────────────────────────────────┐
│  Schema 层 — SKILL.md                                │
│  定义 LLM 怎么运行 skill + 强制归档作为最后一步          │
├─────────────────────────────────────────────────────┤
│  Wiki 层 — wiki.md                                   │
│  LLM 编译的执行索引 + 跨次规律积累（永不手动编辑）        │
├─────────────────────────────────────────────────────┤
│  Raw 层 — raw/YYYY-MM-DD/                            │
│  不可变的每次执行归档（input.md + summary.md，只追加）   │
├─────────────────────────────────────────────────────┤
│  Graph 层 — meta.md + discover.py  ← 本项目扩展        │
│  声明式数据依赖 → 自动跨 skill 关联 + 执行前上下文注入    │
└─────────────────────────────────────────────────────┘
```

关键约束是 **Raw 层只追加、Wiki 层只由 LLM 写**。人手改 wiki 会让它和 raw 归档脱钩，下一次编译就把手改的内容盖掉——所以规范里直接禁掉手动编辑。

与 Karpathy 原版的差异：

| Karpathy LLM Wiki | 本项目 |
|---|---|
| 单域 wiki | 多 skill，每个有独立 wiki |
| 手动 ingest 文档 | 归档嵌进工作流末尾，自动执行 |
| 无跨域链接 | `meta.md` 声明数据依赖，`discover.py` 自动算关联 |
| 查询时搜索 wiki | 执行前注入关联 skill 的积累知识 |

### 跨 skill 知识图谱

每个 skill 在 `meta.md` 里声明自己生产什么、消费什么：

```yaml
---
skill: hv-analysis
topics: [深度研究, 竞品分析]
product_scope: [ProductA, ProductB]
data_produces: [PDF研究报告, 竞品对比]
data_consumes: [用户行为数据, query日志分析]
---
```

`scripts/discover.py` 扫所有 skill 的 metadata，用加权算法算两两关联分数：

- `topics` 交集 × 2 —— 主题相似度
- `product_scope` 交集 × 3 —— 产品线重合度
- `data_produces ∩ data_consumes` × 4 —— 数据流依赖，权重最高，双向计算

执行某个 skill 前，先跑一次发现，把关联 skill 的 `wiki.md` 加载进上下文。LLM 带着别的工作流已经积累的判断开始干活，不是从零起步。

**举例：** 跑竞品分析 skill 时，自动拉进用户行为分析 skill 沉淀下来的规律——因为后者 `data_produces` 的东西正好是前者 `data_consumes` 的。不需要手写任何配置。

**这套机制有个已知失效模式**：往 `topics` 里塞泛词（"报告"、"文档"、"分析"）能让关联分数虚高，把不相关的 skill 也拉进上下文，反而污染。所以配了 `scripts/check_meta.py` 做验收，三项硬指标：

1. `VISIBLE` —— discover 能读到的 skill 数必须等于真实 skill 目录数（防止 meta.md 格式错误导致静默漏掉）
2. `ORPHAN` —— 关联数为 0 的 skill 必须为 0
3. `GENERIC` —— 泛词命中数不得超过基线（防止靠塞泛词刷关联数）

退出码 0 才算过。这是判卷标准，不是建议。

### 功能

**Skill 全生命周期**
- 按统一规范创建 skill：双语触发词 frontmatter、Obsidian wiki-link 文件清单、强制归档收尾
- 迭代循环：跑 eval → 在 HTML 查看器里人工评审 → 优化 → 重复
- 版本间 A/B 盲测对比（`agents/comparator.md`）

**知识沉淀**
- 每次执行结束自动建 `raw/YYYY-MM-DD/`，写入 `input.md`（用户要什么）+ `summary.md`（关键决策/踩坑）
- 归档后 LLM 自动更新 `wiki.md`——维护执行索引，积累跨次规律
- `scripts/discover.py` 基于 meta.md 声明算跨 skill 关联

**Description 触发优化**
- `scripts/run_eval.py` —— 通过 `claude -p` 子进程实测触发准确性，默认每条 query 跑 3 次、10 并发、单条 30s 超时，触发率阈值 0.5
- `scripts/improve_description.py` —— LLM 驱动的 description 改写
- `scripts/run_loop.py` —— 自动评估+改进循环，默认最多 5 轮，**40% holdout 防过拟合**（`--holdout 0` 可关）
- `scripts/generate_report.py` —— 输出带训练集/测试集分数的 HTML 报告

训练集分数涨、测试集分数不涨，就是过拟合到 eval set 上了——这是这套循环唯一想拦住的东西。

**Eval 查看器**
- `eval-viewer/viewer.html` —— 键盘导航单页应用，内联渲染 PDF/图片/xlsx，支持跨迭代对比
- `eval-viewer/generate_review.py` —— 零依赖 HTTP 服务（默认端口 3117），`--static` 出离线包
- 评审意见写进 `feedback.json`，主流程读它决定要不要再迭一轮

### 目录结构

```
skill-creator/
├── SKILL.md                    # 主文件——完整工作流定义
├── meta.md                     # 依赖声明，供跨 skill 关联发现
├── wiki.md                     # 执行索引（LLM 维护，不手改）
├── agents/
│   ├── analyzer.md             # 子 Agent：分析 benchmark 结果
│   ├── comparator.md           # 子 Agent：盲测 A/B 对比
│   └── grader.md               # 子 Agent：评估 assertions
├── assets/
│   └── eval_review.html        # 浏览器 UI，编辑评估用例
├── eval-viewer/
│   ├── generate_review.py      # 查看器 HTTP 服务
│   └── viewer.html             # 查看器前端
├── references/
│   └── schemas.md              # evals / grading / benchmark 的 JSON 结构定义
├── scripts/
│   ├── aggregate_benchmark.py
│   ├── check_meta.py           # meta.md 质量验收（三项硬指标）
│   ├── discover.py             # 跨 skill 关联分数计算
│   ├── generate_report.py
│   ├── improve_description.py
│   ├── package_skill.py        # 打成可分发 .skill 包
│   ├── quick_validate.py
│   ├── run_eval.py
│   ├── run_loop.py
│   └── utils.py
└── raw/                        # 每次执行的归档（只追加）
```

### 快速开始

```bash
git clone https://github.com/JonasJoe233/skill-creator.git ~/.claude/skills/skill-creator
```

然后对 Claude Code 说「创建一个新 skill」或「优化 xxx skill 的 description」。流程会带着走：意图捕获 → 草稿 → eval → 迭代 → 归档。

跑一次 description 优化循环：

```bash
python3 ~/.claude/skills/skill-creator/scripts/run_loop.py \
  --eval-set evals.json \
  --skill-path ~/.claude/skills/your-skill \
  --model claude-sonnet-5 \
  --verbose
```

`--model` 是必填项（用于改写 description 的模型）。`--eval-set` 的 JSON 结构见 `references/schemas.md`。

### 给任何现有 skill 加上知识沉淀

最小可行配置两步：

```bash
mkdir -p ~/.claude/skills/your-skill/raw
touch ~/.claude/skills/your-skill/wiki.md
```

在 SKILL.md 末尾加上收尾步骤：

```markdown
## 最后一步：归档并编译 wiki
1. 创建 `raw/YYYY-MM-DD/`，写入 input.md + summary.md
2. 读取 wiki.md 并更新索引与跨次积累
```

要启用跨 skill 发现，再加一个 `meta.md`：

```yaml
---
skill: your-skill
topics: [具体主题1, 具体主题2]      # 别写"报告""文档"这类泛词
product_scope: [产品名]
data_produces: [这个 skill 产出什么]
data_consumes: [这个 skill 需要什么]
---
```

验证：

```bash
python3 ~/.claude/skills/_discover.py your-skill   # 看关联结果
python3 ~/.claude/skills/skill-creator/scripts/check_meta.py   # 退出码 0 才算合格
```

### 依赖

- Claude Code CLI（`claude` 命令可用，eval 靠 `claude -p` 子进程跑）
- Python 3.10+ 与 `pyyaml`
- `gh` CLI（可选，打包/建仓时用）
- Obsidian（可选，用于 wiki-link 导航和 graph view）

### 致谢

- 架构灵感来自 [Karpathy 的 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- 基于 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 系统构建

---

## English

### The problem

Writing skills has two real pain points. Most tooling only addresses the first.

**One: the `description` is imprecise, so the skill doesn't fire when it should.** Claude Code decides whether to load a skill based on its `description` field. That field is pure natural language — the only way to know if it's good is to measure. Yet almost everyone rewrites it by feel, tries two queries, and ships. No eval set, no holdout. Whether the rewrite actually improved things or just overfit to those two queries is anyone's guess.

**Two: skills forget everything the moment they finish.** You run a workflow, the agent produces genuinely useful judgments (this data source uses the wrong definition; that format won't parse on the client), and then it's gone. Next run of the same workflow starts from zero. RAG doesn't fix this — it re-retrieves and re-assembles raw documents on every query. Knowledge never compounds.

For the second problem, Karpathy proposed a different architecture: instead of retrieving from raw docs at query time, have the LLM **actively maintain a persistent wiki**. Knowledge gets compiled once and accumulates, rather than being re-derived every time.

This project combines both: a quantifiable eval loop for trigger accuracy, and a three-layer archive plus cross-skill knowledge graph for knowledge retention. The latter extends Karpathy's single-domain wiki so knowledge **compounds across independent workflows**, not just within one domain.

### Architecture

Four layers. The first three map Karpathy's LLM Wiki onto Claude Code Skills; the fourth is this project's extension.

```
┌─────────────────────────────────────────────────────┐
│  Schema layer — SKILL.md                             │
│  How the LLM runs the skill + archiving as mandatory │
│  final step                                          │
├─────────────────────────────────────────────────────┤
│  Wiki layer — wiki.md                                │
│  LLM-compiled execution index + accumulated patterns │
│  (never hand-edited)                                 │
├─────────────────────────────────────────────────────┤
│  Raw layer — raw/YYYY-MM-DD/                         │
│  Immutable per-run archive (input.md + summary.md,   │
│  append-only)                                        │
├─────────────────────────────────────────────────────┤
│  Graph layer — meta.md + discover.py  ← extension    │
│  Declarative data deps → automatic cross-skill       │
│  linkage + pre-execution context injection           │
└─────────────────────────────────────────────────────┘
```

The load-bearing constraint: **the raw layer is append-only, and the wiki layer is written only by the LLM.** Hand-editing the wiki decouples it from the raw archive, and the next compile pass silently overwrites your edits — so the spec forbids manual edits outright.

Differences from the original:

| Karpathy's LLM Wiki | This project |
|---|---|
| Single-domain wiki | Many skills, each with its own wiki |
| Manual document ingest | Archiving embedded at the end of the workflow, automatic |
| No cross-domain links | `meta.md` declares data deps; `discover.py` computes linkage |
| Search the wiki at query time | Inject related skills' accumulated knowledge before execution |

### Cross-skill knowledge graph

Each skill declares what it produces and consumes in `meta.md`:

```yaml
---
skill: hv-analysis
topics: [deep-research, competitive-analysis]
product_scope: [ProductA, ProductB]
data_produces: [PDF research report, competitor comparison]
data_consumes: [user behavior data, query log analysis]
---
```

`scripts/discover.py` scans every skill's metadata and scores each pair with a weighted formula:

- `topics` intersection × 2 — topical similarity
- `product_scope` intersection × 3 — product-line overlap
- `data_produces ∩ data_consumes` × 4 — data-flow dependency, highest weight, computed in both directions

Before running a skill, run discovery and load the related skills' `wiki.md` into context. The LLM starts with judgments other workflows already earned instead of from scratch.

**Example:** running the competitive-analysis skill automatically pulls in patterns accumulated by the user-behavior-analysis skill — because what the latter `data_produces` is exactly what the former `data_consumes`. No hand-written wiring.

**This mechanism has a known failure mode:** stuffing generic terms into `topics` ("report", "document", "analysis") inflates linkage scores, dragging irrelevant skills into context and polluting it. So `scripts/check_meta.py` enforces three hard gates:

1. `VISIBLE` — the number of skills discovery can read must equal the real skill-directory count (catches malformed `meta.md` that would otherwise be silently skipped)
2. `ORPHAN` — skills with zero links must be zero
3. `GENERIC` — generic-term hits must not exceed the baseline (blocks score-farming via vague topics)

Exit code 0 or it doesn't pass. This is the grading standard, not a suggestion.

### Features

**Full skill lifecycle**
- Create skills against one spec: bilingual trigger-word frontmatter, Obsidian wiki-link file manifest, mandatory archiving step
- Iteration loop: run eval → human review in the HTML viewer → improve → repeat
- Blind A/B comparison between versions (`agents/comparator.md`)

**Knowledge retention**
- Every run creates `raw/YYYY-MM-DD/` with `input.md` (what the user asked for) and `summary.md` (key decisions and pitfalls)
- After archiving, the LLM updates `wiki.md` — maintaining the execution index and accumulating cross-run patterns
- `scripts/discover.py` computes cross-skill linkage from `meta.md` declarations

**Description trigger optimization**
- `scripts/run_eval.py` — measures real trigger accuracy via `claude -p` subprocesses; defaults to 3 runs per query, 10 workers, 30s per-query timeout, 0.5 trigger-rate threshold
- `scripts/improve_description.py` — LLM-driven description rewriting
- `scripts/run_loop.py` — automated eval-and-improve loop, up to 5 iterations by default, with a **40% holdout to catch overfitting** (`--holdout 0` disables)
- `scripts/generate_report.py` — HTML report with separate train and test scores

Train score up while test score is flat means you overfit to the eval set. That's the one thing this loop exists to catch.

**Eval viewer**
- `eval-viewer/viewer.html` — keyboard-navigable SPA, renders PDF/images/xlsx inline, compares across iterations
- `eval-viewer/generate_review.py` — zero-dependency HTTP server (port 3117 by default), `--static` emits an offline bundle
- Review notes land in `feedback.json`; the main flow reads it to decide whether to iterate again

<!-- APPEND-MARKER -->
