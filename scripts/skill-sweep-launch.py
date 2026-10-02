#!/usr/bin/env python3
"""
skill-sweep-launch.py — SessionStart hook entry (must be fast).
1) Surface the previous background sweep's one-line summary (then clear it).
2) Detach the real sweep worker to the background and return immediately, so it
   adds ~0 to session startup. Off by default (worker self-exits if not enabled).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _synclib as S

WORKER = os.path.join(HERE, "skill-sweep.py")


def main():
    if not S.sync_enabled():
        sys.exit(0)                       # opt-in only
    data = S.data_dir()
    last = os.path.join(data, "sweep.last")
    log = os.path.join(data, "sweep.log")

    msg = ""
    try:
        if os.path.exists(last):
            with open(last) as f:
                msg = f.read().strip()
            with open(last, "w") as f:
                f.write("")               # clear after surfacing
    except Exception:
        pass

    try:
        with open(log, "a") as lf:
            subprocess.Popen([sys.executable, WORKER],
                             stdout=lf, stderr=lf,
                             start_new_session=True,
                             cwd=os.path.expanduser("~"))
    except Exception as e:
        msg = (msg + " | " if msg else "") + f"[skill-sweep] worker 启动失败: {e}"

    if msg:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": msg}}))


if __name__ == "__main__":
    main()
