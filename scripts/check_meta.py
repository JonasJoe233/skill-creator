#!/usr/bin/env python3
"""
meta.md 质量检查器 —— 验收 skill 关联声明的唯一判卷标准。

用法: python3 ~/.claude/skills/skill-creator/scripts/check_meta.py
退出码 0 = 全过；非 0 = 有项不达标（每项都打印原因）。

三项检查：
  1 VISIBLE   : discover.py 的 load_meta 能读到的 skill 数，必须 = 真实 skill 目录数
  2 ORPHAN    : 关联数为 0 的 skill 数，必须 = 0
  3 GENERIC   : 泛词命中数，必须 ≤ BASELINE_GENERIC（防止靠塞泛词刷关联数）
"""
import os
import subprocess
import sys

import yaml

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DISCOVER = os.path.join(SKILLS_DIR, "_discover.py")

# 2026-08-04 实测：arch-diagram/data_consumes:文档、hv-analysis/topics:报告、
# writing-zh/topics:报告 —— 存量 3 条，本次不清理，只要求不新增。
BASELINE_GENERIC = 3

BAN = {
    "工具", "文档", "数据", "文件", "分析", "报告", "内容", "信息", "处理", "生成",
    "通用", "输出", "输入", "自动化", "效率", "优化", "任务", "项目", "系统", "功能",
    "AI", "agent", "Agent", "skill", "Skill", "LLM", "模型",
    "tool", "tools", "doc", "docs", "data", "file", "files", "report", "content",
    "output", "input", "general", "misc", "utility", "all",
}
FIELDS = ("topics", "product_scope", "data_produces", "data_consumes")


def skill_dirs():
    for d in sorted(os.listdir(SKILLS_DIR)):
        p = os.path.join(SKILLS_DIR, d)
        if os.path.isdir(p) and not d.startswith(("_", ".")):
            yield d, p


def load_meta(path):
    """与 discover.py 的 load_meta 同逻辑：任一环失败即 None（= 图谱看不见）。"""
    mp = os.path.join(path, "meta.md")
    if not os.path.exists(mp):
        return None
    content = open(mp).read()
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except Exception:
        return None


def main():
    dirs = list(skill_dirs())
    total = len(dirs)

    invisible, generic, orphan = [], [], []

    for name, path in dirs:
        meta = load_meta(path)
        if not meta or not meta.get("topics"):
            invisible.append(name)
            continue
        for field in FIELDS:
            for v in (meta.get(field) or []):
                if str(v).strip() in BAN:
                    generic.append(f"{name}/{field}: {v}")

        out = subprocess.run([sys.executable, DISCOVER, name],
                             capture_output=True, text=True).stdout
        if "relevance=" not in out:
            orphan.append(name)

    fail = False
    print(f"[1] VISIBLE  {total - len(invisible)}/{total}")
    for n in invisible:
        print(f"      INVISIBLE: {n}")
    if invisible:
        fail = True

    print(f"[2] ORPHAN   {len(orphan)} (需 = 0)")
    for n in orphan:
        print(f"      ORPHAN: {n}")
    if orphan:
        fail = True

    print(f"[3] GENERIC  {len(generic)} (需 <= {BASELINE_GENERIC})")
    for g in generic:
        print(f"      GENERIC: {g}")
    if len(generic) > BASELINE_GENERIC:
        fail = True

    print("RESULT:", "FAIL" if fail else "PASS")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
