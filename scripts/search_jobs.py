#!/usr/bin/env python3
"""
Remote Job Hunter - multi-source job search engine.

Sources are ordered by reliability:
1. Public JSON APIs (RemoteOK, Remotive)
2. Company ATS feeds (Greenhouse, Lever)
3. Focused search over curated job boards and company career pages (optional, requires IQS tool)
"""
import html
import json
import hashlib
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# Config paths from environment or defaults
CONFIG_PATH = Path(os.environ.get("JOB_HUNTER_CONFIG", "config.json"))
HISTORY_PATH = Path(os.environ.get("JOB_HUNTER_HISTORY", "history.json"))
IQS_TOOL = os.environ.get("JOB_HUNTER_IQS_TOOL", "")
DEDUP_COOLDOWN_DAYS = 7

# Default location filter values (used when config doesn't specify them)
DEFAULT_INCLUDE_REGIONS = [
    "worldwide", "global", "anywhere", "international", "apac", "asia", "china",
    "contractor", "freelance", "async remote", "work from anywhere", "remote-first",
    "north america", "europe", "latam", "mena", "africa", "oceania",
    "美国", "加拿大", "欧洲", "亚洲", "全球", "国际", "远程",
]
DEFAULT_EXCLUDE_KEYWORDS = [
    "us only", "u.s. only", "united states only", "us residents only",
    "authorized to work in the united states", "authorized to work in the us",
    "must be based in the united states", "must reside in the united states",
]

# SPAM keywords (kept as they are not sensitive)
SPAM_TITLE_KEYWORDS = [
    "按摩", "约炮", "小姐", "上门服务", "喝茶", "全套", "特殊服务", "约喝茶",
    "外围", "伴游", "包养", "约妹", "喝茶养生", "商务伴游"
]

EXCLUDE_URL_PATTERNS = [
    "/search?", "/jobs/search", "/company/", "/in/", "/schools/",
    "/career-advice/", "/salary/", "/companies/", "/q-", "/find-jobs",
    "career-advice", "salary-guide", "/about", "/contact", "/privacy", "/terms",
    "/blog/", "/resources/", "/learn/", "/login", "/signin", "/sign-in",
]


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history():
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen": {}, "stats": {"total_searched": 0, "total_matched": 0, "total_applied": 0}}


def save_history(history):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def url_hash(url):
    return hashlib.sha256(urlparse(url).geturl().encode()).hexdigest()[:16]


