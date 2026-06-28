#!/usr/bin/env python3
"""
Remote Job Hunter - Job-to-profile matching engine.
"""
import json, re, sys
from pathlib import Path
import os

CONFIG_PATH = Path(os.environ.get("JOB_HUNTER_CONFIG", "config.json"))

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize(text):
    return re.sub(r'[^\w\s]', ' ', text.lower())

def keyword_overlap(text, keywords):
    text_norm = normalize(text)
    return [kw for kw in keywords if normalize(kw) in text_norm]

def score_skill_match(job_text, skills):
    hits = keyword_overlap(job_text, skills)
    if not hits: return 0, []
    ratio = len(hits) / max(len(skills), 1)
    return min(40, int(ratio * 60)), hits

def score_experience_match(job_text, years):
    senior = ["senior", "lead", "principal", "staff", "head", "高级", "资深", "专家", "负责人"]
    mid = ["mid-level", "intermediate", "中级", "3年以上"]
    junior = ["junior", "entry", "graduate", "intern", "初级", "实习"]
    text = normalize(job_text)
    if years >= 7:
        for kw in senior:
            if normalize(kw) in text: return 20, "senior"
        for kw in mid:
            if normalize(kw) in text: return 15, "mid"
        return 10, "unspecified"
    elif years >= 3:
        for kw in mid:
            if normalize(kw) in text: return 18, "mid"
        for kw in senior:
            if normalize(kw) in text: return 12, "senior"
        for kw in junior:
            if normalize(kw) in text: return 5, "junior"
        return 14, "unspecified"
    else:
        for kw in junior:
            if normalize(kw) in text: return 15, "junior"
        return 8, "unspecified"

def score_remote_match(job_text):
    high = ["fully remote", "100% remote", "remote-first", "remote only", "完全远程"]
    mid = ["remote", "work from home", "distributed", "远程"]
    low = ["hybrid", "flexible", "混合", "灵活"]
    text = normalize(job_text)
    for kw in high:
        if normalize(kw) in text: return 15, "fully remote"
    for kw in mid:
        if normalize(kw) in text: return 12, "remote"
    for kw in low:
        if normalize(kw) in text: return 8, "hybrid"
    return 0, "unknown"

def score_interest_match(job_text, interests):
    hits = keyword_overlap(job_text, interests)
    if not hits: return 0, []
    return min(15, len(hits) * 5), hits

def check_dealbreakers(job_text, dealbreakers):
    text = normalize(job_text)
    for db in dealbreakers:
        if normalize(db) in text: return True, db
    return False, None

def match_job(job, profile):
    job_text = " ".join([job.get("title", ""), job.get("snippet", ""), job.get("content", ""), job.get("company", "")])
    excluded, db_hit = check_dealbreakers(job_text, profile.get("dealbreakers", []))
    if excluded: return -100, {"dealbreaker": db_hit}, True
    s_score, s_hits = score_skill_match(job_text, profile.get("skills", []))
    e_score, e_level = score_experience_match(job_text, profile.get("years_experience", 3))
    r_score, r_type = score_remote_match(job_text)
    i_score, i_hits = score_interest_match(job_text, profile.get("interests", []))
    total = s_score + e_score + r_score + i_score
    details = {"skill_score": s_score, "skill_hits": s_hits, "exp_score": e_score, "exp_level": e_level, "remote_score": r_score, "remote_type": r_type, "interest_score": i_score, "interest_hits": i_hits, "total": total}
    return total, details, False

def main():
    config = load_config()
    profile = config["profile"]
    daily_target = config["search"].get("daily_target", 5)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            search_data = json.load(f)
    else:
        search_data = json.load(sys.stdin)
    jobs = search_data.get("jobs", [])
    if not jobs:
        print(json.dumps({"date": search_data.get("date", ""), "matches": []}, ensure_ascii=False, indent=2))
        return
    scored, excluded_count = [], 0
    for job in jobs:
        score, details, excluded = match_job(job, profile)
        if excluded:
            excluded_count += 1
            continue
        scored.append({"title": job.get("title", ""), "company": job.get("company", ""), "url": job.get("url", ""), "platform": job.get("platform", ""), "snippet": job.get("snippet", ""), "score": score, "details": details})
    scored.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps({"date": search_data.get("date", ""), "total_searched": search_data.get("total_searched", 0), "total_jobs": len(jobs), "excluded": excluded_count, "scored": len(scored), "matches": scored[:daily_target]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
