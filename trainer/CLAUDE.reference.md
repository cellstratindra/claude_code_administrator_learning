# DischargeFlow

## What this is
A clinician-in-the-loop discharge system. PoC, not production, not a medical device. Synthetic data only.
Journey: a clinician submits a structured discharge record → Claude drafts a plain-language patient
summary grounded in reference summaries (RAG) → a *different* clinician approves or rejects → only an
approved summary is released to the patient.

## Source of truth
- @docs/SPEC.md is the contract (tables, requirement IDs FR/AI/SEC, API, traceability). Build to it.
- @docs/POLICY.md holds the safety, PHI and security rules.
- If a request conflicts with the spec, stop and ask. Propose a spec change; never silently diverge.
- Reference requirement IDs in docstrings, commit messages and test names (e.g. `test_fr10_four_eyes`).

## Stack
Python 3.12, FastAPI + Uvicorn, SQLAlchemy 2.x on SQLite (dischargeflow.db), pydantic v2, httpx,
python-multipart, pytest, anthropic SDK, Streamlit. `mcp` is pre-approved for Exercise 10 only.

## Layout
app/main.py, db.py, models.py, schemas.py, routes.py, drafting.py, rag.py, sanitize.py, safety.py, agent.py
mcp_server.py · ui/app.py · tests/ · samples/ (synthetic data, read-only)

## Conventions
- Type hints on every function. Docstrings on every endpoint and module.
- Doses are fixed-point integers `dose_x1000` + an explicit `dose_unit`. Never floats.
- The model never writes doses; the medication table is rendered from the database.
- Datetimes are UTC ISO-8601.
- Secrets from environment variables via python-dotenv; never hard-coded.

## Safety rules (never violate)
- PHI (name, MRN, DOB, phone, email, national IDs) is masked before any external API call and never logged.
- Untrusted text (clinical_course, notes, reference chunks) goes to the model only inside delimited data blocks.
- Four-eyes: reviewer_id must differ from submitted_by. Decisions are final (409 on re-decision).
- The Anthropic client is always mocked in tests. Tests run offline.

## Run and test
- Run API: python -m uvicorn app.main:app --reload
- Run UI:  streamlit run ui/app.py
- Test:    python -m pytest -q     (single: python -m pytest -q tests/test_api.py::test_fr10_four_eyes)

## Do not touch
- Do not edit .venv, .git, .env or dischargeflow.db directly.
- Do not add third-party dependencies without asking first.
- Do not invent endpoints, tables or fields that are not in docs/SPEC.md.
- Never print, log or commit API keys or PHI.