def strip_html(value):
    if not value:
        return ""
    value = re.sub(r"<br\s*/?>", "\n", str(value), flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def text_has_any(text, keywords):
    text = (text or "").lower()
    return any(kw.lower() in text for kw in keywords)


def get_location_filter(config):
    """Read location filter config, fall back to defaults."""
    lf = config.get("search", {}).get("location_filter", {})
    mode = lf.get("mode", "include_global")
    include_regions = lf.get("include_regions", DEFAULT_INCLUDE_REGIONS)
    exclude_keywords = lf.get("exclude_keywords", DEFAULT_EXCLUDE_KEYWORDS)
    return mode, include_regions, exclude_keywords


def has_excluded_location(text, exclude_keywords):
    """Check if text contains any exclusion keyword."""
    if not exclude_keywords:
        return False
    text = (text or "").lower()
    return any(kw in text for kw in exclude_keywords)


def has_included_region(text, include_regions):
    """Check if text mentions any desired region."""
    if not include_regions:
        return True  # No filter = accept all
    text = (text or "").lower()
    return any(kw in text for kw in include_regions)


def http_json(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json,text/plain,*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except Exception as e:
        print("[WARN] JSON fetch failed: %s (%s)" % (url, e), file=sys.stderr)
        return None


def iqs_search(query, num=8):
    if not IQS_TOOL or not Path(IQS_TOOL).exists():
        print("[WARN] IQS tool not configured, skipping web search", file=sys.stderr)
        return []
    cmd = [sys.executable, IQS_TOOL, "search", query, "--num", str(num)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print("[WARN] IQS failed (rc=%d): %s" % (result.returncode, query), file=sys.stderr)
            return []
        try:
            data = json.loads(result.stdout)
            return data.get("results", [])
        except json.JSONDecodeError:
            return []
    except Exception as e:
        print("[WARN] IQS error: %s" % e, file=sys.stderr)
        return []


def is_likely_job_url(url: str) -> bool:
    u = url.lower()
    for pat in EXCLUDE_URL_PATTERNS:
        if pat in u:
            return False
    if "linkedin.com" in u:
        return "/jobs/view/" in u
    if "indeed.com" in u:
        return "/viewjob" in u or "/job/" in u
    if "remoteok.com" in u:
        return True
    if "remotive.com" in u:
        return "/remote-jobs/" in u
    if "weworkremotely.com" in u:
        return "/remote-jobs/" in u or "/job/" in u
    if "wellfound.com" in u:
        return "/jobs" in u
    if "himalayas.app" in u:
        return "/jobs/" in u
    if "remote.co" in u:
        return "/remote-jobs/" in u
    if "zhipin.com" in u:
        return "/job_detail" in u
    if "lagou.com" in u:
        return "/jobs/" in u or "/job/" in u
    if "liepin.com" in u:
        return "/job/" in u
    if "remote3.com" in u or "cryptojobslist.com" in u or "web3.career" in u:
        return True
    return True


def contains_spam_signals(title: str, snippet: str, content: str) -> bool:
    blob = f"{title}\n{snippet}\n{content}"
    for kw in SPAM_TITLE_KEYWORDS:
        if kw in blob:
            return True
    if "远程线上实习" in blob:
        return True
    title_lower = (title or "").lower().strip()
    if title_lower in ["", "jobs", "jobs search", "search results", "login", "sign in"]:
        return True
    if "verification required" in title_lower:
        return True
    return False


def extract_lead_job_title(snippet: str):
    for line in snippet.split("\n"):
        line = line.strip().lstrip("#").strip()
        if "### " in line:
            line = line.split("### ", 1)[-1].strip()
        if not line:
            continue
        if any(ch.isdigit() for ch in line[:3]):
            continue
        if len(line) > 120:
            continue
        low = line.lower()
        if low == "jobs" or "jobs in" in low or low.startswith("get notified"):
            continue
        return line
    return ""


def extract_company(title):
    for sep in [" at ", " @ ", " - ", " | "]:
        if sep in title:
            return title.split(sep)[-1].strip()
    return ""


def classify_platform(url):
    domain = urlparse(url).netloc.lower()
    if "linkedin" in domain: return "LinkedIn"
    if "indeed" in domain: return "Indeed"
    if "remoteok" in domain: return "RemoteOK"
    if "remotive" in domain: return "Remotive"
    if "weworkremotely" in domain: return "WeWorkRemotely"
    if "wellfound" in domain: return "Wellfound"
    if "himalayas" in domain: return "Himalayas"
    if "remote.co" in domain: return "Remote.co"
    if "zhipin" in domain or "boss" in domain: return "Boss直聘"
    if "lagou" in domain: return "拉勾"
    if "liepin" in domain: return "猎聘"
    if "remote3" in domain: return "Remote3"
    if "cryptojobslist" in domain: return "CryptoJobsList"
    if "web3.career" in domain: return "web3.career"
    if "greenhouse" in domain: return "Greenhouse"
    if "lever" in domain: return "Lever"
    return domain


def make_job(title, url, snippet="", content="", platform="", company="", keyword="", relevance=0, source_type="search"):
    title = strip_html(title)
    snippet = strip_html(snippet)
    content = strip_html(content)
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "content": content,
        "platform": platform or classify_platform(url),
        "company": company or extract_company(title),
        "search_keyword": keyword,
        "relevance": relevance,
        "source_type": source_type,
    }


def should_keep_location(title, snippet, content, source_name="", config=None):
    """
    Filter jobs by location based on user's config.
    Modes:
      - "all": no location filtering at all, accept everything
      - "include_global": only keep jobs that mention included regions OR don't specify any region
      - "exclude_only": only exclude jobs matching exclude_keywords, keep everything else
    """
    if config is None:
        return True
    mode, include_regions, exclude_keywords = get_location_filter(config)

    # Mode "all": no filtering
    if mode == "all":
        return True

    blob = " ".join([title or "", snippet or "", content or "", source_name or ""])

    # Always check exclusion list (regardless of mode, unless "all")
    if exclude_keywords and has_excluded_location(blob, exclude_keywords):
        return False

    # Mode "exclude_only": done after exclusion check
    if mode == "exclude_only":
        return True

    # Mode "include_global": also check that job mentions an included region
    # OR doesn't specify any region restriction (generic "remote" is OK)
    if mode == "include_global":
        if has_included_region(blob, include_regions):
            return True
        # If no region keyword found at all, it's probably a generic remote listing — keep it
        return True

    return True


def search_remoteok_api(source, keywords, config):
    data = http_json(source.get("url", "https://remoteok.com/api"))
    if not isinstance(data, list):
        return []
    jobs = []
    for item in data:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        title = item.get("position") or item.get("title") or ""
        tags = " ".join(item.get("tags") or [])
        blob = " ".join([title, item.get("company", ""), tags, item.get("description", "")])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, tags, item.get("description", ""), "RemoteOK", config):
            continue
        jobs.append(make_job(
            title=title,
            url=item.get("url"),
            snippet="%s %s" % (item.get("company", ""), tags),
            content=item.get("description", ""),
            platform="RemoteOK API",
            company=item.get("company", ""),
            keyword="api",
            relevance=1,
            source_type="api",
        ))
    return jobs


def search_remotive_api(source, keywords, config):
    params = {"category": source.get("category", "design")}
    url = source.get("url", "https://remotive.com/api/remote-jobs") + "?" + urllib.parse.urlencode(params)
    data = http_json(url)
    if not isinstance(data, dict):
        return []
    jobs = []
    for item in data.get("jobs", []):
        title = item.get("title") or ""
        tags = item.get("tags", "")
        if isinstance(tags, list):
            tags = " ".join(str(tag) for tag in tags)
        blob = " ".join([title, item.get("company_name", ""), item.get("description", ""), tags])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, item.get("candidate_required_location", ""), item.get("description", ""), "Remotive", config):
            continue
        jobs.append(make_job(
            title=title,
            url=item.get("url", ""),
            snippet="%s %s %s" % (item.get("company_name", ""), item.get("candidate_required_location", ""), item.get("job_type", "")),
            content=item.get("description", ""),
            platform="Remotive API",
            company=item.get("company_name", ""),
            keyword="api",
            relevance=1,
            source_type="api",
        ))
    return jobs


