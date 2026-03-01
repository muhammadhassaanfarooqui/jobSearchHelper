#!/usr/bin/env python3
"""Fetch Software Engineer jobs using python-jobspy.

Scrapes LinkedIn, Indeed, Glassdoor, and ZipRecruiter. Filters by
location (preferred cities + remote), deduplicates against history,
and writes jobs_raw.json for Claude to process.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs

from config import PROJECT_ROOT, load_config


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80]


def load_seen_jobs(history_path: Path) -> set:
    """Load set of previously seen job IDs."""
    if history_path.exists():
        with open(history_path, "r") as f:
            data = json.load(f)
        return set(data.get("seen_ids", []))
    return set()


def save_seen_jobs(history_path: Path, seen_ids: set):
    """Persist seen job IDs to disk."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w") as f:
        json.dump({"seen_ids": sorted(seen_ids)}, f, indent=2)


def make_job_id(job: dict) -> str:
    """Create a unique-ish ID for deduplication from title + company."""
    title = slugify(job.get("title", "unknown"))
    company = slugify(job.get("company_name", "unknown"))
    return f"{company}--{title}"


def fetch_jobs_for_query(query: str, config: dict, location_override: str = None,
                         results_override: int = None) -> pd.DataFrame:
    """Run a single jobspy search and return results as a DataFrame."""
    search_config = config["search"]

    location = location_override or search_config.get("location", "Irving, TX")
    results_wanted = results_override or search_config.get("results_per_query", 20)
    # Skip distance filter for US-wide searches
    distance = None if location_override else search_config.get("distance_miles", 25)

    try:
        kwargs = dict(
            site_name=search_config.get("sites", ["indeed", "linkedin"]),
            search_term=query,
            location=location,
            results_wanted=results_wanted,
            hours_old=search_config.get("hours_old", 24),
            job_type=search_config.get("job_type", "fulltime"),
            description_format="markdown",
            linkedin_fetch_description=True,
            country_indeed="USA",
            is_remote=True if location_override else None,
        )
        if distance is not None:
            kwargs["distance"] = distance
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        jobs_df = scrape_jobs(**kwargs)
    except Exception as e:
        print(f"  [ERROR] jobspy request failed for '{query}': {e}", file=sys.stderr)
        return pd.DataFrame()

    return jobs_df


def _safe_str(value, default: str = "") -> str:
    """Convert a pandas value to str, treating NaN/None as *default*."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    s = str(value).strip()
    return s if s and s.lower() != "nan" else default


def normalize_job(row: pd.Series, query: str) -> dict:
    """Map a jobspy DataFrame row to our standard job schema."""
    # Build location string from available fields
    city = _safe_str(row.get("city"))
    state = _safe_str(row.get("state"))
    location_parts = [p for p in [city, state] if p]
    location = ", ".join(location_parts) if location_parts else _safe_str(row.get("location"))

    # Build apply link from job_url
    job_url = _safe_str(row.get("job_url"))
    site = _safe_str(row.get("site"))
    apply_links = [{"title": site.title(), "link": job_url}] if job_url else []

    # Build detected_extensions from available metadata
    detected_extensions = {}
    if pd.notna(row.get("date_posted")):
        detected_extensions["posted_at"] = str(row["date_posted"])
    if row.get("is_remote"):
        detected_extensions["remote"] = True
    salary_min = row.get("min_amount")
    salary_max = row.get("max_amount")
    if pd.notna(salary_min) and pd.notna(salary_max):
        interval = _safe_str(row.get("interval"), "yearly")
        detected_extensions["salary"] = f"${salary_min:,.0f}-${salary_max:,.0f}/{interval}"

    return {
        "title": _safe_str(row.get("title")),
        "company_name": _safe_str(row.get("company")),
        "location": location,
        "description": _safe_str(row.get("description")),
        "qualifications": [],
        "responsibilities": [],
        "apply_links": apply_links,
        "detected_extensions": detected_extensions,
        "source_query": query,
    }


def is_location_match(job: dict, config: dict) -> bool:
    """Check if a job matches preferred locations or is remote."""
    filters = config.get("filters", {})
    include_remote = filters.get("include_remote", True)
    preferred = filters.get("preferred_locations", [])

    # Check remote
    if include_remote and job.get("detected_extensions", {}).get("remote"):
        return True

    # Check preferred locations
    job_location = job.get("location", "").lower()
    for loc in preferred:
        # Extract city name (before the comma) for flexible matching
        city = loc.split(",")[0].strip().lower()
        if city in job_location:
            return True

    return False


def is_excluded(job: dict, excluded_companies: list) -> bool:
    """Check if job should be filtered out."""
    company = job.get("company_name", "").lower()
    return any(exc.lower() in company for exc in excluded_companies)


def main():
    config = load_config()

    today = date.today().isoformat()
    output_dir = PROJECT_ROOT / config["output"]["output_dir"] / today
    output_dir.mkdir(parents=True, exist_ok=True)

    history_path = PROJECT_ROOT / "history" / "seen_jobs.json"
    seen_ids = load_seen_jobs(history_path)

    excluded = config.get("filters", {}).get("excluded_companies", [])
    queries = config["search"]["queries"]

    all_jobs = []
    run_ids = set()  # dedup within this run

    # Collect all search batches: (label, queries_list, location_override, results_override)
    batches = [("local", queries, None, None)]

    remote_config = config.get("remote_search", {})
    if remote_config.get("enabled", False):
        remote_queries = remote_config.get("queries", [])
        remote_location = remote_config.get("location", "United States")
        remote_results = remote_config.get("results_per_query", 20)
        batches.append(("remote", remote_queries, remote_location, remote_results))

    total_queries = sum(len(b[1]) for b in batches)
    print(f"[fetch_jobs] Date: {today}")
    print(f"[fetch_jobs] Running {total_queries} queries ({len(batches)} batches)...")

    for batch_label, batch_queries, loc_override, res_override in batches:
        if batch_label == "remote":
            print(f"\n--- Remote US-wide queries ---")

        for query in batch_queries:
            print(f"\n  Query: \"{query}\"{' [remote US-wide]' if loc_override else ''}")
            jobs_df = fetch_jobs_for_query(query, config, location_override=loc_override,
                                           results_override=res_override)
            print(f"  Found {len(jobs_df)} raw results")

            for _, row in jobs_df.iterrows():
                job = normalize_job(row, query)
                job_id = make_job_id(job)
                job["job_id"] = job_id

                if job_id in seen_ids or job_id in run_ids:
                    print(f"    SKIP (seen): {job_id}")
                    continue

                if is_excluded(job, excluded):
                    print(f"    SKIP (excluded): {job['company_name']}")
                    continue

                if not is_location_match(job, config):
                    print(f"    SKIP (location): {job['location']} - {job['title']}")
                    continue

                run_ids.add(job_id)
                all_jobs.append(job)
                print(f"    ADD: {job_id}")

    # Write output
    output_file = output_dir / "jobs_raw.json"
    with open(output_file, "w") as f:
        json.dump({"date": today, "total_jobs": len(all_jobs), "jobs": all_jobs}, f, indent=2)

    # Update history
    seen_ids.update(run_ids)
    save_seen_jobs(history_path, seen_ids)

    print(f"\n[fetch_jobs] Done. {len(all_jobs)} new jobs written to {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
