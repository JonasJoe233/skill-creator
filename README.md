# skill-creator
> 创建、评测、迭代其他 skill，并让每次执行的经验沉淀成可复用知识而不是跑完就丢 | Creates, evaluates and iterates on other skills, compounding what each run learns instead of discarding it

## 中文说明

### 解决什么问题

写 skill 有两个真实痛点，市面上的方案基本只解决第一个。第一个是 description 写不准，该触发时不触发：这个字段是纯自然语言，好不好只能实测，但多数人凭感觉改一版、试两条 query 就上线，没有评估集也没有留出集，改完是真变好还是过拟合到自己那两条 query 上，说不清。第二个更隐蔽——skill 跑完就失忆：一次执行里产出了有用的判断（某个数据源口径不对、某种格式在客户端解析不了），下次跑同一个工作流从零开始，知识不累积。这个 skill 把两件事合在一起：用可量化的评估循环解决触发准确性，用三层归档加跨 skill 关联解决知识不沉淀。

### 何时触发

触发词：创建 skill、新建 skill、魔改 skill、优化 skill、测试 skill、create skill、improve skill、edit skill、optimize skill description。

直接执行：用户明确说要创建、修改或优化某个 skill。

先确认：用户说「把这个流程固化下来」时，先问一句是不是要做成一个 skill。

### 工作流

创建一个新 skill：

1. 捕获意图，再做访谈与调研，把用户真正要解决的问题问清楚，而不是照着一句话直接写文件。
2. 按统一规范写 SKILL.md：frontmatter 的触发词分「直接执行」与「先确认」两类写清、正文开头第一节是带链接的目录文件说明、末尾强制带归档收尾步骤。
3. 建 `raw/` 与 `wiki.md` 的归档机制，并写一份 `meta.md` 声明这个 skill 生产什么、消费什么，用于跨 skill 关联发现。
4. 同步到远端仓库，这是新建 skill 的强制最后一步，与归档同级。

评估与迭代：

1. 在同一轮里生成带 skill 与不带 skill 的两组运行，形成可对照的基线。
2. 运行期间起草判定条目，运行完成后采集耗时数据。
3. 评分、聚合，然后启动查看器做人工评审；评审意见落进反馈文件，主流程读它决定要不要再迭一轮。
4. 需要判断两个版本谁更好时走盲测对比，避免知道哪个是新版带来的偏袒。

description 优化：

1. 生成一批用于测触发的评估查询，先与用户确认这批查询是否代表真实用法。
2. 跑优化循环：实测触发准确性、由模型改写 description、再测，默认最多若干轮，并留出一部分查询不参与训练。
3. 看报告里训练集与测试集两个分数：训练涨、测试不涨，就是过拟合到评估集上了——这是整个循环唯一想拦住的东西。
4. 确认后应用结果，最后归档并更新 `wiki.md`。

### 目录结构

```
skill-creator/
├── SKILL.md                    # skill 主文件：skill 规范、创建流程、评估流程、description 优化、环境适配
├── meta.md                     # 关联声明，供跨 skill 关联发现
├── README.md                   # 本文件
├── wiki.md                     # 历次 skill 创建与优化记录索引，由模型维护
├── .gitignore                  # 忽略系统噪音文件
├── agents/
│   ├── analyzer.md             # 子 agent 指令：分析评测结果
│   ├── comparator.md           # 子 agent 指令：盲测 A/B 对比
│   └── grader.md               # 子 agent 指令：按判定条目评分
├── assets/
│   └── eval_review.html        # description 评测用的浏览器界面
├── eval-viewer/
│   ├── generate_review.py      # 查看器服务，零依赖，可导出离线包
│   └── viewer.html             # 查看器前端，键盘导航、内联渲染多种格式
├── references/
│   └── schemas.md              # 评估集、评分、汇总结果的 JSON 结构定义
├── scripts/
│   ├── run_eval.py             # 实测触发准确性
│   ├── run_loop.py             # 自动评估与改进循环，带留出集
│   ├── improve_description.py  # 由模型改写 description
│   ├── generate_report.py      # 输出带训练集与测试集分数的报告
│   ├── aggregate_benchmark.py  # 汇总评测结果
│   ├── discover.py             # 跨 skill 关联分数计算
│   ├── check_meta.py           # 关联声明质量验收，三项硬指标
│   ├── quick_validate.py       # 快速校验
│   ├── package_skill.py        # 打包成可分发的 skill 包
│   └── utils.py                # 公共函数
└── raw/                        # 每次执行的归档，只追加
```

