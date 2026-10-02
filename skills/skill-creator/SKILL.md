---
name: skill-creator
description: |
  创建新 skill、改进现有 skill、运行评估测试 skill 性能。
  触发词：创建 skill、新建 skill、魔改 skill、优化 skill、测试 skill、create skill、improve skill、edit skill、optimize skill description。
  确定性触发（直接执行）：用户明确说要创建/修改/优化某个 skill。
  非确定性触发（先问）：用户说"把这个流程固化下来"——询问："要把它做成一个 skill 吗？"
tags:
  - skill-creator
---

## 目录文件说明

| 文件/目录                                                                            | 作用                                       |
| -------------------------------------------------------------------------------- | ---------------------------------------- |
| [[skill-creator/SKILL\|SKILL.md]]                                                | Skill 主文件（本文件）                           |
| [[skill-creator/meta\|meta.md]]                                                  | 关联声明：topics/product_scope/data 字段，供 `_discover.py` 自动计算与其他 skill 的关联关系 |
| [[skill-creator/wiki\|wiki.md]]                                                  | 历次 skill 创建记录索引（LLM 维护）                  |
| [[skill-creator/agents/analyzer\|agents/analyzer.md]]                            | 分析 benchmark 结果的子 Agent 指令               |
| [[skill-creator/agents/comparator\|agents/comparator.md]]                        | 盲测 A/B 对比的子 Agent 指令                     |
| [[skill-creator/agents/grader\|agents/grader.md]]                                | 评估 assertions 的子 Agent 指令                |
| [[skill-creator/references/schemas\|references/schemas.md]]                      | evals.json / grading.json 等 JSON 结构定义    |
| [[skill-creator/eval-viewer/generate_review.py\|eval-viewer/generate_review.py]] | 生成 eval 查看器的脚本                           |
| [[skill-creator/eval-viewer/viewer.html\|eval-viewer/viewer.html]]               | Eval 查看器 HTML 模板                         |
| [[skill-creator/assets/eval_review.html\|assets/eval_review.html]]               | Description 优化评测 HTML 模板                 |
| [[skill-creator/scripts/__init__.py\|scripts/__init__.py]]                       | 脚本包初始化                                   |
| [[skill-creator/scripts/aggregate_benchmark.py\|scripts/aggregate_benchmark.py]] | 聚合 benchmark 结果                          |
| [[skill-creator/scripts/generate_report.py\|scripts/generate_report.py]]         | 生成评估报告                                   |
| [[skill-creator/scripts/improve_description.py\|scripts/improve_description.py]] | 优化 skill description                     |
| [[skill-creator/scripts/package_skill.py\|scripts/package_skill.py]]             | 打包 skill                                 |
| [[skill-creator/scripts/quick_validate.py\|scripts/quick_validate.py]]           | 快速校验 skill 结构                            |
| [[skill-creator/scripts/run_eval.py\|scripts/run_eval.py]]                       | 运行单次评估                                   |
| [[skill-creator/scripts/run_loop.py\|scripts/run_loop.py]]                       | Description 优化循环                         |
| [[skill-creator/scripts/utils.py\|scripts/utils.py]]                             | 工具函数                                     |
| [[skill-creator/scripts/discover.py\|scripts/discover.py]]                       | 跨 skill 关联发现（扫描 meta.md 计算 topic 重叠度）   |
| `raw/`                                                                           | 每次 skill 创建/优化的归档（input.md + summary.md） |
| [[skill-creator/scripts/check_meta]] | (待补充用途说明) |
| [[skill-creator/README]] | (待补充用途说明) |

# Skill Creator

创建新 skill 并迭代优化的工具。整体流程：

- 明确 skill 要做什么、怎么做
- 写 skill 草稿（遵循下方「Skill 创作规范」）
- 设计测试 prompt，运行 claude-with-skill
- 和用户一起评估结果（定性 + 定量）
- 根据反馈重写，循环直到满意
- 优化 description 触发准确性

遇到用户已有草稿的情况，直接从评估/迭代步骤切入。用户说"不用跑那么多 eval，随便搞搞"也可以灵活处理。