def search_greenhouse(source, keywords, config):
    board = source.get("board")
    if not board:
        return []
    url = "https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=true" % urllib.parse.quote(board)
    data = http_json(url)
    if not isinstance(data, dict):
        return []
    company = source.get("name", board)
    jobs = []
    for item in data.get("jobs", []):
        title = item.get("title") or ""
        offices = " ".join([o.get("name", "") for o in item.get("offices", []) if isinstance(o, dict)])
        departments = " ".join([d.get("name", "") for d in item.get("departments", []) if isinstance(d, dict)])
        content = item.get("content", "")
        blob = " ".join([title, offices, departments, content])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, offices, content, company, config):
            continue
        jobs.append(make_job(
            title=title,
            url=item.get("absolute_url") or item.get("url") or "",
            snippet="%s %s" % (offices, departments),
            content=content,
            platform="%s Careers" % company,
            company=company,
            keyword="ats",
            relevance=1,
            source_type="greenhouse",
        ))
    return jobs


def search_lever(source, keywords, config):
    company = source.get("company")
    if not company:
        return []
    url = "https://api.lever.co/v0/postings/%s?mode=json" % urllib.parse.quote(company)
    data = http_json(url)
    if not isinstance(data, list):
        return []
    display_name = source.get("name", company)
    jobs = []
    for item in data:
        title = item.get("text") or ""
        categories = item.get("categories") or {}
        location = categories.get("location", "") if isinstance(categories, dict) else ""
        team = categories.get("team", "") if isinstance(categories, dict) else ""
        commitment = categories.get("commitment", "") if isinstance(categories, dict) else ""
        description = " ".join([section.get("content", "") for section in item.get("lists", []) if isinstance(section, dict)])
        blob = " ".join([title, location, team, commitment, description])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, location, description, display_name, config):
            continue
        jobs.append(make_job(
            title=title,
            url=item.get("hostedUrl") or item.get("applyUrl") or "",
            snippet="%s %s %s" % (location, team, commitment),
            content=description or item.get("description", ""),
            platform="%s Careers" % display_name,
            company=display_name,
            keyword="ats",
            relevance=1,
            source_type="lever",
        ))
    return jobs