### 产物与归档

产物是一个符合规范的 skill 目录（含 SKILL.md、关联声明、归档机制），以及评估集、评测报告与优化后的 description。

归档机制本身就是这个 skill 要推广的东西，分三层：`raw/` 是不可变的每次执行归档，按日期建目录放「用户要什么」与「关键决策和踩坑」，只追加不改写；`wiki.md` 是由模型编译的执行索引与跨次积累，永不手动编辑——人手改过之后它就和归档脱钩了，下一次编译会把手改的内容盖掉，所以规范里直接禁掉；`meta.md` 声明数据依赖，让关联发现能在执行前把相关 skill 已经积累的判断注入进来，于是模型带着别处赚到的经验开始干活，而不是从零起步。

关联机制有一个已知失效模式：往主题字段里塞泛词能让关联分数虚高，把不相关的 skill 也拉进上下文，反而污染判断。所以配了验收脚本做三项硬指标——能被读到的 skill 数必须等于真实目录数（防止声明文件格式错误导致静默漏掉）、关联数为零的 skill 必须为零、泛词命中数不得超过基线。退出码为零才算过，这是判卷标准而不是建议。

## English

### What problem it solves

Writing skills has two real pain points, and most tooling only addresses the first. One: the description is imprecise, so the skill does not fire when it should. That field is pure natural language, and the only way to know whether it is good is to measure — yet the usual practice is rewriting it by feel, trying two queries and shipping, with no eval set and no holdout, leaving it unknowable whether the rewrite improved anything or merely overfit to those two queries. Two, and subtler: a skill forgets everything the moment it finishes. A run produces genuinely useful judgements — this data source uses the wrong definition, that format will not parse on the client — and the next run of the same workflow starts from zero. This skill combines both answers: a quantifiable eval loop for trigger accuracy, and a three-layer archive plus cross-skill linkage so knowledge accumulates.

### When it triggers

Trigger phrases: 创建 skill, 新建 skill, 魔改 skill, 优化 skill, 测试 skill, create skill, improve skill, edit skill, optimize skill description.

Act directly: the user explicitly asks to create, modify or optimise a skill.

Confirm first: when the user says "let's make this process permanent", ask whether it should become a skill.

### Workflow

Creating a new skill:

1. Capture the intent, then interview and research to establish the actual problem rather than writing files straight from one sentence.
2. Write SKILL.md against one spec: trigger phrases in the frontmatter split into act-directly and confirm-first, a linked file manifest as the first section of the body, and a mandatory archiving step at the end.
3. Set up the `raw/` and `wiki.md` archive mechanism and write a `meta.md` declaring what the skill produces and consumes, which drives cross-skill discovery.
4. Sync to the remote repository — a mandatory final step for a new skill, on the same footing as archiving.

Evaluating and iterating:

1. Generate both with-skill and baseline runs in the same turn so there is a comparable control.
2. Draft the assertions while the runs are in flight, and capture timing data once they finish.
3. Grade, aggregate, then open the viewer for human review; review notes land in a feedback file that the main flow reads to decide whether to iterate again.
4. When two versions must be compared, run a blind comparison so knowing which one is new cannot bias the verdict.

Optimising a description:

1. Generate a set of queries for measuring triggering, and confirm with the user that they represent real usage.
2. Run the loop: measure trigger accuracy, have the model rewrite the description, measure again, for a bounded number of iterations, holding back part of the query set from training.
3. Read both scores in the report: training up while test is flat means overfitting to the eval set, which is the one thing this loop exists to catch.
4. Apply the result once confirmed, then archive and update `wiki.md`.

