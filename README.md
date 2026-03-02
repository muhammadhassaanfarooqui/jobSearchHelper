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

1. **API key** -- Copy `.env.example` to `.env` and add your [SerpAPI](https://serpapi.com/) key:
   ```
   cp .env.example .env
   ```

2. **Search config** -- Copy `config.example.yaml` to `config.yaml` and fill in your details (name, email, search queries, location preferences, filters):
   ```
   cp config.example.yaml config.yaml
   ```

3. **Resume** -- Copy `resume.example.tex` to `resume.tex` and replace with your own LaTeX resume:
   ```
   cp resume.example.tex resume.tex
   ```

## Usage

**Fetch jobs:**
```bash
python src/fetch_jobs.py
```
Writes `output/<date>/jobs_raw.json` with new job listings.

**Generate dashboard:**
```bash
python src/generate_dashboard.py output/<date>
```
Reads `scored_jobs.json` from the given directory and produces `dashboard.html`.

## Project Structure

```
config.yaml          # Your search config (gitignored)
resume.tex           # Your resume (gitignored)
.env                 # API keys (gitignored)
src/
  fetch_jobs.py      # Scrape and filter jobs
  generate_dashboard.py  # Build HTML dashboard
  config.py          # Config loader
output/              # Daily results (gitignored)
history/             # Seen-job dedup history (gitignored)
```
