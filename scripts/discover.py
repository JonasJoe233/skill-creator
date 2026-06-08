#!/usr/bin/env python3
"""
Usage: python -m scripts.discover <skill-name>
   or: python scripts/discover.py <skill-name>
Scans all meta.md files, computes topic overlap, outputs related skills and their wiki paths.
"""
import sys
import os
import glob
import yaml

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# When run from ~/.claude/skills/skill-creator/, go up one level to ~/.claude/skills/
SKILLS_DIR = os.path.dirname(SKILLS_DIR)

def load_meta(skill_dir):
    meta_path = os.path.join(skill_dir, "meta.md")
    if not os.path.exists(meta_path):
        return None
    with open(meta_path) as f:
        content = f.read()
    # Extract YAML frontmatter
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except Exception:
        return None

def find_context_files(skill_dir):
    """Return wiki.md (root level) and raw/**/*.md files if they exist."""
    paths = []
    wiki = os.path.join(skill_dir, "wiki.md")
    if os.path.isfile(wiki):
        paths.append(wiki)
    raw_dir = os.path.join(skill_dir, "raw")
    if os.path.isdir(raw_dir):
        for f in sorted(glob.glob(os.path.join(raw_dir, "**", "*.md"), recursive=True)):
            paths.append(f)
    return paths

def compute_score(meta_a, meta_b):
    """Score relevance between two skills based on topic/scope/data overlap."""
    score = 0
    topics_a = set(meta_a.get("topics", []))
    topics_b = set(meta_b.get("topics", []))
    score += len(topics_a & topics_b) * 2

    scope_a = set(meta_a.get("product_scope", []))
    scope_b = set(meta_b.get("product_scope", []))
    score += len(scope_a & scope_b) * 3

    # Data chain: a produces what b consumes, or vice versa
    produces_a = set(meta_a.get("data_produces", []))
    consumes_b = set(meta_b.get("data_consumes", []))
    score += len(produces_a & consumes_b) * 4

    produces_b = set(meta_b.get("data_produces", []))
    consumes_a = set(meta_a.get("data_consumes", []))
    score += len(produces_b & consumes_a) * 4

    return score

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.discover <skill-name>")
        sys.exit(1)

    target = sys.argv[1]
    target_dir = os.path.join(SKILLS_DIR, target)
    target_meta = load_meta(target_dir)

    if not target_meta:
        print(f"No meta.md found for skill: {target}")
        sys.exit(1)

    results = []
    for entry in os.scandir(SKILLS_DIR):
        if not entry.is_dir() or entry.name.startswith("_") or entry.name == target:
            continue
        meta = load_meta(entry.path)
        if not meta:
            continue
        score = compute_score(target_meta, meta)
        if score > 0:
            context_files = find_context_files(entry.path)
            results.append((score, meta.get("skill", entry.name), context_files))

    results.sort(reverse=True)

    if not results:
        print(f"No related skills found for: {target}")
        return

    print(f"Related skills for [{target}] (sorted by relevance):\n")
    for score, skill_name, files in results:
        print(f"  [{skill_name}]  relevance={score}")
        if files:
            for f in files:
                print(f"    context: {f}")
        else:
            print(f"    context: (no wiki/raw files yet)")
    print()
    print("Suggested action: load the above context files before executing the current skill.")

if __name__ == "__main__":
    main()