def search_ashby(source, keywords, config):
    board = source.get("board")
    if not board:
        return []
    url = "https://api.ashbyhq.com/posting-api/job-board/%s" % urllib.parse.quote(board)
    data = http_json(url)
    if not isinstance(data, dict):
        return []
    display_name = source.get("name", board)
    jobs = []
    for item in data.get("jobs", []):
        title = item.get("title") or ""
        location = item.get("location") or ""
        department = item.get("department") or item.get("team") or ""
        employment = item.get("employmentType") or ""
        content = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
        blob = " ".join([title, location, department, employment, content])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, location, content, display_name, config):
            continue
        job_id = item.get("id") or ""
        job_url = item.get("jobUrl") or item.get("externalLink") or item.get("url") or ""
        if not job_url and job_id:
            job_url = "https://jobs.ashbyhq.com/%s/%s" % (urllib.parse.quote(board), urllib.parse.quote(job_id))
        jobs.append(make_job(
            title=title,
            url=job_url,
            snippet="%s %s %s" % (location, department, employment),
            content=content,
            platform="%s Careers" % display_name,
            company=display_name,
            keyword="ats",
            relevance=1,
            source_type="ashby",
        ))
    return jobs


def search_jobicy_api(source, keywords, config):
    url = source.get("url", "https://jobicy.com/api/v2/remote-jobs")
    data = http_json(url)
    if not isinstance(data, dict):
        return []
    jobs = []
    for item in data.get("jobs", []):
        title = item.get("jobTitle") or item.get("title") or ""
        company = item.get("companyName") or item.get("company") or ""
        location = item.get("jobGeo") or item.get("location") or ""
        content = item.get("jobDescription") or item.get("description") or ""
        tags = item.get("jobIndustry") or item.get("tags") or []
        if isinstance(tags, list):
            tags = " ".join(str(tag) for tag in tags)
        blob = " ".join([title, company, location, content, tags])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, location, content, "Jobicy", config):
            continue
        jobs.append(make_job(
            title=title,
            url=item.get("url") or item.get("jobUrl") or "",
            snippet="%s %s %s" % (company, location, tags),
            content=content,
            platform="Jobicy API",
            company=company,
            keyword="api",
            relevance=1,
            source_type="jobicy",
        ))
    return jobs