## 运行环境与路径约定（作为插件安装时）

本 skill 以 Claude Code 插件形式分发，涉及三类路径，别混：

- **本 skill 自带的工具脚本**：在 `${CLAUDE_PLUGIN_ROOT}/skills/skill-creator/`（下文凡调 `scripts/`、`eval-viewer/` 都从这里取；`${CLAUDE_PLUGIN_ROOT}` 由 Claude Code 注入，更新时会变，别往里写状态）。
- **你为用户创建/管理的 skill**：落在**用户的 skills 目录** `<skillsDir>`，默认 `~/.claude/skills/`；若用户在插件配置里改了 `skillsDir` 以配置为准。
- **本 skill 自身的归档（raw/wiki）**：写到 `${CLAUDE_PLUGIN_DATA}/skill-creator/`（跨更新保留、可写）。

---

## Skill 创作规范（创建/修改任何 skill 时必须遵守）

这是本 skill 创作体系的核心约定，所有新建和修改的 skill 都必须符合。

### 1. SKILL.md frontmatter 格式

```yaml
---
name: skill-name
description: |
  一句话功能概括（20字以内）。
  触发词：中文触发词1、触发词2、English trigger、another trigger。
  确定性触发（直接执行）：明确说明何时直接执行。
  非确定性触发（先问）：何时先确认——询问："确认话术"。
tags:
  - skill-name   # 与目录名一致
---
```

**description 设计原则：**
- 中英双语触发词，中文覆盖口语表达，英文覆盖正式查询
- 确定性触发 = 用户意图明确时直接执行，不需要再问
- 非确定性触发 = 触发词命中但意图模糊时，先用一句话确认

### 2. 目录文件说明（正文开头第一节）

frontmatter 结束后，正文第一节必须是「目录文件说明」表格，列出 skill 目录下所有文件：

```markdown
## 目录文件说明

| 文件/目录 | 作用 |
|-----------|------|
| [[skill-name/SKILL\|SKILL.md]] | Skill 主文件 |
| [[skill-name/path/file\|显示名]] | 文件用途 |
| `raw/` | 每次执行的归档目录 |
```

- `.md`、`.py`、`.json`、`.csv` 等文件用 `[[skill-name/path|显示名]]` wiki 链接
- 空目录（`raw/`）用反引号，不强制链接
- **文件有增删时必须同步更新此表格**

### 3. raw/ 归档 + wiki.md 机制

每个 skill 目录下都需要：

```
skill-name/
├── raw/          # 每次执行的原始归档（只追加，不修改）
│   └── YYYY-MM-DD[_主题]/
│       ├── input.md    # 本次输入摘要
│       ├── summary.md  # 本次核心结论（3-5条）
│       └── [输出文件副本]
└── wiki.md       # LLM 维护的跨次索引（不要手动编辑）
```

**skill 工作流的最后一步必须包含归档步骤：**

```markdown
## 最后一步：归档到 raw/ 并 compile wiki

1. 在 `~/.claude/skills/<skill>/raw/YYYY-MM-DD[_主题]/` 下创建：
   - `input.md`：输入摘要
   - `summary.md`：核心结论 3-5 条
   - 主要输出文件的副本

2. 读取 `wiki.md` 并更新索引表，追加本次记录
```

**wiki.md 最小模板：**
```markdown
# <Skill名> 知识库

## 执行索引
| 日期 | 主题 | 核心结论 | 文件 |
|------|------|---------|------|

## 跨次积累
[多次执行后 LLM 填写的规律性观察]
```

### 4. meta.md（关联发现）

每个 skill 目录下创建 `meta.md`，供 `_discover.py` 计算关联关系：

```yaml
---
skill: skill-name
topics: [主题1, 主题2]
product_scope: [ProductA, ProductB]  # 不涉及则留空 []
data_produces: [产出数据类型]
data_consumes: [消费数据类型]
---

## 关联 Skill

- [[related-skill/SKILL|related-skill]] — 关联原因
```

关联 skill 用 `[[skill-name/SKILL|skill-name]]` 格式，确保 Obsidian 能跳转到对应 SKILL.md。

