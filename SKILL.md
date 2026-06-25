---
name: remote-job-hunter
description: Automates daily remote job search, matching, verification, and email reports based on the user's resume. This skill should be used when the user asks to set up automated job hunting, search for remote jobs daily, or wants a tool that automatically finds and emails suitable remote job matches. Triggers on keywords like "job hunter", "automate job search", "daily job search", "remote job automation", or "set up job hunting".
agent_created: true
---

# Remote Job Hunter

Automated daily remote job search tool. Searches, matches, verifies, and emails suitable remote jobs based on the user's resume and preferences. Works for any career path — Software Engineer, Product Manager, Designer, Data Analyst, Marketing, etc.

## How to trigger this skill

Say something like:
- "帮我设置自动求职"
- "set up job hunter"
- "我想每天自动收到符合我简历的远程工作推荐"

## First Run: Interactive Setup

When the user triggers this skill, **first check if config.json exists in the skill directory**. The skill directory is the directory containing this SKILL.md.

**If `config.json` does NOT exist**, run the interactive setup flow below. Do NOT ask the user to run a terminal command — ask questions in chat and write `config.json` directly.

### Interactive Setup Flow (ask these in order)

1. **Welcome**: Tell the user you're setting up their daily remote job hunter.

2. **Resume**: Ask the user to paste their resume text (or a summary including: job title, years of experience, top skills, interests). Alternatively, ask for their target job title and skills directly.

3. **Extract profile**: From the resume text, extract:
   - `name`: user's name
   - `title`: target job title (e.g. "Product Designer", "Software Engineer")
   - `years_experience`: number of years
   - `skills`: list of key skills
   - `interests`: industry/domain interests
   - `dealbreakers`: things they don't want
   - `languages`: languages they speak
   - `portfolio_url`: (optional) portfolio or LinkedIn URL
   - `contact_email`: email for receiving daily reports

4. **Generate search keywords**: From `title` + `skills`, generate 8-12 search keywords. Show them to the user and ask if they want to customize.

5. **Location filter**: Ask the user: "Do you want to filter jobs by location?" and offer three modes:
   - `all` — no location filtering, show all jobs
   - `exclude_only` — only exclude specific keywords (e.g. "US only", "Canada only")
   - `include_global` — prioritize jobs that mention "worldwide", "global", "anywhere", "APAC", etc.
   Ask them to list any regions they want to exclude or include.

6. **Email config**: Ask for:
   - `contact_email`: email to receive daily reports
   - Ask if they want email reports. If yes, ask for Gmail address and App Password (guide them to generate one at https://myaccount.google.com/apppasswords). If they don't want email, set `enabled: false` in email config.

7. **Schedule**: Ask what time they want the daily report (e.g. "9:00"). This will be used to set up the automation.

8. **Write config.json**: Write all the above into `config.json` in the skill directory. Use `config.template.json` as reference for the structure. Set `search.platforms` to the default list (RemoteOK, Remotive, Greenhouse/Lever ATS sources).

9. **Confirm**: Show the user a summary of their config and ask if it looks correct.

### Config File Location

`config.json` must be written to the **skill directory** (the same directory as this SKILL.md).

Use the `config.template.json` file in this directory as a template. Replace all `{{PLACEHOLDER}}` values with the user's actual information.

## Daily Run

After setup is complete, the skill can be run in two ways:

### Option A: Manual run (for testing)
Ask the user: "Want to run a test search now?" If yes, run:
```bash
cd <skill-directory> && python3 daily_scheduler.py
```
This runs one full cycle: search → match → verify → email.

### Option B: Scheduled daily run
After setup, offer to create a WorkBuddy Automation that runs `daily_scheduler.py` every day at the user's preferred time. To do this:
1. Ask the user to confirm the time
2. Create an automation with `automation_update` tool, mode="create", with:
   - `name`: "daily-job-hunter"
   - `scheduleType`: "recurring"
   - `rrule`: "FREQ=DAILY;BYHOUR=<hour>;BYMINUTE=0" (convert user's time to 24h format)
   - `prompt`: "Run the remote job hunter: cd <skill-directory> && python3 daily_scheduler.py"
   - `cwds`: "<skill-directory>"

## File Structure

```
remote-job-hunter/
├── SKILL.md              # This file
├── config.template.json  # Template for config.json
├── setup.py              # Standalone setup script (alternative to interactive setup)
├── daily_scheduler.py    # Daily run entry point
├── scripts/
│   ├── search_jobs.py    # Search multiple sources
│   ├── match_jobs.py     # Score jobs against profile
│   ├── verify_jobs.py    # Verify jobs are still open
│   └── send_email.py     # Send email report
└── README.md             # User-facing documentation (bilingual EN/CN)
```

## Important Notes

- **No hardcoded profession**: Search keywords are generated from the user's `title` + `skills` in `config.json`, not hardcoded in scripts.
- **No forced region filtering**: Location filter mode and keywords are chosen by the user during setup. The script does not default-exclude any region.
- **Free sources only**: All search sources are free public APIs or company ATS pages. No paid job board subscriptions required.
- **7-day deduplication**: Jobs are tracked in `history.json` (created automatically in the skill directory) with a 7-day cooldown, not permanent exclusion.

## Troubleshooting

**No jobs found:**
- Check `config.json` → `search.keywords` — are they too specific?
- Try changing `location_filter.mode` to `"all"`
- Check `search.platforms` — are sources enabled?

**Email not received:**
- Check spam folder
- Verify SMTP config in `config.json`
- Run `python3 daily_scheduler.py` manually and check console output

**Want to reconfigure:**
Delete `config.json` and re-trigger this skill, or manually edit `config.json`.

## Resources

### scripts/
Executable Python scripts for each stage of the pipeline:
- `search_jobs.py` — multi-source job search
- `match_jobs.py` — resume-to-job matching and scoring
- `verify_jobs.py` — job status verification
- `send_email.py` — SMTP email sending

### references/
(None currently — the skill is self-contained in SKILL.md and scripts.)

### assets/
(None currently.)

---

**License**: MIT — free to use, modify, distribute.
