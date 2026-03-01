#!/usr/bin/env python3
"""Generate a self-contained HTML dashboard from scored_jobs.json."""

import json
import sys
from html import escape
from pathlib import Path

CSS = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: #f4f5f7; color: #1a1a2e; line-height: 1.5; padding: 24px;
}
.container { max-width: 820px; margin: 0 auto; }
header { margin-bottom: 28px; }
header h1 { font-size: 1.6rem; font-weight: 700; color: #1a1a2e; }
.stats {
  display: flex; gap: 16px; margin-top: 8px; font-size: 0.85rem; color: #555;
}
.stats span { background: #fff; padding: 4px 12px; border-radius: 6px; border: 1px solid #e0e0e0; }

.card {
  background: #fff; border-radius: 10px; padding: 20px 24px; margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e8e8e8;
  transition: box-shadow 0.15s;
}
.card:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.1); }

.card-header { display: flex; align-items: flex-start; gap: 16px; }
.score-badge {
  flex-shrink: 0; width: 48px; height: 48px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 1.1rem; color: #fff;
}
.score-green  { background: #22c55e; }
.score-amber  { background: #f59e0b; }
.score-red    { background: #ef4444; }

.card-info { flex: 1; min-width: 0; }
.card-info h2 { font-size: 1.05rem; font-weight: 600; margin-bottom: 2px; }
.card-info .company { font-size: 0.9rem; color: #555; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.tag {
  font-size: 0.75rem; padding: 2px 10px; border-radius: 12px;
  background: #f0f0f5; color: #444; border: 1px solid #e0e0e0;
}
.tag-remote { background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }

.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 7px 14px; border-radius: 7px; font-size: 0.82rem; font-weight: 500;
  text-decoration: none; border: 1px solid transparent; cursor: pointer;
  transition: opacity 0.15s;
}
.btn:hover { opacity: 0.85; }
.btn-apply  { background: #2563eb; color: #fff; }
.btn-resume { background: #f0fdf4; color: #166534; border-color: #bbf7d0; }
.btn-cover  { background: #fefce8; color: #854d0e; border-color: #fde68a; }
.btn[disabled] {
  opacity: 0.4; cursor: not-allowed; pointer-events: none;
}

.details-toggle {
  background: none; border: none; color: #2563eb; font-size: 0.82rem;
  cursor: pointer; padding: 0; margin-top: 12px; font-weight: 500;
}
.details-toggle:hover { text-decoration: underline; }

.details {
  display: none; margin-top: 14px; padding-top: 14px;
  border-top: 1px solid #eee;
}
.details.open { display: block; }

.breakdown { margin-bottom: 12px; }
.breakdown-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; font-size: 0.82rem; }
.breakdown-label { width: 80px; text-align: right; color: #555; }
.breakdown-bar-bg {
  flex: 1; height: 8px; background: #eee; border-radius: 4px; overflow: hidden;
}
.breakdown-bar {
  height: 100%; border-radius: 4px; background: #2563eb; transition: width 0.3s;
}
.breakdown-val { width: 50px; font-size: 0.78rem; color: #666; }

.detail-section h4 { font-size: 0.85rem; font-weight: 600; margin-bottom: 4px; color: #333; }
.detail-section ul { margin: 0 0 10px 18px; font-size: 0.82rem; color: #555; }
.detail-section p { font-size: 0.82rem; color: #555; margin-bottom: 10px; }
"""

JS = """\
function toggleDetails(btn) {
  var d = btn.nextElementSibling;
  var open = d.classList.toggle('open');
  btn.textContent = open ? '\\u25B2 Hide details' : '\\u25BC Show details';
}
"""


def score_class(score: int) -> str:
    if score >= 70:
        return "score-green"
    if score >= 50:
        return "score-amber"
    return "score-red"


def render_card(job: dict, output_dir: Path) -> str:
    folder = job.get("folder", "")
    score = job.get("score", 0)
    title = escape(job.get("title", "Unknown"))
    company = escape(job.get("company_name", "Unknown"))
    location = escape(job.get("location", ""))
    salary = escape(job.get("salary", ""))
    remote = job.get("remote", False)
    strengths = job.get("strengths", [])
    gaps = job.get("gaps", [])
    why = escape(job.get("why_match", ""))
    apply_links = job.get("apply_links", [])
    breakdown = job.get("score_breakdown", {})

    # Check PDFs
    resume_path = output_dir / folder / "tailored_resume.pdf"
    cover_path = output_dir / folder / "cover_letter.pdf"
    resume_exists = resume_path.exists()
    cover_exists = cover_path.exists()

    # Tags
    tags_html = ""
    if remote:
        tags_html += '<span class="tag tag-remote">Remote</span>'
    if location:
        tags_html += f'<span class="tag">{location}</span>'
    if salary:
        tags_html += f'<span class="tag">{salary}</span>'

    # Apply buttons
    apply_btns = ""
    for link_obj in apply_links:
        link_title = escape(link_obj.get("title", "Apply"))
        link_url = escape(link_obj.get("link", "#"))
        apply_btns += (
            f'<a class="btn btn-apply" href="{link_url}" target="_blank" '
            f'rel="noopener">{link_title}</a>'
        )
    if not apply_links:
        apply_btns = '<span class="btn btn-apply" disabled>No apply link</span>'

    resume_disabled = "" if resume_exists else " disabled"
    cover_disabled = "" if cover_exists else " disabled"
    resume_href = f'{escape(folder)}/tailored_resume.pdf' if resume_exists else "#"
    cover_href = f'{escape(folder)}/cover_letter.pdf' if cover_exists else "#"

    # Breakdown bars
    breakdown_html = ""
    for key, label in [("skills", "Skills"), ("experience", "Experience"), ("fit", "Fit")]:
        entry = breakdown.get(key, {})
        s = entry.get("score", 0)
        mx = entry.get("max", 1)
        pct = round(s / mx * 100) if mx else 0
        breakdown_html += (
            f'<div class="breakdown-row">'
            f'<span class="breakdown-label">{label}</span>'
            f'<div class="breakdown-bar-bg"><div class="breakdown-bar" style="width:{pct}%"></div></div>'
            f'<span class="breakdown-val">{s}/{mx}</span>'
            f'</div>'
        )

    strengths_html = "".join(f"<li>{escape(s)}</li>" for s in strengths)
    gaps_html = "".join(f"<li>{escape(g)}</li>" for g in gaps)

    return f"""<div class="card">
  <div class="card-header">
    <div class="score-badge {score_class(score)}">{score}</div>
    <div class="card-info">
      <h2>{title}</h2>
      <div class="company">{company}</div>
      <div class="tags">{tags_html}</div>
    </div>
  </div>
  <div class="actions">
    {apply_btns}
    <a class="btn btn-resume" href="{resume_href}" target="_blank"{resume_disabled}>Resume PDF</a>
    <a class="btn btn-cover" href="{cover_href}" target="_blank"{cover_disabled}>Cover Letter PDF</a>
  </div>
  <button class="details-toggle" onclick="toggleDetails(this)">\u25BC Show details</button>
  <div class="details">
    <div class="breakdown">{breakdown_html}</div>
    <div class="detail-section">
      <h4>Why it's a match</h4>
      <p>{why}</p>
    </div>
    {"<div class='detail-section'><h4>Strengths</h4><ul>" + strengths_html + "</ul></div>" if strengths_html else ""}
    {"<div class='detail-section'><h4>Gaps</h4><ul>" + gaps_html + "</ul></div>" if gaps_html else ""}
  </div>
</div>"""


def generate_dashboard(output_dir: Path) -> None:
    scored_path = output_dir / "scored_jobs.json"
    if not scored_path.exists():
        print(f"Error: {scored_path} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(scored_path.read_text())
    date = escape(data.get("date", "Unknown"))
    total_fetched = data.get("total_fetched", 0)
    total_after_filter = data.get("total_after_filter", 0)
    jobs = data.get("jobs", [])

    # Sort by score descending
    jobs.sort(key=lambda j: j.get("score", 0), reverse=True)

    cards_html = "\n".join(render_card(j, output_dir) for j in jobs)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Dashboard &mdash; {date}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Job Search Dashboard</h1>
    <div class="stats">
      <span>{date}</span>
      <span>{len(jobs)} matches from {total_fetched} jobs fetched</span>
      <span>{total_after_filter} passed filters</span>
    </div>
  </header>
  {cards_html}
</div>
<script>{JS}</script>
</body>
</html>"""

    out_path = output_dir / "dashboard.html"
    out_path.write_text(html)
    print(f"Dashboard written to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output-directory>", file=sys.stderr)
        sys.exit(1)
    generate_dashboard(Path(sys.argv[1]))
