#!/usr/bin/env python3
"""
_synclib.py — shared helpers for the skill-creator plugin's sync layer.

Design rules (why it is built this way):
- The sync layer is OFF unless the user explicitly sets syncEnabled=true in the
  plugin config. Plugin hooks fire for everyone who installs the plugin, so it
  must never commit/push on someone's machine without opt-in.
- Credentials come from the GH_TOKEN environment variable first (cross-platform).
  A macOS Keychain item is an optional fallback. Tokens are never written into
  command arguments or logs — only passed through the subprocess environment.
- Git layout is auto-detected: the "nearest .git ancestor up to skillsDir"
  rule supports both single-repo (skillsDir is the repo) and per-skill
  (each skill dir is its own repo) without a strategy flag.
"""
import os
import subprocess


def _opt(key, default=""):
    """Read a plugin userConfig value from the CLAUDE_PLUGIN_OPTION_<KEY> env."""
    return os.environ.get(f"CLAUDE_PLUGIN_OPTION_{key.upper()}", default)


def sync_enabled():
    return _opt("SYNCENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def skills_dir():
    d = _opt("SKILLSDIR", "").strip() or "~/.claude/skills"
    return os.path.abspath(os.path.expanduser(d))


def _keychain_token(item):
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", item, "-w"],
            capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def build_env():
    """Subprocess env: resolve GH_TOKEN, proxy, and non-interactive git."""
    env = dict(os.environ)
    if not env.get("GH_TOKEN"):
        item = _opt("KEYCHAINITEM", "").strip()
        if item:
            tok = _keychain_token(item)
            if tok:
                env["GH_TOKEN"] = tok   # passed via env only, never logged/argv
    proxy = _opt("PROXY", "").strip()
    if proxy:
        env["http_proxy"] = env["https_proxy"] = proxy
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    return env


def data_dir():
    """Writable, update-stable dir for logs/state."""
    d = os.environ.get("CLAUDE_PLUGIN_DATA", "").strip()
    d = d or os.path.expanduser("~/.claude/skill-creator-sync")
    os.makedirs(d, exist_ok=True)
    return d


def git(repo, *args, env=None, timeout=60):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True,
                          env=env or os.environ, timeout=timeout)


def find_repo(path, root):
    """Nearest ancestor of `path` (up to and including `root`) that has .git."""
    path = os.path.abspath(path)
    root = os.path.abspath(root)
    cur = path if os.path.isdir(path) else os.path.dirname(path)
    while True:
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        if cur == root or len(cur) <= len(root):
            return None
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
