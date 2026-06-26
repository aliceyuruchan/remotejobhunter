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
    print("This will create your config.json for daily job hunting.")
    print("You can paste your resume text, or answer questions manually.\n")

    resume_text = ""
    use_resume = ask("Do you want to paste your resume text to auto-fill? (y/n)", default="n")
    if use_resume.lower() == "y":
        print("\nPaste your resume text below. End with a blank line:")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        resume_text = "\n".join(lines)
        if resume_text:
            parsed = parse_resume(resume_text)
            print(f"\n[Auto-parsed] Name: {parsed['name']}")
            print(f"  Title: {parsed['title']}")
            print(f"  Skills: {', '.join(parsed['skills'][:5])}")
            print(f"  Years: {parsed['years_experience']}")
            confirm = ask("Use this parsed info? (y/n)", default="y")
            if confirm.lower() == "y":
                name = parsed["name"] or ask("Your full name", required=True)
                title = parsed["title"] or ask("Your job title", required=True)
                years = parsed["years_experience"] or ask_int("Years of experience", default=5)
                skills = parsed["skills"] or ask_list("Your skills (comma-separated)", default=["product design", "UX"])
                interests = ask_list("Your interests (comma-separated)", default=["remote work", "AI"])
                dealbreakers = ask_list("Dealbreakers (comma-separated)", default=["on-site required", "no remote"])
                languages = ask_list("Languages you speak (comma-separated)", default=["English", "Chinese"])
                resume_summary = parsed["summary"] or ask("Brief resume summary", required=True)
                portfolio_url = ask("Portfolio URL (optional)", required=False)
                email = ask("Your email address (for reports)", required=True)
                smtp_host = ask("SMTP host", default="smtp.gmail.com")
                smtp_port = ask_int("SMTP port", default=587)
                smtp_user = ask("SMTP username (usually your email)", required=True)
                smtp_pass = ask("SMTP password (App Password for Gmail)", required=True)

                search_keywords = generate_search_keywords(title, skills)
                location_filter = ask_location_filter()

                config = {
                    "profile": {
                        "name": name,
                        "title": title,
                        "years_experience": years,
                        "skills": skills,
                        "interests": interests,
                        "dealbreakers": dealbreakers,
                        "languages": languages,
                        "resume_summary": resume_summary,
                        "portfolio_url": portfolio_url,
                        "contact_email": email
                    },
                    "search": {
                        "api_sources": [
                            {"name": "RemoteOK", "url": "https://remoteok.com/api", "enabled": True, "type": "remoteok"},
                            {"name": "Remotive", "url": "https://remotive.com/api/remote-jobs", "enabled": True, "type": "remotive", "category": "design"}
                        ],
                        "ats_sources": [],
                        "official_sources": [],
                        "location_filter": location_filter,
                        "keywords": search_keywords,
                        "max_results_per_platform": 8,
                        "time_range": "OneWeek",
                        "daily_target": 5
                    },
                    "cover_letter": {
                        "style": "professional_warm",
                        "language": "bilingual",
                        "max_length": 400,
                        "tone": "confident but not arrogant, shows genuine interest"
                    },
                    "auto_apply": {"enabled": False, "platforms": [], "note": "Experimental."},
                    "email": {
                        "smtp_host": smtp_host,
                        "smtp_port": smtp_port,
                        "smtp_user": smtp_user,
                        "smtp_pass": smtp_pass
                    }
                }
                config_path = Path(__file__).resolve().parent / "config.json"
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print(f"\nConfig saved to: {config_path}")
                print(f"Search keywords auto-generated: {', '.join(search_keywords)}")
                return config_path

    # Manual mode
    print("\n--- Manual Setup ---")
    name = ask("Your full name", required=True)
    title = ask("Your job title (e.g., 'Product Designer', 'Software Engineer')", required=True)
    years = ask_int("Years of experience", default=5)
    skills = ask_list("Your skills (comma-separated)", default=["product design", "UX design"])
    interests = ask_list("Your interests (comma-separated)", default=["remote work", "AI"])
    dealbreakers = ask_list("Dealbreakers (comma-separated)", default=["on-site required", "no remote"])
    languages = ask_list("Languages you speak (comma-separated)", default=["English", "Chinese"])
    resume_summary = ask("Brief resume summary (or paste resume text)", required=True)
    portfolio_url = ask("Portfolio URL (optional)", required=False)
    email = ask("Your email address (for reports)", required=True)
    smtp_host = ask("SMTP host", default="smtp.gmail.com")
    smtp_port = ask_int("SMTP port", default=587)
    smtp_user = ask("SMTP username (usually your email)", required=True)
    smtp_pass = ask("SMTP password (App Password for Gmail)", required=True)

    search_keywords = generate_search_keywords(title, skills)
    print(f"\nAuto-generated search keywords: {', '.join(search_keywords)}")
    customize = ask("Customize search keywords? (y/n)", default="n")
    if customize.lower() == "y":
        skills = ask_list("Search keywords (comma-separated)", default=search_keywords)

    location_filter = ask_location_filter()

    config = {
        "profile": {
            "name": name,
            "title": title,
            "years_experience": years,
            "skills": skills,
            "interests": interests,
            "dealbreakers": dealbreakers,
            "languages": languages,
            "resume_summary": resume_summary,
            "portfolio_url": portfolio_url,
            "contact_email": email
        },
        "search": {
            "api_sources": [
                {"name": "RemoteOK", "url": "https://remoteok.com/api", "enabled": True, "type": "remoteok"},
                {"name": "Remotive", "url": "https://remotive.com/api/remote-jobs", "enabled": True, "type": "remotive", "category": "design"}
            ],
            "ats_sources": [],
            "official_sources": [],
            "location_filter": location_filter,
            "keywords": search_keywords,
            "max_results_per_platform": 8,
            "time_range": "OneWeek",
            "daily_target": 5
        },
        "cover_letter": {
            "style": "professional_warm",
            "language": "bilingual",
            "max_length": 400,
            "tone": "confident but not arrogant, shows genuine interest"
        },
        "auto_apply": {"enabled": False, "platforms": [], "note": "Experimental."},
        "email": {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_user": smtp_user,
            "smtp_pass": smtp_pass
        }
    }
    config_path = Path(__file__).resolve().parent / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"\nConfig saved to: {config_path}")
    return config_path


