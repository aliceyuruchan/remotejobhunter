#!/usr/bin/env node
import { searchJobs } from "linkedin-mcp-search/dist/linkedin.js";

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith("--")) continue;
    const name = key.slice(2);
    const value = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : "true";
    args[name] = value;
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
const keywords = args.keywords || "";
const location = args.location || "Remote";
const limit = Math.min(Number(args.limit || 10), 50);

if (!keywords.trim()) {
  console.error("Missing --keywords");
  process.exit(2);
}

try {
  const result = await searchJobs({
    keywords,
    location,
    workplaceType: ["remote"],
    datePosted: args.datePosted || "past-week",
    sortBy: args.sortBy || "most-recent",
    limit,
  });
  const jobs = (result.jobs || []).map((job) => ({
    id: job.id,
    title: job.title || "",
    company: job.company || "",
    location: job.location || "",
    workplaceType: job.workplaceType || "",
    postedTimeAgo: job.postedTimeAgo || "",
    salary: job.salary || "",
    isEasyApply: Boolean(job.isEasyApply),
    url: job.url || "",
  }));
  console.log(JSON.stringify({
    success: true,
    totalResults: result.totalResults || jobs.length,
    jobCount: jobs.length,
    jobs,
  }));
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
