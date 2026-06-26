#!/usr/bin/env python3
"""
Remote Job Hunter - Instant search entry point.
Runs the full pipeline and prints results to console.
Designed for agent direct invocation.
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def main():
    cmd = [sys.executable, str(SCRIPT_DIR / "daily_scheduler.py"), "--dry-run"]
    if "--max-results" in sys.argv:
        idx = sys.argv.index("--max-results")
        if idx + 1 < len(sys.argv):
            cmd.extend(["--max-results", sys.argv[idx + 1]])
    elif "-n" in sys.argv:
        idx = sys.argv.index("-n")
        if idx + 1 < len(sys.argv):
            cmd.extend(["--max-results", sys.argv[idx + 1]])

    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
