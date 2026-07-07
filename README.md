# Remote Job Hunter

If you have any questions about using this skill, feel free to email me at **aliceyuruchan@gmail.com** or DM me on LinkedIn: **aliceyuruchan**.

Remote Job Hunter is a resume-first job search automation tool. It searches remote job sources, matches roles against your resume and preferences, verifies links, deduplicates results, and sends a daily email report.

It works for many career paths: product design, UX research, software engineering, product management, data, marketing, operations, and more. During setup, it starts from your resume, infers possible roles, and asks you to confirm your job and remote-region preferences.

## Features

- Multi-source search: RemoteOK, Remotive, Jobicy, Himalayas, Arbeitnow, We Work Remotely RSS, Greenhouse, Ashby, Lever, and optional LinkedIn.
- Resume-first onboarding: upload/provide a resume file path or paste resume text.
- Role inference: suggests possible target roles from your resume.
- Smart matching: scores jobs by title relevance, skills, experience, interests, and remote fit.
- Region filtering: can filter US-only, EMEA-only, Canada-only, UK-only, and other restricted remote roles.
- Job verification: checks whether matched job links are still active.
- Email reports: sends a daily report with top matches.
- 7-day deduplication: avoids repeating the same job within a cooldown window.

## Install

### npm

Run directly:

```bash
npx remote-job-hunter setup
npx remote-job-hunter now
npx remote-job-hunter run
```

Or install globally:

```bash
npm install -g remote-job-hunter
remote-job-hunter setup
remote-job-hunter now
remote-job-hunter run
```

### GitHub

```bash
git clone https://github.com/aliceyuruchan/remotejobhunter.git
cd remotejobhunter
python3 setup.py
```

## Setup Flow

Interactive setup is recommended:

```bash
remote-job-hunter setup
```

The setup flow:

1. Asks for a resume file path, or lets you paste resume text.
2. Parses the resume and suggests possible target roles.
3. Lets you choose job intentions and extra keywords.
4. Asks for remote-region preferences, including whether to filter US-only or EMEA-only jobs.
5. Asks for email settings and the daily report time.
6. Asks whether to run one test search immediately.

For non-interactive setup:

```bash
remote-job-hunter setup --quick \
  --name "Your Name" \
  --title "Product Designer" \
  --email "you@example.com" \
  --skills "Figma,UX Design,Product Design"
```

## Commands

| Command | Description |
|---|---|
| `remote-job-hunter setup` | Resume-first interactive setup |
| `remote-job-hunter now` | Run once without sending email and print matches |
| `remote-job-hunter run` | Run the full daily workflow and send the email report |
| `remote-job-hunter search` | Run only the search stage |
| `remote-job-hunter match` | Run only the matching stage, reading JSON from stdin |
| `remote-job-hunter verify` | Run only the verification stage, reading JSON from stdin |
| `remote-job-hunter email` | Send/save report, reading matched JSON from stdin |

Python entry points are also available:

```bash
python3 setup.py
python3 run_now.py
python3 daily_scheduler.py
python3 daily_scheduler.py --dry-run
python3 daily_scheduler.py --no-email
python3 daily_scheduler.py --output-json results.json
```

## Configuration

Setup generates a local `config.json`. Do not commit this file because it may contain personal email settings.

Example:

```json
{
  "profile": {
    "name": "Your Name",
    "title": "Product Designer",
    "years_experience": 5,
    "skills": ["Figma", "UX Design", "Product Design"],
    "interests": ["remote work", "AI", "B2B SaaS"],
    "dealbreakers": ["on-site required", "no remote"],
    "resume_summary": "Resume summary...",
    "portfolio_url": "https://...",
    "contact_email": "you@example.com"
  },
  "search": {
    "location_filter": {
      "mode": "exclude_only",
      "include_regions": [],
      "exclude_keywords": ["us only", "united states only", "emea only"]
    },
    "keywords": ["product designer", "ux designer"],
    "daily_target": 5
  },
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "you@example.com",
    "smtp_pass": "your-app-password"
  }
}
```

## Search Sources