运行关联发现：
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/skill-creator/scripts/discover.py" <skill-name> --skills-dir <skillsDir>
```

### 5. 版本持久化（由插件同步层处理）

skill 的归档不止于本地。本插件带了一个**同步层**（见插件 README 的 Automation 一节），在你写 skill 文件时自动 commit、并按用户配置决定是否 push 到远端——这样 raw/ 证据和 wiki/SKILL 的演进天然进 git 历史，可审计、可回滚。**它默认关闭**，由用户在插件配置里显式开启，不会在任何人机器上擅自推送。

- **默认（single-repo）**：所有 skill 共用一个 git 仓。用户开 `syncEnabled`、把 `skillsDir` 指向一个已初始化的仓库即可，新建 skill 无需单独建 repo。
- **可选（per-skill）**：每个 skill 一个独立远端，适合 skill 含敏感/经营数据、要单独分享或单独控权的场景。为单个 skill 建仓的序列：

```bash
cd <skillsDir>/<skill-name>
printf '.DS_Store\n**/.DS_Store\n' > .gitignore
gh repo create <your-owner>/<skill-name> --private   # <your-owner> 换成你自己的 GitHub 账号
git init -b main
git remote add origin git@github.com:<your-owner>/<skill-name>.git
git add -A && git commit -m "init <skill-name> skill"
git push -u origin main                               # -u 设 upstream，后续同步层才能 push
```

**红线确认**：`gh repo create` + `push` 命中「公开发布/推送」红线，执行前须向用户确认仓库名与 public/private。

---

## 创建 skill

### 捕获意图

先理解用户想要什么。当前对话可能已经包含了用户想固化的工作流（比如他说"把这个做成 skill"）。如果有，先从对话历史里提取：用了什么工具、步骤顺序、用户纠正了什么、输入输出格式。然后让用户补充缺口并确认。

需要确认的四个问题：
1. 这个 skill 要让 Claude 做什么？
2. 什么时候应该触发？（用户说什么词/在什么场景）
3. 预期输出格式是什么？
4. 需要设置测试用例验证 skill 是否正常工作吗？（有客观可验证输出的 skill 适合测试用例；有主观输出的通常不需要）

### 访谈和调研

主动追问边界情况、输入输出格式、示例文件、成功标准、依赖项。

检查可用的 MCP——如果对调研有帮助（搜索文档、查找类似 skill），通过子 Agent 并行调研。在拿到足够信息之前，先不要写测试 prompt。

### 写 SKILL.md

基于上述信息，按「Skill 创作规范」填写：
- frontmatter（name / description / tags）
- 目录文件说明（第一节）
- 核心工作流
- 最后一步：raw/ 归档 + wiki.md 更新
- 创建 meta.md

同时初始化 skill 目录结构：
```bash
mkdir -p ~/.claude/skills/<skill-name>/raw
touch ~/.claude/skills/<skill-name>/wiki.md
```

用对应 skill 的内容填充 wiki.md 初始模板。

### Skill 结构规范

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description, tags required)
│   └── Markdown instructions
├── meta.md (required)
├── wiki.md (required, LLM-maintained)
├── raw/ (required, execution archives)
└── Bundled Resources (optional)
    ├── scripts/    - 确定性/重复性任务的可执行代码
    ├── references/ - 按需加载到上下文的文档
    └── assets/     - 输出中使用的文件（模板、图标等）
```

**三级加载系统：**
1. **元数据**（name + description）— 始终在上下文中（~100 词）
2. **SKILL.md 正文** — skill 触发时在上下文中（理想 <500 行）
3. **捆绑资源** — 按需加载（无限制，脚本可以不加载直接执行）

**关键模式：**
- SKILL.md 保持在 500 行以内；接近上限时增加层级并明确指向下一级文件的指针
- 从 SKILL.md 中清晰引用文件，并说明何时读取
- 大型引用文件（>300 行）包含目录

---

## 运行和评估测试用例

这部分是一个连续序列——不要中途停下。不要使用 `/skill-test` 或其他测试 skill。

