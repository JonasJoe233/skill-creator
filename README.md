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

<!-- APPEND-MARKER -->