def setup_cron():
    print("\n=== Schedule Setup ===")
    choice = ask("Set up daily cron job? (y/n)", default="y")
    if choice.lower() != "y":
        return
    time_str = ask("What time should it run each day? (e.g., '9:00')", default="9:00")
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

    search_keywords = generate_search_keywords(title, skills)

    location_filter = {"mode": location_mode, "include_regions": [], "exclude_keywords": []}
    if location_mode == "exclude_only":
        location_filter["exclude_keywords"] = ["us only", "united states only", "us residents only"]
    elif location_mode == "include_global":
        location_filter["include_regions"] = ["worldwide", "global", "anywhere", "international", "apac", "asia"]
        location_filter["exclude_keywords"] = ["us only", "united states only"]

    config = {
        "profile": {
            "name": name,
            "title": title,
            "years_experience": years,
            "skills": skills,
            "interests": interests,
            "dealbreakers": ["on-site required", "no remote"],
            "languages": ["English"],
            "resume_summary": args.summary or f"{title} with {years}+ years experience.",
            "portfolio_url": args.portfolio or "",
            "contact_email": email
        },
        "search": {
            "api_sources": [
                {"name": "RemoteOK", "url": "https://remoteok.com/api", "enabled": True, "type": "remoteok"},
                {"name": "Remotive", "url": "https://remotive.com/api/remote-jobs", "enabled": True, "type": "remotive"}
            ],
            "ats_sources": [],
            "official_sources": [],
            "location_filter": location_filter,
            "keywords": search_keywords,
            "max_results_per_platform": 8,
            "time_range": "OneWeek",
            "daily_target": 5
        },
        "cover_letter": {
            "style": "professional_warm",
            "language": "bilingual",
            "max_length": 400,
            "tone": "confident but not arrogant, shows genuine interest"
        },
        "auto_apply": {"enabled": False, "platforms": [], "note": "Experimental."},
        "email": {
            "smtp_host": args.smtp_host or "smtp.gmail.com",
            "smtp_port": args.smtp_port or 587,
            "smtp_user": args.smtp_user or email,
            "smtp_pass": args.smtp_pass or ""
        }
    }

    config_path = Path(__file__).resolve().parent / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"Config saved to: {config_path}")
    print(f"Search keywords: {', '.join(search_keywords)}")
    print(f"Location mode: {location_mode}")
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
    parser.add_argument("--portfolio", type=str, help="Portfolio URL")
    parser.add_argument("--location-mode", type=str, choices=["all", "exclude_only", "include_global"], help="Location filter mode")
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
            setup_cron()
        else:
            print("\nOn Windows, set up a Scheduled Task manually.")
    print("\nSetup complete!")
    if not args.quick:
        print("Run manually: python3 daily_scheduler.py")
        print("Or wait for the scheduled cron job.")


if __name__ == "__main__":
    main()
