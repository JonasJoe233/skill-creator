# Skill Creator (魔改版)

基于社区开源 skill-creator 深度定制，改造为带知识管理、自动化评测、触发精度优化、且与 Obsidian 笔记体系耦合的 skill 全生命周期工具。

## 与原版的核心差异

### 1. Jonas Skill 规范

所有通过此工具创建/修改的 skill 必须遵守统一结构约定：

- **frontmatter**：中英双语触发词 + 确定性/非确定性触发分级 + 具体确认话术
- **目录文件说明**：正文第一节必须是 Obsidian `[[wiki-link]]` 格式的文件清单，文件增删时同步更新
- **tags**：必须与目录名一致

### 2. 知识管理层

原版没有执行历史机制。本版加了三层持久化：

| 机制 | 作用 |
|------|------|
| `raw/YYYY-MM-DD/` | 每次执行归档（input.md + summary.md + 输出副本） |
| `wiki.md` | LLM 自维护的跨次索引和规律积累 |
| `meta.md` | 声明 topics / product_scope / data 字段，供 `_discover.py` 自动计算跨 skill 关联 |

### 3. Description 优化工具链

自建了一套 description 触发精度优化系统：

- **`scripts/run_eval.py`** — 通过 `claude -p` 子进程实际调用 skill，stream-json 解析提前检测是否触发
- **`scripts/improve_description.py`** — 调 claude 子进程改写 description，超 1024 字自动缩短
- **`scripts/run_loop.py`** — 编排评估+改进循环，train/test split（默认 40% holdout 防过拟合），满分提前退出
- **`scripts/generate_report.py`** — 生成带自动刷新的 HTML 报告，可视化训练集/测试集得分
- **`assets/eval_review.html`** — 浏览器 UI 编辑评估用例集，导出 JSON

### 4. Eval 查看器

- `eval-viewer/viewer.html` — 单页应用，键盘导航、inline 渲染 PDF/图片/xlsx（SheetJS）、benchmark 详情、跨迭代对比
- `eval-viewer/generate_review.py` — 零依赖 HTTP 服务器，每次刷新重生成 HTML，支持 `--static` 离线模式
- 反馈写入 `feedback.json`，主流程读取后决定是否继续迭代

### 5. 本地生态集成

- 假定 `~/.claude/skills/` 为根目录
- 需要 `claude` CLI（子进程跑 eval）和 `gh` CLI（建 GitHub 仓库）
- 与 `_discover.py` 配合实现跨 skill 关联发现
- Obsidian wiki 链接贯穿所有文件
- 适配三种运行环境（Claude.ai / Cowork / 本地 CLI），各有降级策略

## 目录结构

```
skill-creator/
├── SKILL.md                  # 主文件，完整工作流定义
├── meta.md                   # 关联声明
├── wiki.md                   # 执行索引（LLM 维护）
├── agents/
│   ├── analyzer.md           # 分析 benchmark 结果的子 Agent 指令
│   ├── comparator.md         # 盲测 A/B 对比的子 Agent 指令
│   └── grader.md             # 评估 assertions 的子 Agent 指令
├── assets/
│   └── eval_review.html      # Description 优化评测用例编辑 UI
├── eval-viewer/
│   ├── generate_review.py    # Eval 查看器 HTTP 服务
│   └── viewer.html           # Eval 查看器前端
├── references/
│   └── schemas.md            # evals.json / grading.json 结构定义
└── scripts/
    ├── __init__.py
    ├── aggregate_benchmark.py
    ├── discover.py            # 跨 skill 关联发现（原 _discover.py）
    ├── generate_report.py
    ├── improve_description.py
    ├── package_skill.py
    ├── quick_validate.py
    ├── run_eval.py
    ├── run_loop.py
    └── utils.py
```
