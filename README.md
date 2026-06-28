# Remote Job Hunter

自动化每日远程职位搜索工具。按你的简历和偏好，每天自动搜索、匹配、验证并邮件推送适合的远程岗位。

**适用于任何职业方向** — 软件工程师、产品经理、设计师、数据分析师、市场营销……安装时填入你的简历，脚本会自动适配。

Automated daily remote job search tool. Searches, matches, verifies, and emails you suitable remote jobs daily based on your resume and preferences.

**Works for any career path** — Software Engineer, Product Manager, Designer, Data Analyst, Marketing... Paste your resume during setup and the script adapts automatically.

---

## 功能 Features

- 🔍 **多来源搜索** Multi-source search：RemoteOK API、Remotive API、Greenhouse/Lever ATS、网页搜索 Web search
- 🎯 **智能匹配** Smart matching：按你的技能、年限、兴趣打分排序 Score by skills, years, interests
- ✅ **岗位验证** Job verification：自动检测岗位是否还在招聘 Auto-detect closed jobs
- 📧 **邮件报告** Email reports：每日发送匹配结果 + 求职信草稿 Daily matches + cover letter drafts
- 🌍 **地区过滤由用户决定** User-controlled location filter：安装时选择模式 Choose mode at setup — 不会自动过滤任何地区 no automatic region filtering
- 📅 **7 天去重** 7-day deduplication：同一岗位一周内不重复推送 No duplicate jobs within 7 days

---

## 3 步快速开始 Quick Start (3 Steps)

### Step 1: 安装 Install

```bash
# 从 ClawHub 安装 / Install from ClawHub
openclaw skills install @aliceyuruchan/remotejobhunter

# 或手动克隆 / Or clone manually
git clone https://github.com/aliceyuruchan/remotejobhunter.git
cd remotejobhunter
```

### Step 2: 配置 Configure (2 种方式 2 ways)

**方式 A：快速配置（推荐）Quick setup (recommended)**
```bash
python3 setup.py --quick --name "Your Name" --title "Product Designer" --email "you@example.com" --skills "Figma,UI/UX,Product Design"
```

**方式 B：交互式配置 Interactive setup**
```bash
python3 setup.py
```
按提示回答即可。支持粘贴简历自动提取信息。

### Step 3: 运行 Run

**即时搜索（不发送邮件，结果直接显示）Instant search (console output, no email):**
```bash
python3 run_now.py
```

**完整流程（搜索 + 匹配 + 验证 + 邮件报告）Full pipeline with email:**
```bash
python3 daily_scheduler.py
```

**设置每日定时 Daily schedule:**
```bash
# 安装时已自动配置 cron，或手动设置 / Cron is auto-configured during setup, or set manually:
crontab -e
# 添加 / Add: 0 9 * * * cd /path/to/remotejobhunter && python3 daily_scheduler.py
```

---

## 进阶命令 Advanced Commands

| 命令 Command | 说明 Description |
|---|---|
| `python3 run_now.py` | 即时搜索，结果输出到控制台 Instant search, console output |
| `python3 daily_scheduler.py --dry-run` | 完整流程但不发邮件，仅控制台输出 Full pipeline, no email, console only |
| `python3 daily_scheduler.py --no-email` | 完整流程但跳过邮件发送 Full pipeline, skip email |
| `python3 daily_scheduler.py --output-json results.json` | 同时保存结果为 JSON Also save results to JSON |
| `python3 setup.py --quick --name "X" --title "Y" --email "Z"` | 非交互式快速配置 Non-interactive quick setup |

---

## 配置文件说明 Config File (`config.json`)

安装后自动生成 `config.json`，结构如下 / Automatically generated after setup:

```json
{
  "profile": {
    "name": "Your Name",
    "title": "Your Target Job Title",
    "years_experience": 5,
    "skills": ["python", "product design", "AI tools"],
    "interests": ["remote work", "B2B SaaS"],
    "dealbreakers": ["on-site required"],
    "languages": ["English", "Chinese"],
    "resume_summary": "Resume summary...",
    "portfolio_url": "https://...",
    "contact_email": "your@email.com"
  },
  "search": {
    "location_filter": {
      "mode": "exclude_only",
      "include_regions": [],
      "exclude_keywords": ["us only", "united states only"]
    },
    "keywords": ["software engineer", "backend developer", "python"],
    "daily_target": 5
  }
}
```

`search.keywords` 由 `setup.py` 根据你的 `title` 和 `skills` 自动生成，也可手动修改。

`search.keywords` is auto-generated from your `title` and `skills` by `setup.py`, and can be manually edited.

---

