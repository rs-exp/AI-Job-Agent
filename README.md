# AI Job Agent

A multi-source job discovery and candidate-fit platform. It ingests postings from several job boards, normalises them into a single internal contract, deduplicates, scores them against a candidate profile, and turns those scores into an auditable application workflow.

Built in Python on PostgreSQL. The scoring engine is deliberately deterministic and explainable — not because a model wouldn't help, but so that when a model is added there is a baseline to measure it against.

---

## The problem

Job search at volume is a data problem before it is a judgement problem. Postings arrive from different sources in different shapes, the same role appears on three boards, most listings are irrelevant, and the handful worth acting on get lost. Manually triaging a few hundred postings a week is not sustainable and is not repeatable.

This project treats that as a pipeline: collect, normalise, deduplicate, score, decide — with the state of every decision persisted so the system can be re-run without losing work already done.

---

## Architecture

```
                    ┌──────────────────────────────────────────┐
   Job boards  ───▶ │  scrapers/     common scraper interface  │
   (Remotive,       │                per-source implementations│
    Arbeitnow,      └────────────────────┬─────────────────────┘
    Greenhouse)                          │  raw payload (JSONB, preserved as-is)
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │  jobs_raw       immutable source evidence│
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │  services/     normalisation             │
                    │                relevance filtering       │
                    │                candidate suitability     │
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │  jobs_normalized  + dedupe metadata      │
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │  job_scores     versioned rule scoring   │
                    │                 fit bucket + red flags   │
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────┐
                    │  job_application_decisions               │
                    │  apply / review / save_for_later / skip  │
                    │  + manual override protection            │
                    └────────────────────┬─────────────────────┘
                                         ▼
                              Markdown + CSV reports

   agents/pipeline_runner.py orchestrates every stage and records each
   execution in pipeline_runs with per-stage counts, status and errors.
```

Each layer has one job and a stable contract with the next. Ingestion collects, it does not interpret. Normalisation interprets, it does not judge. Scoring judges, it does not decide. The decision layer decides, and a human can override it.

---

## Design decisions

These are the choices that shaped the system, and the reasoning behind them. They matter more than the feature list.

**Raw payloads are preserved immutably.** Every posting is stored as its complete original JSONB payload alongside searchable metadata. Parsing logic will always be wrong in some way that only becomes obvious later; keeping the source evidence means the normaliser can be improved and replayed over historical data without refetching from upstream APIs that may have rate limits, may have changed, or may no longer carry the posting.

**Ingestion is idempotent.** Records are upserted on a unique job URL using `ON CONFLICT`, so a repeated run refreshes existing rows rather than duplicating them. This bounds the work any re-run can perform — which matters now for database writes, and matters considerably more once a paid model sits in the pipeline and reprocessing unchanged content has a direct cost.

**Scoring is versioned, not overwritten.** Moving from `rule_v0.1` to `rule_v0.2` added rows rather than replacing them. Both versions' scores coexist on the same dataset, so successive scoring strategies are directly comparable instead of being taken on faith. This is the mechanism that will later let a model-based scorer be evaluated against the rule engine on identical inputs.

**The rule engine stays explainable.** Every score carries a fit bucket, red flags and a recommendation, so any ranking can be explained without inspecting the code. A deterministic, inspectable, cheap baseline is worth keeping even after a model is introduced — it is the control group.

**Relevance and suitability are separate concerns.** Whether a posting is the right *kind* of role and whether it suits *this* candidate are computed by separate modules. Collapsing them means a location or seniority constraint silently corrupts role classification, and the resulting score cannot be reasoned about.

**Human decisions are protected from the automation.** Manual overrides and applied records are never overwritten by subsequent pipeline runs. Any system that suggests actions to a person must not discard what that person already decided; without this, an automated run silently reverts real work.

**Failures are recorded, not swallowed.** The orchestrator writes every run to `pipeline_runs` with status, timestamps, per-stage counts and captured error messages, and marks failed runs as failed. Scraper failure handling is covered by tests, because upstream sources going down is a normal operating condition, not an exception.

---

## Pipeline stages

Run end to end with a single command via `agents/pipeline_runner.py`:

