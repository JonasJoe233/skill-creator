# Skill Creator

一个 Claude Code skill，用于创建、测试和迭代优化 skill —— 内置基于 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 思路的知识积累机制。

## 解决什么问题

Coding Agent（Claude Code、Cursor、Codex）有一个记忆问题：你让 Agent 跑一个工作流，它产出了有用的洞察，然后全忘了。下次跑同一个工作流，从零开始。RAG 不解决这个问题——它每次查询都在重新检索和拼凑，知识不 compound。

Karpathy 提了一个不同的架构：不要在查询时从原始文档里检索，让 LLM **主动维护一层持久的 wiki**。知识编译一次，持续积累，不是每次重新推导。

这个项目把这个思路进一步发展——应用到多 Skill 的 Agent 系统中，让**知识跨独立工作流 compound**，而不只是在单一领域内积累。

## 核心架构

三层结构，从 Karpathy 的 LLM Wiki 映射到 Claude Code Skills，外加一层跨域关联：

```
┌─────────────────────────────────────────────────────┐
│  Schema 层 — SKILL.md                               │
│  定义 LLM 怎么运行 skill + 强制归档作为最后一步       │
├─────────────────────────────────────────────────────┤
│  Wiki 层 — wiki.md                                  │
│  LLM 编译的执行索引 + 跨次规律积累（永不手动编辑）    │
├─────────────────────────────────────────────────────┤
│  Raw 层 — raw/YYYY-MM-DD/                           │
│  不可变的每次执行归档（input.md + summary.md，只追加） │
├─────────────────────────────────────────────────────┤
│  Graph 层 — meta.md + _discover.py  [创新点]         │
│  声明式数据依赖 → 自动跨 skill 知识图谱 + 上下文注入  │
└─────────────────────────────────────────────────────┘
```

### 与 Karpathy 原版的差异

| Karpathy LLM Wiki | 本系统 |
|---|---|
| 单域 wiki | 多 Skill，每个有独立 wiki |
| 手动 ingest 文档 | 归档嵌入工作流，自动执行 |
| 无跨域链接 | `meta.md` 声明数据依赖，`_discover.py` 自动计算关联 |
| 查询时搜索 wiki | 执行前注入关联 Skill 的积累知识 |

## 核心创新：跨 Skill 知识图谱

每个 Skill 在 `meta.md` 里声明自己生产和消费什么：

```yaml
skill: hv-analysis
topics: [深度研究, 竞品分析]
product_scope: [ProductA, ProductB]
data_produces: [PDF研究报告, 竞品对比]
data_consumes: [用户行为数据, query日志分析]
```

`_discover.py` 扫描所有 Skill 的 metadata，用加权算法计算关联分数：

- `topics` 交集 × 2（主题相似度）
- `product_scope` 交集 × 3（产品线重合度）
- `data_produces ∩ data_consumes` × 4（数据流依赖——权重最高）

执行某个 Skill 前，系统自动发现关联 Skill 并加载它们的 `wiki.md` 到上下文。LLM 带着跨域积累知识开始工作，不是从零起步。

**举例：** 执行竞品分析 Skill 时，自动拉取用户行为分析 Skill 积累的规律（因为后者 produce 的数据正好是前者 consume 的）。不需要手动配置。

## 与现有方案的对比

调研了 400+ 相关仓库（LLM Wiki 实现、Agent 记忆系统、Claude Code skill 框架）：

- **LLM Wiki 三层架构** — 已充分产品化（atomicstrata/llm-wiki-compiler、SwarmVault、Pratiyush/llm-wiki）
- **Agent 持久记忆** — 竞争激烈（Graphiti、Mem0、OpenLore、Mnemon、PAR）
- **Claude Code Skill 框架** — Brain-AI、MemStack、PFAA-Agents

**没有现存项目实现了声明式跨 Skill 数据依赖发现。** 所有知识共享方案要么是共享记忆池（被动查询），要么是代码级静态分析。没有人做到"通过声明式 metadata 自动计算 Skill 间关联分数，并在执行前精准注入相关上下文"。

