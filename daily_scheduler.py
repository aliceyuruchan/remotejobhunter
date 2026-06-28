#!/usr/bin/env python3
"""Remote Job Hunter - daily scheduler with agent-friendly CLI."""
import argparse
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

def run_bool(cmd, stdin_data=None, timeout=120, env=None):
    payload = json.dumps(stdin_data, ensure_ascii=False) if stdin_data is not None else None
    result = subprocess.run(cmd, input=payload, capture_output=True, text=True, timeout=timeout, env=env)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode != 0:
        print("[ERROR] Command failed: %s" % " ".join(map(str, cmd)), file=sys.stderr)
        return False
    return True

def print_matches_console(data, max_results=10):
    """Print job matches in a clean console format for agent to show user."""
    matches = data.get("matches", [])
    closed = data.get("closed_filtered", 0)
    total_searched = data.get("total_searched", 0)

    print("\n" + "=" * 60)
    print("  REMOTE JOB HUNTER - RESULTS")
    print("=" * 60)
    print(f"  Searched: {total_searched} jobs | Active matches: {len(matches)} | Closed filtered: {closed}")
    print("-" * 60)

    if not matches:
        print("  No matching jobs found today.")
        print("=" * 60)
        return

    for i, job in enumerate(matches[:max_results], 1):
        score = job.get("match_score", job.get("score", 0))
        title = job.get("title", "Untitled")
        company = job.get("company", "Unknown")
        platform = job.get("platform", job.get("source", ""))
        remote_type = job.get("remote_type", "")
        url = job.get("url", "")
        details = job.get("details", {})
        skills_hit = ", ".join(details.get("skill_hits", []))[:60]

        print(f"\n  #{i} [{score} pts] {title}")
        print(f"      Company:  {company}")
        if platform:
            print(f"      Platform: {platform}")
        if remote_type:
            print(f"      Remote:   {remote_type}")
        if skills_hit:
            print(f"      Skills:   {skills_hit}")
        if url:
            print(f"      Link:     {url}")

    print("\n" + "=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Remote Job Hunter Daily Scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Run full pipeline but do not send email; print results to console")
    parser.add_argument("--no-email", action="store_true", help="Run pipeline but skip email sending")
    parser.add_argument("--max-results", type=int, default=10, help="Max results to show in console output (default: 10)")
    parser.add_argument("--output-json", type=str, help="Also save verified results to a JSON file")
    args = parser.parse_args()

    # Check config exists
    if not CONFIG_PATH.exists():
        print("[ERROR] config.json not found. Run: python3 setup.py", file=sys.stderr)
        sys.exit(1)

    env = dict(os.environ)
    env["JOB_HUNTER_CONFIG"] = str(CONFIG_PATH)
    env["JOB_HUNTER_HISTORY"] = str(HISTORY_PATH)

    print("[SCHEDULER] Starting job search...", file=sys.stderr)
    search_data = run_json([sys.executable, str(SEARCH_SCRIPT)], timeout=420, env=env)

    print("[SCHEDULER] Matching jobs...", file=sys.stderr)
    matches_data = run_json([sys.executable, str(MATCH_SCRIPT)], stdin_data=search_data, timeout=120, env=env)

    print("[SCHEDULER] Verifying job links...", file=sys.stderr)
    verified_data = run_json([sys.executable, str(VERIFY_SCRIPT)], stdin_data=matches_data, timeout=240, env=env)

    active = len(verified_data.get("matches", []))
    closed = verified_data.get("closed_filtered", 0)

    # Save to JSON if requested
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(verified_data, f, ensure_ascii=False, indent=2)
        print(f"[SCHEDULER] Results saved to {args.output_json}", file=sys.stderr)

    # Console output for dry-run or when explicitly requested
    if args.dry_run:
        print_matches_console(verified_data, max_results=args.max_results)
        print(f"[SCHEDULER] Dry run complete. {active} active matches ({closed} closed filtered). Email not sent.", file=sys.stderr)
        return

    if active == 0:
        print("[SCHEDULER] Done. 0 active matches (%d closed filtered out). Email skipped." % closed, file=sys.stderr)
        return

    if args.no_email:
        print_matches_console(verified_data, max_results=args.max_results)
        print(f"[SCHEDULER] Done. {active} active matches ({closed} closed filtered out). Email skipped by --no-email.", file=sys.stderr)
        return

    print("[SCHEDULER] Sending email...", file=sys.stderr)
    email_ok = run_bool([sys.executable, str(EMAIL_SCRIPT)], stdin_data=verified_data, timeout=120, env=env)

    print("[SCHEDULER] Done. %d active matches (%d closed filtered out). Email: %s" % (active, closed, "ok" if email_ok else "failed"), file=sys.stderr)

if __name__ == "__main__":
    main()