def search_arbeitnow_api(source, keywords, config):
    data = http_json(source.get("url", "https://www.arbeitnow.com/api/job-board-api"))
    if not isinstance(data, dict):
        return []
    jobs = []
    for item in data.get("data", []):
        title = item.get("title") or ""
        company = item.get("company_name") or ""
        location = " ".join(item.get("location") or [])
        tags = " ".join(item.get("tags") or [])
        content = item.get("description") or ""
        blob = " ".join([title, company, location, tags, content])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, location, content, "Arbeitnow", config):
            continue
        jobs.append(make_job(
            title=title,
            url=item.get("url") or "",
            snippet="%s %s %s" % (company, location, tags),
            content=content,
            platform="Arbeitnow API",
            company=company,
            keyword="api",
            relevance=1,
            source_type="arbeitnow",
        ))
    return jobs


def search_himalayas_api(source, keywords, config):
    data = http_json(source.get("url", "https://himalayas.app/jobs/api"))
    if not isinstance(data, dict):
        return []
    jobs = []
    for item in data.get("jobs", []):
        title = item.get("title") or ""
        company = item.get("companyName") or ""
        location = item.get("location") or item.get("locationRestrictions") or ""
        if isinstance(location, list):
            location = " ".join(str(part) for part in location)
        content = item.get("description") or item.get("excerpt") or ""
        tags = item.get("tags") or []
        if isinstance(tags, list):
            tags = " ".join(str(tag) for tag in tags)
        blob = " ".join([title, company, location, tags, content])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, location, content, "Himalayas", config):
            continue
        jobs.append(make_job(
            title=title,
            url=item.get("applicationLink") or item.get("url") or item.get("jobUrl") or "",
            snippet="%s %s %s" % (company, location, tags),
            content=content,
            platform="Himalayas API",
            company=company,
            keyword="api",
            relevance=1,
            source_type="himalayas",
        ))
    return jobs


def search_rss_source(source, keywords, config):
    url = source.get("url", "")
    if not url:
        return []
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/rss+xml,text/xml,*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print("[WARN] RSS fetch failed: %s (%s)" % (url, e), file=sys.stderr)
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print("[WARN] RSS parse failed: %s (%s)" % (url, e), file=sys.stderr)
        return []
    jobs = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        description = item.findtext("description") or ""
        blob = " ".join([title, description, source.get("name", "")])
        if not text_has_any(blob, keywords):
            continue
        if not should_keep_location(title, "", description, source.get("name", ""), config):
            continue
        jobs.append(make_job(
            title=title,
            url=link,
            snippet=source.get("name", ""),
            content=description,
            platform=source.get("name", "RSS"),
            company=extract_company(title),
            keyword="rss",
            relevance=1,
            source_type="rss",
        ))
    return jobs


def search_api_sources(config):
    all_jobs = []
    keywords = config["search"].get("keywords", [])
    for source in config["search"].get("api_sources", []):
        if not source.get("enabled", True):
            continue
        print("[API] %s" % source.get("name", source.get("type", "api")), file=sys.stderr)
        if source.get("type") == "remoteok":
            all_jobs.extend(search_remoteok_api(source, keywords, config))
        elif source.get("type") == "remotive":
            all_jobs.extend(search_remotive_api(source, keywords, config))
        elif source.get("type") == "jobicy":
            all_jobs.extend(search_jobicy_api(source, keywords, config))
        elif source.get("type") == "arbeitnow":
            all_jobs.extend(search_arbeitnow_api(source, keywords, config))
        elif source.get("type") == "himalayas":
            all_jobs.extend(search_himalayas_api(source, keywords, config))
        elif source.get("type") == "rss":
            all_jobs.extend(search_rss_source(source, keywords, config))
        time.sleep(1)
    return all_jobs


def search_ats_sources(config):
    all_jobs = []
    keywords = config["search"].get("keywords", [])
    for source in config["search"].get("ats_sources", []):
        if not source.get("enabled", True):
            continue
        print("[ATS] %s" % source.get("name", source.get("company", source.get("board", "ats"))), file=sys.stderr)
        if source.get("type") == "greenhouse":
            all_jobs.extend(search_greenhouse(source, keywords, config))
        elif source.get("type") == "lever":
            all_jobs.extend(search_lever(source, keywords, config))
        elif source.get("type") == "ashby":
            all_jobs.extend(search_ashby(source, keywords, config))
        time.sleep(0.5)
    return all_jobs


