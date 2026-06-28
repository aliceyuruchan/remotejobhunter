#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const args = process.argv.slice(2);
const command = args[0] || "run";

const commands = {
  setup: ["setup.py"],
  run: ["daily_scheduler.py"],
  now: ["run_now.py"],
  search: ["scripts/search_jobs.py"],
  match: ["scripts/match_jobs.py"],
  verify: ["scripts/verify_jobs.py"],
  email: ["scripts/send_email.py"]
};

function printHelp() {
  console.log(`Remote Job Hunter

Usage:
  remote-job-hunter setup        Create config.json interactively
  remote-job-hunter run          Run search -> match -> verify -> email
  remote-job-hunter now          Run once without email and print matches
  remote-job-hunter search       Run only the search stage
  remote-job-hunter match        Run only the match stage, reading JSON from stdin
  remote-job-hunter verify       Run only the verification stage, reading JSON from stdin
  remote-job-hunter email        Send/save report, reading matched JSON from stdin
  remote-job-hunter where        Print the installed package path
  remote-job-hunter --help       Show this help

Environment:
  JOB_HUNTER_CONFIG              Path to config.json
  JOB_HUNTER_HISTORY             Path to history.json
  JOB_HUNTER_REPORTS_DIR         Path to reports directory
  JOB_HUNTER_COVER_LETTERS_DIR   Path to cover letters directory
`);
}

if (command === "--help" || command === "-h" || command === "help") {
  printHelp();
  process.exit(0);
}

if (command === "where") {
  console.log(root);
  process.exit(0);
}

const script = commands[command];
if (!script) {
  console.error(`Unknown command: ${command}`);
  printHelp();
  process.exit(1);
}

const python = process.env.PYTHON || "python3";
const extraArgs = args.slice(1);
const result = spawnSync(python, [join(root, script[0]), ...extraArgs], {
  cwd: root,
  stdio: "inherit",
  env: process.env
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
