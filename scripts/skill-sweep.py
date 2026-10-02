#!/usr/bin/env python3
"""
skill-sweep.py — SessionStart background worker (runs detached; off by default).

Catches skill changes that the Write/Edit hook never saw — e.g. files produced
by scripts (Bash), which don't trigger PostToolUse. Conservative rule: only
auto-commit changes under a skill's `raw/` dir; anything outside raw/ is reported
only. Supports single-repo (skillsDir is a git repo) and per-skill (each subdir
is a repo). Logs to the plugin data dir.
"""
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synclib as S


def repos_to_scan(root):
    if os.path.isdir(os.path.join(root, ".git")):
        return [root]                                   # single-repo
    out = []
    if os.path.isdir(root):
        for e in sorted(os.scandir(root), key=lambda x: x.name):
            if e.is_dir() and os.path.isdir(os.path.join(e.path, ".git")):
                out.append(e.path)                      # per-skill
    return out


def main():
    if not S.sync_enabled():
        return
    root = S.skills_dir()
    env = S.build_env()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines, acted, reported = [f"=== sweep {ts} ==="], [], []

    for repo in repos_to_scan(root):
        name = os.path.basename(repo)
        st = S.git(repo, "status", "--porcelain", env=env)
        if st.returncode != 0:
            lines.append(f"[{name}] status 失败: {st.stderr.strip()}")
            continue
        raw_changes, outside = [], []
        for l in [x for x in st.stdout.splitlines() if x.strip()]:
            p = l[3:].strip()
            if p.startswith('"'):
                p = p[1:-1]
            (raw_changes if (p.startswith("raw/") or "/raw/" in p) else outside).append(p)

        did_commit = pushed = False
        if raw_changes:
            # stage only raw/ dirs (covers single-repo nested skills too)
            S.git(repo, "add", "--", *sorted({c.split("raw/")[0] + "raw/" for c in raw_changes}), env=env)
            if S.git(repo, "diff", "--cached", "--name-only", env=env).stdout.strip():
                c = S.git(repo, "commit", "-m", f"sweep: auto-archive raw/ ({ts})", env=env)
                did_commit = c.returncode == 0
                if not did_commit:
                    lines.append(f"[{name}] commit 失败: {(c.stderr or c.stdout).strip()[:200]}")

        up = S.git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", env=env)
        if up.returncode == 0:
            ah = S.git(repo, "rev-list", "--count", "@{u}..HEAD", env=env)
            if ah.stdout.strip() not in ("", "0"):
                p = S.git(repo, "push", env=env, timeout=120)
                pushed = p.returncode == 0
                if not pushed:
                    lines.append(f"[{name}] push 失败: {(p.stderr or p.stdout).strip()[:200]}")

        if did_commit or pushed:
            acted.append(f"{name}(+{len(raw_changes)}raw,push={'y' if pushed else 'n'})")
        if outside:
            reported.append(f"{name}: raw/外 {len(outside)} 项")
            lines.append(f"[{name}] ⚠ raw/外改动仅报告: {outside[:6]}")

    if not acted and not reported:
        lines.append("全部 synced，无操作")
    try:
        with open(os.path.join(S.data_dir(), "sweep.log"), "a") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
    summary = ""
    if acted:
        summary = f"[skill-sweep] 已归档/补推 {len(acted)} 个: " + "; ".join(acted)
    if reported:
        summary += (" | 待处理 " if summary else "[skill-sweep] 待处理 ") + "; ".join(reported)
    try:
        with open(os.path.join(S.data_dir(), "sweep.last"), "w") as f:
            f.write(summary)
    except Exception:
        pass


if __name__ == "__main__":
    main()