把结果放在 `<skill-name>-workspace/` 里，与 skill 目录并列。工作区内按迭代组织结果（`iteration-1/`、`iteration-2/` 等），每个测试用例在其中有一个目录（`eval-0/`、`eval-1/` 等）。不要提前创建所有目录——用到时再创建。

### 第一步：同一 turn 内生成所有运行（with-skill 和 baseline）

对每个测试用例，在同一 turn 内生成两个子 Agent——一个有 skill，一个没有。重要：不要先生成 with-skill 运行再回来生成 baseline。同时启动所有运行，让它们同时完成。

**With-skill 运行：**
```
执行此任务：
- Skill 路径：<path-to-skill>
- 任务：<eval prompt>
- 输入文件：<eval files if any，或 "none">
- 将输出保存到：<workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- 要保存的输出：<用户关心的内容>
```

**Baseline 运行**（相同 prompt，但 baseline 取决于情境）：
- **创建新 skill**：完全没有 skill。相同 prompt，无 skill 路径，保存到 `without_skill/outputs/`。
- **改进现有 skill**：旧版本。编辑前先快照（`cp -r <skill-path> <workspace>/skill-snapshot/`），然后将 baseline 子 Agent 指向快照。保存到 `old_skill/outputs/`。

为每个测试用例写 `eval_metadata.json`（assertions 现在可以为空）。给每个 eval 一个基于测试内容的描述性名称——不只是 "eval-0"。

### 第二步：运行期间起草 assertions

不要只是等运行完成——这段时间可以用来起草每个测试用例的定量 assertions 并向用户解释。

好的 assertions 是客观可验证的，名称具有描述性。主观性 skill（写作风格、设计质量）更适合定性评估——不要强行给主观内容加 assertions。

### 第三步：运行完成后捕获时间数据

每个子 Agent 任务完成时，将时间数据保存到运行目录的 `timing.json`：
```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

### 第四步：评分、聚合、启动查看器

所有运行完成后：

1. **评分** — 生成 grader 子 Agent（读 `agents/grader.md`），评估每个 assertion。将结果保存到每个运行目录的 `grading.json`。grading.json 的 expectations 数组必须使用 `text`、`passed`、`evidence` 字段。

2. **聚合到 benchmark** — 从 skill-creator 目录运行：
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```

3. **分析师过场** — 读取 benchmark 数据，找出聚合统计可能隐藏的模式。参见 `agents/analyzer.md`。

4. **启动查看器：**
   ```bash
   nohup python "${CLAUDE_PLUGIN_ROOT}/skills/skill-creator/eval-viewer/generate_review.py" \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```

5. 告知用户打开了结果查看器，让他们查看后回来反馈。

### 第五步：读取反馈

用户说完成后，读取 `feedback.json`。空反馈意味着用户认为没问题。重点改进用户有具体意见的测试用例。

完成后关闭查看器服务器：
```bash
kill $VIEWER_PID 2>/dev/null
```

---

## 改进 skill

这是循环的核心。你已经运行了测试用例，用户已经查看了结果，现在基于他们的反馈让 skill 更好。

**改进思路：**
1. **从反馈中泛化。** 目标是创建能在各种 prompt 下工作的 skill，不只针对这几个测试用例。
2. **保持 prompt 精简。** 删除没有贡献的内容。读 transcript，不只是最终输出。
3. **解释为什么。** 尽量解释你要求模型做某事的原因。如果发现自己在写全大写的 ALWAYS 或 NEVER，那是黄旗。
4. **找跨测试用例的重复工作。** 如果所有测试用例都独立写了相似的辅助脚本，考虑把它打包进 skill。

**迭代循环：**
1. 应用改进
2. 将所有测试用例重新跑到 `iteration-<N+1>/` 目录
3. 用 `--previous-workspace` 指向上一次迭代启动查看器
4. 等用户查看并反馈
5. 读取新反馈，再次改进，循环

持续到：用户满意、反馈全为空、或不再有实质性进展。

**改进后同步更新：**
- 「目录文件说明」表格（如有新增文件）
- `raw/` 归档 + `wiki.md`（记录本次优化的核心决策）

