#!/usr/bin/env python3
"""
skill-autopush.py — PostToolUse(Write|Edit) hook worker.

When the user edits a file inside their skills dir and sync is enabled, commit
it in the nearest git repo and push if an upstream is configured. Off by default.
Reads the hook payload (JSON) from stdin; emits a hookSpecificOutput note.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synclib as S


def emit(msg):
    if msg:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse", "additionalContext": msg}}))


def main():
    if not S.sync_enabled():
        sys.exit(0)                       # opt-in only; silent no-op otherwise
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    path = (data.get("tool_input", {}) or {}).get("file_path", "")
    if not path:
        sys.exit(0)

    root = S.skills_dir()
    if not os.path.abspath(path).startswith(root + os.sep):
        sys.exit(0)                       # only touch files under the skills dir
    repo = S.find_repo(path, root)
    if not repo:
        sys.exit(0)                       # no git repo here; never auto-init

    env = S.build_env()
    try:
        S.git(repo, "add", "-A", env=env)
        if not S.git(repo, "status", "--porcelain", env=env).stdout.strip():
            sys.exit(0)
        rel = os.path.relpath(path, repo)
        c = S.git(repo, "commit", "-m", f"auto: update {rel}", env=env)
        if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
            raise RuntimeError(c.stderr or c.stdout)
        # push only if this branch has an upstream configured
        has_up = S.git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name",
                       "@{u}", env=env).returncode == 0
        if has_up:
            S.git(repo, "pull", "--rebase", env=env, timeout=120)
            pr = S.git(repo, "push", env=env, timeout=120)
            if pr.returncode != 0:
                raise RuntimeError((pr.stderr or pr.stdout).strip()[:200])
            emit(f"[skill-sync] {os.path.basename(repo)} 已 commit+push")
        else:
            emit(f"[skill-sync] {os.path.basename(repo)} 已本地 commit（未配 upstream，未推）")
    except Exception as e:
        emit(f"[skill-sync ERROR] {os.path.basename(repo)}: {str(e)[:200]}")


if __name__ == "__main__":
    main()
