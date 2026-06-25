#!/usr/bin/env python3
"""
Remote Job Hunter - Verify job URLs are still active.
Checks each matched job URL for signs the position has been closed.
"""
import json, re, sys, time, urllib.request, urllib.error, ssl
from pathlib import Path

CLOSED_SIGNALS = [
    "已停止招聘", "已关闭", "已下线", "已结束", "已招满", "暂停招聘",
    "职位已关闭", "职位已下线", "职位已停止", "招聘已结束", "暂时关闭",
    "no longer accepting", "position closed", "job closed", "expired",
    "this position has been filled", "applications are closed",
    "招聘已暂停", "已停招", "岗位已关闭", "岗位已下线",
]

def fetch_page(url, timeout=10):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        data = resp.read()
        for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                return data.decode(enc)
            except:
                continue
        return data.decode("utf-8", errors="replace")
    except Exception as e:
        return None

def is_closed(html):
    if not html:
        return False, "fetch_failed"
    text = html.lower()
    for sig in CLOSED_SIGNALS:
        if sig.lower() in text:
            return True, sig
    return False, None

def verify_jobs(jobs):
    results = []
    for job in jobs:
        url = job.get("url", "")
        if not url:
            results.append({**job, "active": True, "verify_note": "no_url"})
            continue
        html = fetch_page(url)
        closed, reason = is_closed(html)
        job_out = {**job, "active": not closed, "verify_note": "closed:" + reason if closed else "ok"}
        results.append(job_out)
        if closed:
            print("[VERIFY] CLOSED: %s (%s) — %s" % (job.get("title", ""), url[:60], reason), file=sys.stderr)
        time.sleep(1.5)
    return results

def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    jobs = data.get("matches", [])
    if not jobs:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print("[VERIFY] Checking %d matched jobs..." % len(jobs), file=sys.stderr)
    verified = verify_jobs(jobs)
    active_jobs = [j for j in verified if j.get("active", True)]
    closed_count = len(verified) - len(active_jobs)
    print("[VERIFY] %d active, %d closed/failed" % (len(active_jobs), closed_count), file=sys.stderr)

    data["matches"] = active_jobs
    data["verified"] = True
    data["closed_filtered"] = closed_count
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