| Stage | Module | Output |
|---|---|---|
| Source access check | `agents/source_checker.py` | reachability of each configured source |
| Ingestion | `agents/*_ingestor.py`, `scrapers/` | `jobs_raw` — full JSONB payloads |
| Normalisation | `services/job_normalizer.py` | `jobs_normalized` — source-neutral schema |
| Deduplication | `agents/job_deduplicator.py` | canonical vs duplicate, with reason |
| Relevance + suitability | `services/job_relevance_filter.py`, `services/candidate_suitability_scorer.py` | per-posting relevance and fit signals |
| Scoring | `agents/job_match_scorer.py` | `job_scores` — score, fit bucket, red flags |
| Decisions | `agents/application_decision_generator.py` | `job_application_decisions` |
| Reporting | `agents/job_report_generator.py` | Markdown + CSV |

Every run is recorded in `pipeline_runs`.

---

## Data model

| Table | Purpose |
|---|---|
| `jobs_raw` | complete original payload as JSONB, unique on job URL |
| `jobs_normalized` | source-neutral fields plus dedupe metadata (`dedupe_key`, `is_duplicate`, `duplicate_of_job_id`, `dedupe_reason`) |
| `job_scores` | versioned scores with `scoring_version`, `fit_bucket`, red flags, `recommendation` |
| `job_application_decisions` | workflow state, constrained in SQL to valid statuses, with `manual_override`, `user_notes`, `applied_at` |
| `pipeline_runs` | one row per execution: status, timings, per-stage counts, error message |

Invalid workflow states are prevented by database constraints rather than by application convention.

---

## Project layout

```
agents/      ingestion, normalisation, dedupe, scoring, decisions, reporting, orchestrator
scrapers/    base_scraper interface + Remotive, Arbeitnow, Greenhouse, dummy (test double)
services/    relevance filtering, candidate suitability scoring, normalisation
database/    schema.sql, migrations, connection manager, repositories, viewers
models/      job model
utils/       logging
scripts/     operational and backfill scripts
tests/       unit tests per module
config/      candidate preferences and relevance rules
```

---

## Getting started

Requires Python 3.14 and PostgreSQL 16.

```bash
git clone https://github.com/rs-exp/AI-Job-Agent.git
cd AI-Job-Agent

python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

copy .env.example .env           # Linux/macOS: cp .env.example .env
                                 # then set your PostgreSQL connection details

copy data\candidate_profile.example.json data\candidate_profile.json
                                 # then edit it with your own profile

python database/apply_schema.py
python database/verify_tables.py

python agents/pipeline_runner.py
```

Inspect results:

```bash
python database/view_pipeline_runs.py
python database/view_job_scores.py
python database/view_application_decisions.py
```

Manage decisions manually:

```bash
python agents/application_decision_cli.py --list --status apply --limit 10
python agents/application_decision_cli.py --job-id <id> --decision applied --notes "Applied on company site"
```

A job marked manually is locked against future automated runs until explicitly unlocked.

---

## Configuration

`data/candidate_profile.json` holds the candidate profile used for scoring. It is gitignored; create it from `data/candidate_profile.example.json`.

`config/candidate_preferences.py` and `config/relevance_rules.py` hold the location, role-priority and keyword weightings used by relevance filtering and suitability scoring. These are currently in source rather than in the profile JSON; consolidating them into the profile is a known piece of tidying.

`data/sources.csv` lists the configured job sources. Sources are added by implementing the `scrapers/base_scraper.py` interface — the pipeline itself does not change.

---

## Testing

```bash
python -m pytest
```

Run it as `python -m pytest`, not bare `pytest` — the repository root needs to be on `sys.path` for the package imports to resolve.

Tests cover normalisation, relevance filtering, candidate suitability scoring, repository upsert behaviour, connection management, logging, each scraper, and scraper failure handling. A `dummy_scraper` provides a test double so source behaviour can be exercised without hitting live APIs.

---

## Roadmap

Clearly separated from what is built, because the distinction matters.

**Model-based evaluation layer.** A model independently re-scores shortlisted postings and its judgement is compared against the deterministic scorer on identical inputs. Disagreement is treated as calibration signal for tuning the rule engine, not as an automatic replacement for it. The versioned scoring already in place exists to make this comparison possible; the idempotency already in place exists to bound its cost.

**Automated resume tailoring.** Per-posting resume generation driven from the same scored and decisioned dataset.

**Additional sources.** The scraper interface is the extension point — a new source is a new implementation, not a change to the pipeline.

---

## Status

Actively developed. The ingestion, normalisation, deduplication, scoring, orchestration, decision and reporting layers are working end to end. The model layer is designed but not yet implemented — deliberately, so that the deterministic baseline it will be measured against is stable first.