## 搜索来源 Search Sources

| 来源 Source | 类型 Type | 说明 Notes |
|------|------|------|
| RemoteOK | API | 免费，无需密钥 Free, no key needed |
| Remotive | API | 免费，无需密钥 Free, no key needed |
| Greenhouse | ATS | 公司招聘系统，直接拉取 Company ATS, direct fetch |
| Lever | ATS | 公司招聘系统，直接拉取 Company ATS, direct fetch |
| 网页搜索 Web search | IQS工具 IQS tool | 可选，需配置路径 Optional, path config required |

在 `config.json` 的 `search.platforms` 里启用/禁用各个来源。

Enable/disable sources in `config.json` → `search.platforms`.

---

## 地区过滤 Location Filter

安装时 `setup.py` 会问你选择哪种地区过滤模式 / `setup.py` asks you to choose a location filter mode:

| 模式 Mode | 说明 Notes |
|------|------|
| **All** | 不过滤，展示所有远程岗位 No filtering, show all remote jobs |
| **Exclude only** | 只排除包含排除关键词的岗位（如 `us only`），保留其他所有 Only exclude jobs matching exclude keywords |
| **Include global** | 优先包含地区关键词的岗位（如 `worldwide`、`asia`），同时排除排除关键词 Prioritize jobs mentioning preferred regions, also exclude unwanted regions |

三种模式下，排除关键词和包含关键词都由**用户自己填写**，脚本不会默认过滤任何地区。

In all three modes, include/exclude keywords are **set by the user**. The script does not filter any region by default.

配置示例 Config example:
```json
"location_filter": {
  "mode": "exclude_only",
  "include_regions": [],
  "exclude_keywords": ["us only", "united states only", "us residents only"]
}
```

---

## 其他过滤规则 Other Filters

脚本还会过滤 / The script also filters:

- ❌ 已关闭的岗位（通过 verify 检测）Closed jobs (detected via verification)
- ❌ 垃圾/诈骗岗位 Spam/scam jobs

---

## 邮件报告示例 Email Report Example

```
Subject: 🎯 Remote Job Matches — 2026-06-26

Top 5 Matches:
1. [92分 Score] Senior Product Designer @ Automattic
   $95K-$200K · Worldwide Remote
   https://automattic.com/...

2. [85分 Score] Product Designer @ ChartMogul
   $100K-$150K · Asia+Europe Only
   ...

Attached: cover_letter_Automattic_2026-06-26.md
```

---

## 常见问题 FAQ

**Q: 支持中国用户吗？Does it work for users in China?**
A: 支持。安装时选择地区过滤模式，可以排除 US-only 岗位或优先全球远程的职位。默认不会自动过滤任何地区。
Yes. Choose location filter mode during setup to exclude US-only jobs or prioritize worldwide remote. No region is filtered by default.

**Q: 需要付费订阅求职网站吗？Do I need paid job board subscriptions?**
A: 不需要。使用的都是免费公开 API 和公司官网 ATS。
No. All sources are free public APIs and company ATS pages.

**Q: 能自动投递吗？Can it auto-apply?**
A: 目前只生成求职信草稿，不自动投递（`auto_apply.enabled: false`）。
Currently only generates cover letter drafts, does not auto-apply (`auto_apply.enabled: false`).

**Q: 我是 XX 职业，能用吗？I'm a [XX profession], can I use this?**
A: 能。`setup.py` 会根据你的职位和技能自动生成搜索关键词，不限定设计师。
Yes. `setup.py` auto-generates search keywords from your title and skills. Not limited to designers.

---

## 依赖 Dependencies

- Python 3.7+
- 标准库（无需 pip install）Standard library only (no pip install needed)
- 可选 Optional：`pdfplumber`（简历 PDF 自动解析 resume PDF parsing）
- 可选 Optional：`iqs-tool`（网页搜索增强 web search enhancement）

---

## npm CLI

After publishing to npm, users can run:

```bash
npx remote-job-hunter setup
npx remote-job-hunter now
npx remote-job-hunter run
```

Or install globally:

```bash
npm install -g remote-job-hunter
remote-job-hunter setup
remote-job-hunter run
```

Commands:

- `setup` creates `config.json`
- `now` runs once without email and prints matches
- `run` runs the full daily workflow and sends the email report
- `search`, `match`, `verify`, and `email` run individual pipeline stages

---

## License

MIT – 自由使用、修改、分发。Free to use, modify, and distribute.

---

## 发布 Links

- GitHub: https://github.com/aliceyuruchan/remotejobhunter
- 欢迎 PR 和 Issue / PRs and Issues welcome