### Layout

```
skill-creator/
├── SKILL.md                    # main file: the skill spec, creation flow, eval flow, description optimisation, environment notes
├── meta.md                     # relation declarations for cross-skill discovery
├── README.md                   # this file
├── wiki.md                     # index of past creations and optimisations, model-maintained
├── .gitignore                  # ignores OS noise files
├── agents/
│   ├── analyzer.md             # subagent: analyse benchmark results
│   ├── comparator.md           # subagent: blind A/B comparison
│   └── grader.md               # subagent: grade against assertions
├── assets/
│   └── eval_review.html        # browser UI for description evaluation
├── eval-viewer/
│   ├── generate_review.py      # viewer server, zero dependencies, offline bundle supported
│   └── viewer.html             # viewer frontend, keyboard navigable, renders several formats inline
├── references/
│   └── schemas.md              # JSON shapes for eval sets, grading and aggregated results
├── scripts/
│   ├── run_eval.py             # measure trigger accuracy for real
│   ├── run_loop.py             # automated eval-and-improve loop with a holdout
│   ├── improve_description.py  # model-driven description rewriting
│   ├── generate_report.py      # report with separate train and test scores
│   ├── aggregate_benchmark.py  # aggregate benchmark results
│   ├── discover.py             # cross-skill linkage scoring
│   ├── check_meta.py           # quality gates on relation declarations
│   ├── quick_validate.py       # fast validation
│   ├── package_skill.py        # bundle into a distributable skill package
│   └── utils.py                # shared helpers
└── raw/                        # per-run archive, append-only
```

### Outputs & archiving

The outputs are a spec-compliant skill directory (SKILL.md, relation declarations, archive mechanism) plus eval sets, evaluation reports and an improved description.

The archive mechanism is itself what this skill propagates, in three layers. `raw/` is the immutable per-run archive, one dated folder holding what the user asked for and the key decisions and pitfalls, append-only and never rewritten. `wiki.md` is the model-compiled execution index and cross-run accumulation, never hand-edited — a manual edit decouples it from the archive and the next compile pass overwrites it, so the spec forbids it outright. `meta.md` declares data dependencies so discovery can inject the accumulated judgements of related skills before execution, letting the model start with experience earned elsewhere rather than from scratch.

The linkage mechanism has a known failure mode: stuffing generic terms into the topics field inflates scores, drags irrelevant skills into context and pollutes the judgement. A validation script therefore enforces three hard gates — the number of readable skills must equal the real directory count (catching malformed declarations that would otherwise be silently skipped), skills with zero links must be zero, and generic-term hits must not exceed the baseline. Exit code zero or it does not pass; this is the grading standard, not a suggestion.

## 补充说明 / Notes

以下内容来自本仓库原有的手写说明，SKILL.md 中没有，保留在此。

### 架构由来

四层结构中，前三层是把 Karpathy 提出的 LLM Wiki 构想映射到 skill 系统上，第四层是本项目的扩展：

```
Schema 层 — SKILL.md      定义模型怎么运行这个 skill，并把归档写成强制的最后一步
Wiki 层  — wiki.md        由模型编译的执行索引与跨次积累，永不手动编辑
Raw 层   — raw/<日期>/     不可变的每次执行归档，只追加
Graph 层 — meta.md + 关联发现脚本   声明式数据依赖，自动跨 skill 关联并在执行前注入上下文
```

与原始构想的差异：原版是单域 wiki、手动把文档 ingest 进去、没有跨域链接、查询时再去搜 wiki；这里是每个 skill 各有独立 wiki、归档嵌进工作流末尾自动执行、由声明式依赖自动算出关联，并在执行前把关联 skill 的积累注入进来。换句话说，扩展的部分是让知识跨独立工作流累积，而不只在单一领域内累积。

