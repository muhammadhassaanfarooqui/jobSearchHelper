---
allowed-tools: Bash, Read, Write, Glob, Grep, Agent
---

# Daily Job Search: Find, Rank, Tailor, and Output PDFs

You are running the daily job search pipeline. Follow each step below precisely and autonomously.

## Step 1: Fetch Jobs

Run the Python script to fetch jobs from Google Jobs via SerpAPI:

```
cd /home/hassaan/workplace/jobSearchHelper/src && /home/hassaan/workplace/jobSearchHelper/.venv/bin/python fetch_jobs.py
```

This outputs `output/YYYY-MM-DD/jobs_raw.json`. Read that file.

If the script fails (e.g., missing API key), stop and tell the user what went wrong.

## Step 2: Read Resume

Read `resume.tex` from the project root. This is the base resume you'll tailor from.

Also check if `cover_letter_reference.tex` exists in the project root. If it does, read it and use its style/format as a template for cover letters. If it doesn't exist, use a standard professional cover letter format in LaTeX.

## Step 3: Read Config

Read `config.yaml` to get the user's info (name, email, phone, linkedin, location) and the `top_n` setting (default 5).

## Step 4: Rank Jobs

First, filter out any jobs that belong to **excluded industries** listed in `config.yaml` (e.g., banking, financial services, financial institutions). A job should be excluded if the hiring company is primarily a bank, credit union, financial institution, or financial services company — even if the role itself is a software engineering position. Remove these jobs from consideration entirely before scoring.

Score every remaining job in jobs_raw.json against the resume on a 0-100 scale. Consider:

- **Skills match (40%):** How well do the candidate's technical skills (Java, distributed systems, AWS ECS, AI tooling, etc.) match what the job requires?
- **Experience match (30%):** Does the candidate's seniority, years of experience, and domain (cloud infrastructure, container orchestration, backend systems) align?
- **Role fit (30%):** Is the job title/responsibilities a natural fit for someone with this background?

Select the top N jobs (from config, default 5). If fewer than N jobs were fetched, use all of them.

## Step 5: Process Each Top Job

For each selected job, do the following:

### 5a. Create output folder

Create `output/YYYY-MM-DD/company--role/` where company and role are slugified (lowercase, hyphens, no special chars, max 80 chars).

### 5b. Write job_details.md

Write a file with:
- Job title, company, location
- Overall match score and breakdown (skills/experience/fit)
- Key strengths: what makes the candidate a strong match
- Gaps to address: what the candidate should emphasize or acknowledge
- Full job description
- Apply links (from the job data)

### 5c. Tailor the resume

Read `resume.tex` and create `tailored_resume.tex` in the job's output folder. Tailoring rules:

- **Reorder bullet points** to lead with the most relevant experience for this role
- **Adjust the Professional Summary** to emphasize skills/experience most relevant to this job
- **Emphasize matching skills** in the Technical Skills section (reorder, adjust emphasis)
- **NEVER fabricate** experience, skills, projects, or metrics. Only rearrange and re-emphasize what's already there.
- **Keep the same LaTeX structure** and formatting as the original
- **Keep it to one page** — the resume must remain concise

### 5d. Write cover letter

Create `cover_letter.tex` in the job's output folder. The cover letter should:

- Be addressed to the hiring team at the specific company
- Use the user's info from config.yaml (name, email, phone, linkedin, location)
- Open with genuine enthusiasm for the specific role and company
- Connect 2-3 of the candidate's strongest relevant achievements to the job requirements (cite specific metrics from the resume)
- Show awareness of what the company does and why the candidate is drawn to it
- Close with a confident call to action
- Be roughly 3-4 paragraphs, fitting on one page
- Use clean LaTeX formatting matching the resume's style (same font package: carlito, same geometry)

### 5e. Compile to PDF

For each `.tex` file, compile to PDF:

```
cd /path/to/job/folder && pdflatex -interaction=nonstopmode tailored_resume.tex
cd /path/to/job/folder && pdflatex -interaction=nonstopmode cover_letter.tex
```

Verify the PDFs were created. If compilation fails, read the `.log` file, fix the LaTeX error, and retry once.

After successful compilation, clean up LaTeX build artifacts (`.aux`, `.log`, `.out` files) from the job folder.

## Step 6: Write Daily Summary

Create `output/YYYY-MM-DD/summary.md` with:

```markdown
# Job Search Results — YYYY-MM-DD

## Top Matches

| # | Company | Role | Score | Location |
|---|---------|------|-------|----------|
| 1 | ... | ... | 92 | ... |
| ... |

## Details

### 1. [Company] — [Role] (Score: XX/100)
- **Why it's a match:** 1-2 sentence summary
- **Apply:** [link]
- **Files:** `company--role/tailored_resume.pdf`, `company--role/cover_letter.pdf`

(repeat for each job)
```

Also create `output/YYYY-MM-DD/scored_jobs.json` with structured data for the dashboard. Use this exact schema:

```json
{
  "date": "YYYY-MM-DD",
  "total_fetched": 27,
  "total_after_filter": 13,
  "jobs": [
    {
      "rank": 1,
      "job_id": "company--role",
      "title": "Role Title",
      "company_name": "Company Name",
      "location": "City, ST",
      "remote": false,
      "salary": "$100,000-$130,000/year",
      "score": 78,
      "score_breakdown": {
        "skills": { "score": 36, "max": 40 },
        "experience": { "score": 20, "max": 30 },
        "fit": { "score": 22, "max": 30 }
      },
      "strengths": ["Strength 1", "Strength 2"],
      "gaps": ["Gap 1", "Gap 2"],
      "why_match": "One-liner summary of why this is a match",
      "apply_links": [{ "title": "LinkedIn", "link": "https://..." }],
      "folder": "company--role"
    }
  ]
}
```

Populate every field from the data you already have in context. `folder` must match the actual directory name created in Step 5a. `apply_links` should come from the raw job data. If salary is not available, use an empty string. Set `remote` to true/false based on the job details.

## Step 7: Generate Dashboard

Run the dashboard generator to create an interactive HTML dashboard:

```
cd /home/hassaan/workplace/jobSearchHelper/src && \
  /home/hassaan/workplace/jobSearchHelper/.venv/bin/python generate_dashboard.py \
  /home/hassaan/workplace/jobSearchHelper/output/YYYY-MM-DD
```

This produces `output/YYYY-MM-DD/dashboard.html`. If it fails, report the error but do not block the pipeline.

## Important Notes

- Use today's date (YYYY-MM-DD format) for all paths
- Work autonomously — don't ask for confirmation between steps
- If any single job fails (bad LaTeX, etc.), continue with the remaining jobs
- At the end, tell the user how many jobs were processed and where to find the output
