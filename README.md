# Job Search Helper

Automated daily job search pipeline. Scrapes LinkedIn, Indeed, Glassdoor, and ZipRecruiter, deduplicates against history, and generates an HTML dashboard with scored results.

## Setup

```bash
git clone https://github.com/muhammadhassaanfarooqui/jobSearchHelper.git
cd jobSearchHelper
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1. **Search config** -- Copy `config.example.yaml` to `config.yaml` and fill in your details (name, email, search queries, location preferences, filters):
   ```
   cp config.example.yaml config.yaml
   ```

2. **Resume** -- Copy `resume.example.tex` to `resume.tex` and replace with your own LaTeX resume:
   ```
   cp resume.example.tex resume.tex
   ```

## Usage

### One-command daily pipeline (recommended)

This project is designed to run end-to-end via [Claude Code](https://claude.com/claude-code). With Claude Code installed, run:

```
/find-jobs
```

This single command will:
1. Fetch jobs from LinkedIn, Indeed, Glassdoor, and ZipRecruiter
2. Filter out excluded companies and industries
3. Score and rank every job against your resume (skills 40%, experience 30%, fit 30%)
4. Pick the top N matches (configured in `config.yaml`)
5. For each top job: tailor your resume, write a cover letter, and compile both to PDF
6. Generate a daily summary and an interactive HTML dashboard

Output lands in `output/YYYY-MM-DD/` with per-job folders containing PDFs, details, and apply links.

### Manual scripts

**Fetch jobs only:**
```bash
python src/fetch_jobs.py
```
Writes `output/<date>/jobs_raw.json` with new job listings.

**Generate dashboard only:**
```bash
python src/generate_dashboard.py output/<date>
```
Reads `scored_jobs.json` from the given directory and produces `dashboard.html`.

### Prerequisites

- [Claude Code](https://claude.com/claude-code) (for the `/find-jobs` skill)
- `pdflatex` (for resume/cover letter PDF compilation)

## Project Structure

```
.claude/commands/
  find-jobs.md       # Claude Code skill — runs the full pipeline
src/
  fetch_jobs.py      # Scrape and filter jobs
  generate_dashboard.py  # Build HTML dashboard
  config.py          # Config loader
config.yaml          # Your search config (gitignored)
resume.tex           # Your resume (gitignored)
output/              # Daily results (gitignored)
history/             # Seen-job dedup history (gitignored)
```