| Source | Type | Notes |
|---|---|---|
| RemoteOK | API | Free, no key required |
| Remotive | API | Free, no key required |
| Jobicy | API | Remote job API |
| Himalayas | API | Remote job API |
| Arbeitnow | API | Job board API |
| We Work Remotely | RSS | Design and product RSS feeds |
| Greenhouse | ATS | Company career boards |
| Ashby | ATS | Company career boards |
| Lever | ATS | Company career boards |
| LinkedIn | MCP bridge | Optional, powered by `linkedin-mcp-search`; disabled by default to avoid rate limits |
| Web search | IQS tool | Optional, requires configuring an IQS tool path |

## Region Filtering

Remote Job Hunter can filter region-restricted remote jobs such as:

- US-only
- EMEA-only
- Canada-only
- UK-only
- "remote within the United States"
- "one of our US hubs"
- "authorized to work in the country for which you applied"

This is useful for people applying from outside the US or Europe. Jobs that merely mention Figma as a skill are preserved; the filter targets region restrictions, not design-tool keywords.

## Email Reports

For Gmail, use an App Password instead of your normal login password:

https://myaccount.google.com/apppasswords

If SMTP credentials are missing, the tool can still run search/match/verify and save an HTML report locally.

## Privacy

The generated files below may contain personal data and are ignored by git/npm packaging:

- `config.json`
- `history.json`
- `reports/`
- `cover-letters/`
- `cron.log`

## Troubleshooting

**No config found**

Run:

```bash
remote-job-hunter setup
```

**No jobs found**

Try broadening `search.keywords`, lowering region restrictions, or setting `location_filter.mode` to `all`.

**Email not received**

Check spam, SMTP username/password, and whether your email provider requires an app password.

**LinkedIn source not running**

LinkedIn is optional and disabled by default in newly generated configs. Enable a source with `"type": "linkedin"` in `search.api_sources`. It uses `linkedin-mcp-search` and may be rate-limited by LinkedIn.

## Links

- GitHub: https://github.com/aliceyuruchan/remotejobhunter
- npm: https://www.npmjs.com/package/remote-job-hunter

## License

MIT. Free to use, modify, and distribute.

---

# 中文说明

如果你在使用这个 skill 时有任何疑问，欢迎发邮件给我：**aliceyuruchan@gmail.com**，也可以在 LinkedIn 上私信我：**aliceyuruchan**。

Remote Job Hunter 是一个从简历开始的远程求职自动化工具。它会根据你的简历和偏好搜索远程岗位、打分匹配、验证岗位是否仍然开放、去重，并生成每日邮件报告。

## 快速开始

```bash
npx remote-job-hunter setup
npx remote-job-hunter now
npx remote-job-hunter run
```

也可以全局安装：

```bash
npm install -g remote-job-hunter
remote-job-hunter setup
remote-job-hunter now
remote-job-hunter run
```

## 配置流程

推荐使用交互式配置：

```bash
remote-job-hunter setup
```

配置流程会：

1. 要求你提供简历文件路径，或直接粘贴简历文本。
2. 解析简历并推断适合的岗位方向。
3. 让你选择岗位意向和额外关键词。
4. 让你选择远程地区偏好，例如是否过滤 US-only / EMEA-only 岗位。
5. 设置邮件和每日发送时间。
6. 询问是否立即试跑一次。

## 常用命令

| 命令 | 说明 |
|---|---|
| `remote-job-hunter setup` | 从简历开始进行交互式配置 |
| `remote-job-hunter now` | 立即试跑一次，不发送邮件，只在控制台显示结果 |
| `remote-job-hunter run` | 执行完整每日流程，并发送邮件报告 |

## 注意事项

- `config.json` 可能包含邮箱和 app password，不要上传到 GitHub。
- 如果使用 Gmail，请使用 App Password，不要使用普通登录密码。
- LinkedIn 来源是可选的，默认关闭，因为 LinkedIn 可能会 rate limit。
- 地区过滤会排除 US-only、EMEA-only、Canada-only、UK-only 等限制岗位，但不会误删只把 Figma 当作技能要求的岗位。