关联分数的算法：主题交集按较低权重计，产品线交集按中等权重计，一方产出正好是另一方所需的数据依赖按最高权重计并双向计算。举例来说，跑竞品分析类 skill 时会自动拉进行为分析类 skill 沉淀的规律，因为后者产出的正是前者消费的，不需要手写任何配置。

### 快速开始

把这个仓库 clone 到 `~/.claude/skills/skill-creator`，然后直接说「创建一个新 skill」或「优化某个 skill 的 description」，流程会带着走：意图捕获、草稿、评估、迭代、归档。

跑一次 description 优化循环时，指定评估集、目标 skill 路径与用于改写的模型；模型参数是必填项，评估集的 JSON 结构见 `references/schemas.md`。

### 给任何现有 skill 加上知识沉淀

最小可行配置两步：建一个 `raw/` 目录、建一个空的 `wiki.md`；然后在该 skill 的 SKILL.md 末尾加一节收尾步骤，写明先建当日归档目录并写入两份说明，再读取 `wiki.md` 更新索引与跨次积累。

要启用跨 skill 发现，再补一个 `meta.md`，声明这个 skill 的主题、产品范围、产出与消费的数据——主题里写具体的词，不要写「报告」「文档」这类泛词。配好后跑一次关联发现看结果，再跑验收脚本，退出码为零才算合格。

### 依赖

命令行版的 Claude Code（评估通过子进程调用它来实测触发）、Python 3.10 及以上并安装 `pyyaml`、可选的 `gh` 命令行（打包与建仓时用）、可选的 Obsidian（用于 wiki 链接导航与图谱视图）。

### 致谢

架构灵感来自 Karpathy 的 LLM Wiki 构想，实现构建在 Claude Code 的 skill 系统之上。

### Notes (English)

From the repository's earlier hand-written README, not covered by SKILL.md.

Architecture: of the four layers, the first three map Karpathy's LLM Wiki idea onto the skill system and the fourth is this project's extension — the schema layer (SKILL.md) defines how the model runs the skill and makes archiving a mandatory final step; the wiki layer is a model-compiled index and accumulation that is never hand-edited; the raw layer is an immutable, append-only per-run archive; and the graph layer adds declarative data dependencies with automatic cross-skill linkage and pre-execution context injection. The original was a single-domain wiki with manual document ingest, no cross-domain links, and search at query time; here each skill has its own wiki, archiving is embedded at the end of the workflow and runs automatically, linkage is computed from declared dependencies, and related skills' accumulation is injected before execution. The extension, in short, is making knowledge compound across independent workflows rather than only within one domain.

Linkage scoring weights topical overlap lowest, product-line overlap in the middle, and a genuine data dependency — where one skill's output is exactly another's input — highest, computed in both directions. Running a competitive-analysis skill therefore pulls in the patterns accumulated by a behaviour-analysis skill automatically, with no hand-written wiring.

Quick start: clone this repository into `~/.claude/skills/skill-creator`, then say "create a new skill" or "optimise the description for skill X" and the flow walks through intent capture, draft, eval, iterate, archive. To run one description-optimisation loop, supply the eval set, the target skill path and the model used for rewriting; the model argument is required, and the eval-set JSON shape is documented in `references/schemas.md`.

Adding knowledge retention to an existing skill takes two steps — create a `raw/` directory and an empty `wiki.md` — plus a closing section at the end of that skill's SKILL.md instructing it to create the dated archive folder with its two notes and then update the wiki index and accumulation. To enable cross-skill discovery, add a `meta.md` declaring topics, product scope, and what the skill produces and consumes, keeping topics specific rather than generic. Then run discovery to inspect the result and the validation script, where exit code zero means passing.

Requirements: the Claude Code CLI (evals invoke it as subprocesses to measure triggering for real), Python 3.10 or newer with `pyyaml`, optionally the `gh` CLI for packaging and repository creation, and optionally Obsidian for wiki-link navigation and graph view.

Credits: the architecture is inspired by Karpathy's LLM Wiki idea and built on the Claude Code skill system.
