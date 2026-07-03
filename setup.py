#!/usr/bin/env python3
"""
Remote Job Hunter - Setup script.
Creates config.json from user input, resume PDF, or command-line arguments.
Supports interactive and non-interactive (quick) modes.
"""
import argparse
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path


def ask(question, default=None, required=True):
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    while True:
        value = input(prompt).strip()
        if not value:
            if default is not None:
                return default
            if not required:
                return ""
            print("This field is required.")
            continue
        return value


def ask_choice(question, options, default=0):
    """Ask user to choose from a numbered list."""
    print(f"\n{question}")
    for i, opt in enumerate(options):
        marker = " →" if i == default else "  "
        print(f"{marker} {i+1}. {opt}")
    while True:
        choice = input(f"Choose [1-{len(options)}, default {default+1}]: ").strip()
        if not choice:
            return default
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
            print(f"Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print("Please enter a number.")


def ask_location_filter():
    """Interactive location filter setup."""
    print("\n=== Location Filter ===")
    print("This controls which jobs are kept or filtered based on location.")
    
    mode_options = [
        "All — no location filtering, show every remote job",
        "Exclude only — only remove jobs matching your exclusion keywords, keep everything else",
        "Include global — prioritize jobs that mention your preferred regions (e.g. Worldwide, Asia)",
    ]
    mode_idx = ask_choice("How should location filtering work?", mode_options, default=0)
    mode_values = ["all", "exclude_only", "include_global"]
    mode = mode_values[mode_idx]
    
    if mode == "all":
        include_regions = []
        exclude_keywords = []
        print("\nNo location filtering applied. All remote jobs will be shown.")
    elif mode == "exclude_only":
        exclude_keywords = ask_list(
            "Keywords to EXCLUDE (jobs mentioning these will be removed)",
            default=["us only", "united states only", "us residents only", "authorized to work in the us"]
        )
        include_regions = []
        print(f"\nJobs mentioning: {', '.join(exclude_keywords)} will be filtered out.")
    elif mode == "include_global":
        include_regions = ask_list(
            "Preferred regions to INCLUDE (jobs mentioning these are prioritized)",
            default=["worldwide", "global", "anywhere", "international", "apac", "asia", "china", "contractor", "freelance"]
        )
        exclude_keywords = ask_list(
            "Keywords to EXCLUDE (jobs mentioning these will be removed)",
            default=["us only", "united states only", "us residents only"]
        )
        print(f"\nJobs with: {', '.join(include_regions)} will be prioritized.")
        print(f"Jobs with: {', '.join(exclude_keywords)} will be filtered out.")
    
    return {
        "mode": mode,
        "include_regions": include_regions,
        "exclude_keywords": exclude_keywords,
    }


def ask_int(question, default=None):
    while True:
        value = ask(question, str(default) if default is not None else None)
        try:
            return int(value)
        except ValueError:
            print("Please enter a number.")


def ask_list(question, default=None):
    """Ask for a comma-separated list."""
    default_str = ", ".join(default) if default else ""
    value = ask(question, default_str, required=False)
    if not value:
        return []
    return [item.strip() for item in value.split(",")]


def ask_yes_no(question, default="y"):
    value = ask(question, default=default, required=False).strip().lower()
    return value in ["y", "yes", "是", "好", "ok", "true", "1"]


def ask_time(question, default="12:00"):
    while True:
        value = ask(question, default=default)
        try:
            hour, minute = map(int, value.split(":"))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return "%02d:%02d" % (hour, minute)
        except Exception:
            pass
        print("Invalid time format. Use HH:MM, for example 12:00 or 09:30.")


def ask_resume_text():
    print("\n=== Step 1: Upload / Provide Resume ===")
    print("Paste a local resume file path, or type 'paste' to paste resume text.")
    print("Supported file types: PDF, TXT, MD. PDF parsing works best with pdfplumber or pdftotext installed.")
    while True:
        value = ask("Resume path or 'paste'", required=True)
        if value.lower() == "paste":
            print("\nPaste your resume text below. End with a blank line:")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            text = "\n".join(lines).strip()
            if text:
                return text, ""
            print("Resume text is empty. Please paste again or provide a file path.")
            continue
        path = Path(value).expanduser()
        if not path.exists():
            print("File not found. Please check the path, or type 'paste'.")
            continue
        if path.suffix.lower() == ".pdf":
            text = extract_text_from_pdf(str(path)).strip()
        else:
            try:
                text = path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception as e:
                print(f"Could not read file: {e}")
                continue
        if text:
            return text, str(path)
        print("Could not extract resume text. Try installing pdfplumber/pdftotext, or type 'paste'.")


def infer_job_titles(parsed, resume_text):
    text = resume_text.lower()
    suggestions = []
    if parsed.get("title"):
        suggestions.append(parsed["title"])
    title_rules = [
        ("Product Designer", ["product designer", "产品设计", "ux/ui", "figma", "design system"]),
        ("UX Designer", ["ux designer", "ux design", "user experience", "用户体验"]),
        ("UX Researcher", ["ux researcher", "ux research", "user research", "用户研究"]),
        ("Interaction Designer", ["interaction designer", "interaction design", "交互设计"]),
        ("UI Designer", ["ui designer", "ui design", "interface design", "界面设计"]),
        ("Product Manager", ["product manager", "product owner", "产品经理"]),
        ("Service Designer", ["service design", "service designer", "服务设计"]),
        ("Design Systems Designer", ["design system", "component library", "设计系统", "组件库"]),
        ("AI Product Designer", ["ai", "llm", "人工智能", "ai product"]),
        ("Fintech Product Designer", ["fintech", "financial", "finance", "金融科技"]),
        ("B2B SaaS Product Designer", ["b2b", "saas", "enterprise", "企业级"]),
    ]
    for title, keywords in title_rules:
        if any(kw in text for kw in keywords):
            suggestions.append(title)
    fallback = ["Product Designer", "UX Designer", "Product Manager", "UX Researcher"]
    for title in fallback:
        suggestions.append(title)
    deduped = []
    seen = set()
    for title in suggestions:
        key = title.strip().lower()
        if key and key not in seen:
            deduped.append(title.strip())
            seen.add(key)
    return deduped[:8]


def ask_job_intentions(suggestions):
    print("\n=== Step 2: Job Intention ===")
    print("Based on your resume, these roles may fit:")
    for i, title in enumerate(suggestions, 1):
        print(f"  {i}. {title}")
    print("Choose one or more numbers, or type your own comma-separated target titles.")
    value = ask("Target roles", default="1")
    selected = []
    if re.fullmatch(r"[\d,\s]+", value):
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            idx = int(part) - 1
            if 0 <= idx < len(suggestions):
                selected.append(suggestions[idx])
    else:
        selected = [item.strip() for item in value.split(",") if item.strip()]
    if not selected:
        selected = [suggestions[0]]
    primary = selected[0]
    return primary, selected


def ask_remote_region_filter():
    print("\n=== Step 3: Remote Region Preference ===")
    options = [
        "No region filtering — show all remote jobs",
        "Exclude US-only jobs",
        "Exclude US-only and EMEA-only jobs",
        "Prefer global/APAC/Asia-friendly remote jobs, and exclude US-only / EMEA-only",
        "Custom include/exclude keywords",
    ]
    idx = ask_choice("How should remote-region filtering work?", options, default=2)
    us_only = [
        "us only", "u.s. only", "united states only", "us residents only",
        "authorized to work in the united states", "authorized to work in the us",
        "must be based in the united states", "must reside in the united states",
        "usa/emea", "usa / emea", "us/emea", "us / emea",
    ]
    emea_only = [
        "emea only", "europe only", "eu only", "uk only", "united kingdom only",
        "must be based in europe", "must reside in europe", "european timezone only",
    ]
    if idx == 0:
        return {"mode": "all", "include_regions": [], "exclude_keywords": []}
    if idx == 1:
        return {"mode": "exclude_only", "include_regions": [], "exclude_keywords": us_only}
    if idx == 2:
        return {"mode": "exclude_only", "include_regions": [], "exclude_keywords": us_only + emea_only}
    if idx == 3:
        return {
            "mode": "include_global",
            "include_regions": [
                "worldwide", "global", "anywhere", "international", "remote-first",
                "async remote", "work from anywhere", "apac", "asia", "china",
                "hong kong", "singapore", "contractor", "freelance",
            ],
            "exclude_keywords": us_only + emea_only,
        }
    include_regions = ask_list("Preferred region keywords to INCLUDE", default=["worldwide", "global", "apac", "asia"])
    exclude_keywords = ask_list("Region keywords to EXCLUDE", default=us_only + emea_only)
    return {"mode": "include_global", "include_regions": include_regions, "exclude_keywords": exclude_keywords}


def default_search_sources():
    return {
        "api_sources": [
            {"name": "RemoteOK", "url": "https://remoteok.com/api", "enabled": True, "type": "remoteok"},
            {"name": "Remotive Design", "url": "https://remotive.com/api/remote-jobs", "enabled": True, "type": "remotive", "category": "design"},
            {"name": "Jobicy Design", "url": "https://jobicy.com/api/v2/remote-jobs?tag=design", "enabled": True, "type": "jobicy"},
            {"name": "Jobicy Product", "url": "https://jobicy.com/api/v2/remote-jobs?tag=product", "enabled": True, "type": "jobicy"},
            {"name": "Himalayas", "url": "https://himalayas.app/jobs/api", "enabled": True, "type": "himalayas"},
            {"name": "Arbeitnow", "url": "https://www.arbeitnow.com/api/job-board-api", "enabled": True, "type": "arbeitnow"},
            {"name": "We Work Remotely Design RSS", "url": "https://weworkremotely.com/categories/remote-design-jobs.rss", "enabled": True, "type": "rss"},
            {"name": "We Work Remotely Product RSS", "url": "https://weworkremotely.com/categories/remote-product-jobs.rss", "enabled": True, "type": "rss"},
            {"name": "LinkedIn Remote Jobs", "enabled": False, "type": "linkedin", "location": "Remote", "datePosted": "past-week", "limit": 10, "max_keywords": 5, "delay_seconds": 2},
        ],
        "ats_sources": [
            {"name": "Figma", "type": "greenhouse", "board": "figma", "enabled": True},
            {"name": "Stripe", "type": "greenhouse", "board": "stripe", "enabled": True},
            {"name": "Airtable", "type": "greenhouse", "board": "airtable", "enabled": True},
            {"name": "Intercom", "type": "greenhouse", "board": "intercom", "enabled": True},
            {"name": "Datadog", "type": "greenhouse", "board": "datadog", "enabled": True},
            {"name": "Vercel", "type": "greenhouse", "board": "vercel", "enabled": True},
            {"name": "Notion", "type": "ashby", "board": "notion", "enabled": True},
            {"name": "Linear", "type": "ashby", "board": "linear", "enabled": True},
            {"name": "Cursor", "type": "ashby", "board": "cursor", "enabled": True},
            {"name": "Perplexity", "type": "ashby", "board": "perplexity", "enabled": True},
            {"name": "Runway", "type": "ashby", "board": "runway", "enabled": True},
        ],
        "official_sources": [
            {"name": "Wellfound", "enabled": False, "query_template": "site:wellfound.com/jobs {keyword} remote"},
            {"name": "电鸭社区", "enabled": False, "query_template": "site:eleduck.com/posts {keyword} 远程"},
            {"name": "BOSS直聘", "enabled": False, "query_template": "site:zhipin.com/web/geek/job {keyword} 远程"},
            {"name": "Remote3", "enabled": False, "query_template": "site:remote3.co {keyword} remote"},
            {"name": "CryptoJobsList", "enabled": False, "query_template": "site:cryptojobslist.com {keyword} remote"},
            {"name": "Web3.career", "enabled": False, "query_template": "site:web3.career {keyword} remote"},
        ],
    }


def build_config(name, title, years, skills, interests, dealbreakers, languages,
                 resume_summary, portfolio_url, email, smtp_host, smtp_port,
                 smtp_user, smtp_pass, location_filter, search_keywords,
                 daily_target=5, schedule_time="12:00", resume_path=""):
    sources = default_search_sources()
    search = {
        "platforms": sources["api_sources"],
        "api_sources": sources["api_sources"],
        "ats_sources": sources["ats_sources"],
        "official_sources": sources["official_sources"],
        "location_filter": location_filter,
        "keywords": search_keywords,
        "max_results_per_platform": 20,
        "max_results_per_official_source": 8,
        "time_range": "OneWeek",
        "daily_target": daily_target,
    }
    return {
        "profile": {
            "name": name,
            "title": title,
            "years_experience": years,
            "skills": skills,
            "interests": interests,
            "dealbreakers": dealbreakers,
            "languages": languages,
            "resume_summary": resume_summary,
            "resume_path": resume_path,
            "portfolio_url": portfolio_url,
            "contact_email": email,
        },
        "search": search,
        "schedule": {
            "daily_time": schedule_time,
            "timezone_note": "Use your machine or automation timezone.",
        },
        "cover_letter": {
            "style": "professional_warm",
            "language": "bilingual",
            "max_length": 400,
            "tone": "confident but not arrogant, shows genuine interest",
        },
        "auto_apply": {"enabled": False, "platforms": [], "note": "Experimental."},
        "email": {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_user": smtp_user,
            "smtp_pass": smtp_pass,
        },
    }


def save_config(config):
    config_path = Path(__file__).resolve().parent / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config_path


def extract_text_from_pdf(pdf_path):
    """Try pdfplumber first, fall back to pdftotext."""
    # Try pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        pass
    except Exception:
        pass
    # Fallback: pdftotext (poppler)
    try:
        result = subprocess.run(
            ["pdftotext", pdf_path, "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    # Fallback: strings (macOS/Linux)
    try:
        result = subprocess.run(
            ["strings", pdf_path],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception:
        pass
    return ""


def parse_resume(text):
    """
    Naively parse resume text to extract structured info.
    Returns dict with: name, title, skills, interests, years_experience, summary
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {
        "name": "",
        "title": "",
        "skills": [],
        "interests": [],
        "years_experience": 3,
        "summary": "",
        "dealbreakers": [],
    }

    # Try to find name: first non-empty short line near top
    for line in lines[:10]:
        if 2 <= len(line.split()) <= 5 and len(line) < 40:
            if not any(kw in line.lower() for kw in ["email", "phone", "linkedin", "github", "http"]):
                result["name"] = line
                break

    # Common job title keywords
    title_kws = [
        "engineer", "developer", "designer", "manager", "analyst", "scientist",
        "product", "project", "marketing", "sales", "support", "lead", "head",
        "director", "vp", "chief", "officer", "consultant", "specialist",
        "researcher", "architect", "devops", "sre", "data", "ml", "ai",
        "前端", "后端", "产品", "设计", "工程", "经理", "总监", "主管",
    ]
    for line in lines[:30]:
        low = line.lower()
        if any(kw in low for kw in title_kws):
            if 3 <= len(line.split()) <= 8 and len(line) < 60:
                result["title"] = line
                break

    # Skills: look for sections with "skills", "technologies", "tools"
    skill_section = ""
    in_skill = False
    skill_kws = ["skill", "technolog", "tool", "proficient", "expertise", "competency",
                 "技能", "技术", "工具", "熟练"]
    for i, line in enumerate(lines):
        low = line.lower()
        if any(kw in low for kw in skill_kws) and len(line) < 40:
            in_skill = True
            start = i + 1
            continue
        if in_skill:
            if line.startswith("#") or line.startswith("=") or (line and line[0].isupper() and len(line) < 40 and any(c in line for c in [":", "-", "•"])):
                skill_section = " ".join(lines[start:i])
                break
            if i - start > 20:
                skill_section = " ".join(lines[start:i])
                break
    if skill_section:
        # Extract comma/bullet separated items
        items = re.split(r"[,•·\n|/;]", skill_section)
        result["skills"] = [i.strip() for i in items if i.strip() and len(i.strip()) < 30][:15]

    # Years of experience: look for patterns like "5 years", "2019-2024"
    exp_pattern = re.compile(r"(\d+)\+?\s*(year|yr|年)", re.I)
    for line in lines:
        m = exp_pattern.search(line)
        if m:
            result["years_experience"] = min(int(m.group(1)), 30)
            break
    if result["years_experience"] == 3:
        # Try date range
        dates = re.findall(r"(20\d{2})\s*[-~]\s*(20\d{2}|present|now|至今)", re.I)
        if dates:
            start = int(dates[0][0])
            end = int(dates[0][1]) if dates[0][1].isdigit() else 2026
            result["years_experience"] = max(end - start, 1)

    # Summary: first paragraph longer than 50 chars
    for line in lines[:50]:
        if len(line) > 50 and not line.startswith("http") and not "@" in line:
            result["summary"] = line[:300]
            break

    return result


def generate_search_keywords(title, skills):
    """Auto-generate search keywords from title and skills."""
    keywords = []
    # Add the exact title
    if title:
        keywords.append(title.lower())
    # Add title without senior/mr./ms. prefixes
    if title:
        stripped = re.sub(
            r"^(senior|mr\.?|ms\.?|staff|principal|lead|head of|chief|director of)\s+",
            "", title.lower()
        )
        if stripped != title.lower():
            keywords.append(stripped)
    # Add top skills as keywords
    for skill in skills[:5]:
        kw = skill.lower()
        if kw not in [k.lower() for k in keywords]:
            keywords.append(kw)
    return keywords


def create_config():
    print("\n=== Remote Job Hunter Setup ===\n")
    print("This setup starts from your resume, then asks you to confirm job and remote preferences.\n")

    resume_text, resume_path = ask_resume_text()
    parsed = parse_resume(resume_text)
    suggestions = infer_job_titles(parsed, resume_text)

    print("\n[Resume parsed]")
    print(f"  Name: {parsed.get('name') or 'not detected'}")
    print(f"  Current title: {parsed.get('title') or 'not detected'}")
    print(f"  Skills: {', '.join(parsed.get('skills', [])[:8]) or 'not detected'}")
    print(f"  Years: {parsed.get('years_experience') or 'not detected'}")

    title, target_titles = ask_job_intentions(suggestions)
    skills = parsed.get("skills") or ask_list("Skills to match against", default=["product design", "UX design"])
    extra_skills = ask_list("Additional skills/keywords to include (optional)", default=[])
    skills = skills + [s for s in extra_skills if s not in skills]

    search_keywords = []
    for target_title in target_titles:
        for kw in generate_search_keywords(target_title, skills):
            if kw.lower() not in [k.lower() for k in search_keywords]:
                search_keywords.append(kw)
    custom_keywords = ask_list("Extra search keywords (optional)", default=[])
    for kw in custom_keywords:
        if kw.lower() not in [k.lower() for k in search_keywords]:
            search_keywords.append(kw)

    location_filter = ask_remote_region_filter()

    print("\n=== Step 4: Email and Schedule ===")
    name = parsed.get("name") or ask("Your full name", required=True)
    years = parsed.get("years_experience") or ask_int("Years of experience", default=5)
    interests = ask_list("Interests to prioritize", default=["remote work"] + target_titles[:3])
    dealbreakers = ask_list("Dealbreakers", default=["on-site required", "no remote"])
    languages = ask_list("Languages you speak", default=["English"])
    resume_summary = parsed.get("summary") or ask("Brief resume summary", required=True)
    portfolio_url = ask("Portfolio URL (optional)", required=False)
    email = ask("Email address for reports", required=True)
    smtp_host = ask("SMTP host", default="smtp.gmail.com")
    smtp_port = ask_int("SMTP port", default=587)
    smtp_user = ask("SMTP username", default=email)
    smtp_pass = ask("SMTP password / app password", required=False)
    schedule_time = ask_time("What time should the daily report run?", default="12:00")
    daily_target = ask_int("How many jobs should each report include?", default=5)

    config = build_config(
        name=name,
        title=title,
        years=years,
        skills=skills,
        interests=interests,
        dealbreakers=dealbreakers,
        languages=languages,
        resume_summary=resume_summary,
        portfolio_url=portfolio_url,
        email=email,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
        location_filter=location_filter,
        search_keywords=search_keywords,
        daily_target=daily_target,
        schedule_time=schedule_time,
        resume_path=resume_path,
    )
    config_path = save_config(config)

    print(f"\nConfig saved to: {config_path}")
    print(f"Target roles: {', '.join(target_titles)}")
    print(f"Search keywords: {', '.join(search_keywords)}")
    print(f"Location filter: {location_filter.get('mode')}")
    print(f"Daily report time: {schedule_time}")

    trial_run = ask_yes_no("\n=== Step 5: Run one test search now? (y/n)", default="y")
    if trial_run:
        print("\nRunning a dry-run search. This will not send email.\n")
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "run_now.py"), "--max-results", str(daily_target)])
        if result.returncode != 0:
            print("\nTest run failed. You can retry later with: python3 run_now.py --dry-run")
    return config_path


def setup_cron(schedule_time=None):
    print("\n=== Schedule Setup ===")
    choice = ask("Set up daily cron job? (y/n)", default="y")
    if choice.lower() != "y":
        return
    time_str = schedule_time or ask_time("What time should it run each day?", default="12:00")
    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        print("Invalid time format. Use HH:MM (24-hour).")
        return
    work_dir = Path(__file__).resolve().parent
    scheduler_path = work_dir / "daily_scheduler.py"
    python = sys.executable
    command = f"{python} {scheduler_path}"
    cron_time = f"{minute} {hour} * * *"
    cron_entry = f'{cron_time} {command} >> {work_dir}/cron.log 2>&1'
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""
    except Exception:
        existing = ""
    if "daily_scheduler.py" in existing:
        print("Cron job already exists. Skipping.")
        return
    new_cron = existing.strip() + "\n" + cron_entry + "\n"
    try:
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_cron)
        if process.returncode == 0:
            print(f"Cron job installed: runs daily at {time_str}.")
        else:
            print("Failed to install cron job. Set it up manually.")
    except Exception as e:
        print(f"Error setting up cron: {e}")

def quick_setup(args):
    """Non-interactive setup from command-line arguments."""
    print("\n=== Remote Job Hunter Quick Setup ===\n")

    name = args.name or "User"
    title = args.title or "Remote Worker"
    email = args.email or ""
    skills = [s.strip() for s in args.skills.split(",")] if args.skills else ["remote work"]
    interests = [s.strip() for s in args.interests.split(",")] if args.interests else ["remote work"]
    years = args.years or 3
    location_mode = args.location_mode or "all"
    schedule_time = args.schedule_time or "12:00"
    daily_target = args.daily_target or 5

    search_keywords = generate_search_keywords(title, skills)

    location_filter = {"mode": location_mode, "include_regions": [], "exclude_keywords": []}
    if location_mode == "exclude_only":
        location_filter["exclude_keywords"] = [
            "us only", "u.s. only", "united states only", "us residents only",
            "usa/emea", "usa / emea", "us/emea", "us / emea",
            "emea only", "europe only", "eu only", "uk only",
        ]
    elif location_mode == "include_global":
        location_filter["include_regions"] = ["worldwide", "global", "anywhere", "international", "apac", "asia"]
        location_filter["exclude_keywords"] = [
            "us only", "united states only", "usa/emea", "us/emea",
            "emea only", "europe only",
        ]

    config = build_config(
        name=name,
        title=title,
        years=years,
        skills=skills,
        interests=interests,
        dealbreakers=["on-site required", "no remote"],
        languages=["English"],
        resume_summary=args.summary or f"{title} with {years}+ years experience.",
        portfolio_url=args.portfolio or "",
        email=email,
        smtp_host=args.smtp_host or "smtp.gmail.com",
        smtp_port=args.smtp_port or 587,
        smtp_user=args.smtp_user or email,
        smtp_pass=args.smtp_pass or "",
        location_filter=location_filter,
        search_keywords=search_keywords,
        daily_target=daily_target,
        schedule_time=schedule_time,
        resume_path=args.resume or "",
    )

    config_path = save_config(config)
    print(f"Config saved to: {config_path}")
    print(f"Search keywords: {', '.join(search_keywords)}")
    print(f"Location mode: {location_mode}")
    print(f"Daily report time: {schedule_time}")
    if not email:
        print("\nNote: No email provided. Email reports are disabled until you set email in config.json.")
    print("\nNext steps:")
    print("  Test run:   python3 run_now.py --dry-run")
    print("  Daily run:  python3 daily_scheduler.py")
    return config_path

def main():
    parser = argparse.ArgumentParser(description="Remote Job Hunter Setup")
    parser.add_argument("--quick", action="store_true", help="Non-interactive quick setup")
    parser.add_argument("--name", type=str, help="Your full name")
    parser.add_argument("--title", type=str, help="Job title (e.g. 'Product Designer')")
    parser.add_argument("--email", type=str, help="Email for reports")
    parser.add_argument("--skills", type=str, help="Comma-separated skills")
    parser.add_argument("--interests", type=str, help="Comma-separated interests")
    parser.add_argument("--years", type=int, help="Years of experience")
    parser.add_argument("--summary", type=str, help="Resume summary")
    parser.add_argument("--resume", type=str, help="Resume file path used for quick setup metadata")
    parser.add_argument("--portfolio", type=str, help="Portfolio URL")
    parser.add_argument("--location-mode", type=str, choices=["all", "exclude_only", "include_global"], help="Location filter mode")
    parser.add_argument("--schedule-time", type=str, help="Daily report time in HH:MM, default 12:00")
    parser.add_argument("--daily-target", type=int, help="Number of jobs per daily report, default 5")
    parser.add_argument("--smtp-host", type=str, help="SMTP host")
    parser.add_argument("--smtp-port", type=int, help="SMTP port")
    parser.add_argument("--smtp-user", type=str, help="SMTP username")
    parser.add_argument("--smtp-pass", type=str, help="SMTP password")
    args = parser.parse_args()

    if args.quick:
        config_path = quick_setup(args)
    else:
        config_path = create_config()
        if platform.system() != "Windows":
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    schedule_time = json.load(f).get("schedule", {}).get("daily_time")
            except Exception:
                schedule_time = None
            setup_cron(schedule_time)
        else:
            print("\nOn Windows, set up a Scheduled Task manually.")
    print("\nSetup complete!")
    if not args.quick:
        print("Run manually: python3 daily_scheduler.py")
        print("Or wait for the scheduled cron job.")


if __name__ == "__main__":
    main()