## 功能

### Skill 全生命周期管理
- 按标准化规范创建 Skill（双语触发词 frontmatter、Obsidian wiki-link 文件清单、强制归档步骤）
- 迭代改进循环：跑 eval → 用户在 HTML 查看器中评审 → 优化 → 重复
- 版本间 A/B 盲测对比

### 知识积累
- **自动归档**：每次 Skill 执行结束创建 `raw/YYYY-MM-DD/`，包含输入摘要 + 核心结论
- **LLM 编译 wiki**：归档后 LLM 自动更新 `wiki.md`——维护执行索引，积累跨次规律
- **跨 Skill 发现**：`_discover.py` 基于 meta.md 声明计算 Skill 间关联

### Description 触发优化
- `scripts/run_eval.py` — 通过 `claude -p` 子进程测试触发准确性
- `scripts/improve_description.py` — LLM 驱动的 description 改写
- `scripts/run_loop.py` — 自动评估+改进循环，train/test split（40% holdout 防过拟合）
- `scripts/generate_report.py` — 生成带训练集/测试集得分的 HTML 报告

### Eval 查看器
- `eval-viewer/viewer.html` — 键盘导航单页应用，内联渲染 PDF/图片/xlsx，跨迭代对比
- `eval-viewer/generate_review.py` — 零依赖 HTTP 服务，支持 `--static` 离线模式
- 反馈写入 `feedback.json`，主流程读取后决定是否继续迭代

## 目录结构

```
skill-creator/
├── SKILL.md                  # 主文件——完整工作流定义
├── meta.md                   # 依赖声明，供跨 Skill 关联发现
├── wiki.md                   # 执行索引（LLM 维护）
├── agents/
│   ├── analyzer.md           # 子 Agent：分析 benchmark 结果
│   ├── comparator.md         # 子 Agent：盲测 A/B 对比
│   └── grader.md             # 子 Agent：评估 assertions
├── assets/
│   └── eval_review.html      # 浏览器 UI，编辑评估用例
├── eval-viewer/
│   ├── generate_review.py    # Eval 查看器 HTTP 服务
│   └── viewer.html           # Eval 查看器前端
├── references/
│   └── schemas.md            # JSON schema 定义（evals、grading、benchmark）
└── scripts/
    ├── aggregate_benchmark.py
    ├── discover.py           # 跨 Skill 关联分数计算
    ├── generate_report.py
    ├── improve_description.py
    ├── package_skill.py
    ├── quick_validate.py
    ├── run_eval.py
    ├── run_loop.py
    └── utils.py
```

## 快速开始

1. 把这个 Skill 复制到 `~/.claude/skills/skill-creator/`
2. 对 Claude Code 说："创建一个新 skill" 或 "create a new skill"
3. Skill 会引导你完成：意图捕获 → 草稿 → 评估 → 迭代 → 归档

### 给任何现有 Skill 加上知识积累

最小可行配置：

```bash
mkdir -p ~/.claude/skills/your-skill/raw
touch ~/.claude/skills/your-skill/wiki.md
```

在 SKILL.md 最后一步加上：
```markdown
## 最后一步：归档并编译 wiki
1. 创建 `raw/YYYY-MM-DD/`，写入 input.md + summary.md
2. 读取 wiki.md 并更新索引
```

要启用跨 Skill 发现，加 `meta.md`：
```yaml
---
skill: your-skill
topics: [主题1, 主题2]
product_scope: [产品名]
data_produces: [这个 skill 产出什么]
data_consumes: [这个 skill 需要什么]
---
```

然后运行：`python3 ~/.claude/skills/_discover.py your-skill`

## 依赖

- Claude Code CLI（`claude` 命令可用）
- `gh` CLI（打包 Skill 时创建 GitHub 仓库）
- Python 3.10+（eval 脚本）
- Obsidian（可选，用于 wiki-link 导航和 graph view）

## 致谢

- 架构灵感来自 [Karpathy 的 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- 基于 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 系统构建