---

## 高级：盲测对比

需要在两个版本间做更严格对比时，使用盲测系统。参见 `agents/comparator.md` 和 `agents/analyzer.md`。这是可选的，需要子 Agent，大多数用户不需要。

---

## Description 优化

description 字段是决定 Claude 是否调用 skill 的主要机制。创建或改进 skill 后，提供优化 description 以提高触发准确性。

优化后的 description 必须仍符合「Skill 创作规范」的格式（中英双语触发词 + 确定性/非确定性触发说明）。

### 第一步：生成触发评估查询

创建 20 个评估查询——should-trigger 和 should-not-trigger 各半。保存为 JSON：
```json
[
  {"query": "用户的 prompt", "should_trigger": true},
  {"query": "另一个 prompt", "should_trigger": false}
]
```

查询必须真实且具体，有足够的细节（文件路径、个人背景、列名、公司名等）。避免过于简单的查询。

### 第二步：与用户确认

1. 读取 `assets/eval_review.html` 模板
2. 替换占位符并写入临时文件，打开：`open /tmp/eval_review_<skill-name>.html`
3. 用户可编辑查询、切换 should-trigger、添加/删除条目，然后点击 "Export Eval Set"
4. 文件下载到 `~/Downloads/eval_set.json`

### 第三步：运行优化循环

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id> \
  --max-iterations 5 \
  --verbose
```

用系统 prompt 中的模型 ID，确保触发测试匹配用户实际体验。

### 第四步：应用结果

取 `best_description` 更新 SKILL.md frontmatter，并调整为「Skill 创作规范」格式（中英双语）。向用户展示前后对比和评分。

---

## 打包（仅当 `present_files` 工具可用时）

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

---

## 完成后：归档到 raw/ 并 compile wiki

skill 创建/优化完成后执行：

1. 在 `${CLAUDE_PLUGIN_DATA}/skill-creator/raw/YYYY-MM-DD_<skill-name>/` 下创建（用插件数据目录，跨更新保留；不要写进 `${CLAUDE_PLUGIN_ROOT}`，那里更新即丢）：
   - `input.md`：创建/优化的 skill 名称、用户需求摘要、迭代次数
   - `summary.md`：最终 skill 的核心设计决策（3-5条）

2. 读取 `${CLAUDE_PLUGIN_DATA}/skill-creator/wiki.md` 并更新：
   - 索引表追加本次记录（日期 / skill 名 / 操作类型 / 核心变化）
   - wiki.md 由 LLM 维护，不要手动编辑

---

## 环境适配

### Claude.ai
- 无子 Agent：测试用例顺序执行，跳过 baseline 运行
- 无浏览器：直接在对话中展示结果，让用户内联反馈
- 跳过定量 benchmark
- 跳过 description 优化（需要 `claude` CLI）

### Cowork
- 有子 Agent，主流程正常工作
- 无浏览器：`generate_review.py` 用 `--static <output_path>` 生成静态 HTML
- "Submit All Reviews" 下载 `feedback.json` 文件
- 在完全完成 skill 且用户认可后再运行 description 优化
- **重要**：先生成 eval 查看器让用户看，再自己评估修改

### 更新现有 skill
- 保留原始名称（目录名和 name frontmatter）
- 如路径只读，先复制到 `/tmp/<skill-name>/` 再编辑

---

## 参考文件

- `agents/grader.md` — 评估 assertions 的子 Agent 指令
- `agents/comparator.md` — 盲测 A/B 对比的子 Agent 指令
- `agents/analyzer.md` — 分析某版本为什么胜出的子 Agent 指令
- `references/schemas.md` — evals.json、grading.json 等 JSON 结构

---

核心循环再强调一次：

- 明确 skill 要做什么
- 按「Skill 创作规范」写草稿（含 raw/ + wiki.md 机制）
- 在测试 prompt 上运行 claude-with-skill
- 和用户一起评估（**先生成查看器让用户看，再自己改**）
- 循环直到满意
- 优化 description 触发准确性（中英双语格式）
- 归档到 raw/ 并更新 wiki.md