def search_query_sources(config):
    all_jobs = []
    search_config = config["search"]
    grouped_sources = []
    grouped_sources.extend(search_config.get("platforms", []))
    grouped_sources.extend(search_config.get("official_sources", []))
    for platform in grouped_sources:
        if not platform.get("enabled", True):
            continue
        if not platform.get("query_template"):
            continue
        source_limit = search_config.get("max_results_per_official_source", search_config.get("max_results_per_platform", 6))
        for keyword in search_config.get("keywords", []):
            query = platform["query_template"].format(keyword=keyword)
            print("[SEARCH] %s: %s" % (platform["name"], query), file=sys.stderr)
            results = iqs_search(query, num=source_limit)
            time.sleep(1)
            for r in results:
                url = r.get("url", "")
                if not url:
                    continue
                if not is_likely_job_url(url):
                    continue
                if contains_spam_signals(r.get("title", ""), r.get("snippet", ""), r.get("content", "")):
                    continue
                if not should_keep_location(r.get("title", ""), r.get("snippet", ""), r.get("content", ""), platform.get("name", ""), config):
                    continue
                lead_title = extract_lead_job_title(r.get("snippet", "")) or r.get("title", "")
                all_jobs.append(make_job(
                    title=lead_title,
                    url=url,
                    snippet=r.get("snippet", ""),
                    content=r.get("content", ""),
                    platform=platform.get("name") or classify_platform(url),
                    company=extract_company(lead_title),
                    keyword=keyword,
                    relevance=r.get("score", 0),
                    source_type="search",
                ))
    return all_jobs


def search_all(config):
    jobs = []
    jobs.extend(search_api_sources(config))
    jobs.extend(search_ats_sources(config))
    jobs.extend(search_query_sources(config))
    return [job for job in jobs if job.get("url") and job.get("title")]


def seen_within_cooldown(entry, today_date):
    first_seen = entry.get("first_seen") or entry.get("last_seen") or ""
    try:
        first_date = datetime.strptime(first_seen, "%Y-%m-%d")
        return today_date - first_date < timedelta(days=DEDUP_COOLDOWN_DAYS)
    except Exception:
        return True


def deduplicate(jobs, history):
    new_jobs = []
    today = time.strftime("%Y-%m-%d")
    today_date = datetime.strptime(today, "%Y-%m-%d")
    for job in jobs:
        h = url_hash(job["url"])
        if h in history["seen"]:
            entry = history["seen"][h]
            entry["last_seen"] = today
            entry["times_seen"] = entry.get("times_seen", 0) + 1
            if entry.get("applied", False):
                continue
            if seen_within_cooldown(entry, today_date):
                continue
            entry["first_seen"] = today
            entry["title"] = job.get("title", entry.get("title", ""))
            new_jobs.append(job)
        else:
            history["seen"][h] = {
                "url": job["url"],
                "title": job.get("title", ""),
                "first_seen": today,
                "last_seen": today,
                "times_seen": 1,
                "applied": False,
                "saved": False,
                "source_type": job.get("source_type", ""),
            }
            new_jobs.append(job)
    return new_jobs


def main():
    config = load_config()
    history = load_history()
    all_jobs = search_all(config)
    new_jobs = deduplicate(all_jobs, history)
    history["stats"]["total_searched"] = history["stats"].get("total_searched", 0) + len(all_jobs)
    history["stats"]["total_matched"] = history["stats"].get("total_matched", 0) + len(new_jobs)
    save_history(history)
    today = time.strftime("%Y-%m-%d")
    print(json.dumps({"date": today, "total_searched": len(all_jobs), "new_jobs": len(new_jobs), "jobs": new_jobs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
