#!/usr/bin/env python3
"""Remote Job Hunter - daily scheduler."""
import json
import subprocess
import sys
from pathlib import Path
import os

# Get the directory where this script is located
WORK_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = WORK_DIR / "scripts"

# Config and history paths from environment or defaults
CONFIG_PATH = Path(os.environ.get("JOB_HUNTER_CONFIG", WORK_DIR / "config.json"))
HISTORY_PATH = Path(os.environ.get("JOB_HUNTER_HISTORY", WORK_DIR / "history.json"))

# Script paths
SEARCH_SCRIPT = SCRIPTS_DIR / "search_jobs.py"
MATCH_SCRIPT = SCRIPTS_DIR / "match_jobs.py"
VERIFY_SCRIPT = SCRIPTS_DIR / "verify_jobs.py"
EMAIL_SCRIPT = SCRIPTS_DIR / "send_email.py"

def run_json(cmd, stdin_data=None, timeout=240, env=None):
    payload = json.dumps(stdin_data, ensure_ascii=False) if stdin_data is not None else None
    result = subprocess.run(cmd, input=payload, capture_output=True, text=True, timeout=timeout, env=env)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0:
        raise RuntimeError("Command failed: %s\n%s" % (" ".join(map(str, cmd)), result.stderr))
    return json.loads(result.stdout)

def run_bool(cmd, stdin_data=None, timeout=120):
    payload = json.dumps(stdin_data, ensure_ascii=False) if stdin_data is not None else None
    result = subprocess.run(cmd, input=payload, capture_output=True, text=True, timeout=timeout)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0:
        print("[ERROR] Command failed: %s" % " ".join(map(str, cmd)), file=sys.stderr)
        return False
    return True

def main():
    env = dict(os.environ)
    env["JOB_HUNTER_CONFIG"] = str(CONFIG_PATH)
    env["JOB_HUNTER_HISTORY"] = str(HISTORY_PATH)

    print("[SCHEDULER] Starting job search...", file=sys.stderr)
    search_data = run_json([sys.executable, str(SEARCH_SCRIPT)], timeout=420, env=env)

    print("[SCHEDULER] Matching jobs...", file=sys.stderr)
    matches_data = run_json([sys.executable, str(MATCH_SCRIPT)], stdin_data=search_data, timeout=120)

    print("[SCHEDULER] Verifying job links...", file=sys.stderr)
    verified_data = run_json([sys.executable, str(VERIFY_SCRIPT)], stdin_data=matches_data, timeout=240)

    active = len(verified_data.get("matches", []))
    closed = verified_data.get("closed_filtered", 0)
    if active == 0:
        print("[SCHEDULER] Done. 0 active matches (%d closed filtered out). Email skipped." % closed, file=sys.stderr)
        return

    print("[SCHEDULER] Sending email...", file=sys.stderr)
    email_ok = run_bool([sys.executable, str(EMAIL_SCRIPT)], stdin_data=verified_data, timeout=120)

    print("[SCHEDULER] Done. %d active matches (%d closed filtered out). Email: %s" % (active, closed, "ok" if email_ok else "failed"), file=sys.stderr)

if __name__ == "__main__":
    main()
