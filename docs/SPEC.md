# DischargeFlow — Product & Technical Specification

> **Status:** v1.0 (course baseline) · **Owner:** CellStrat CCA Intensive · **Type:** Proof of concept, not a medical device
>
> This file is the **single source of truth** for the build. Every endpoint, table, prompt rule
> and test in the course traces back to a requirement ID in this document (see §11). If code and
> spec disagree, the spec wins until the spec is deliberately changed. Claude Code must **not**
> invent behaviour that is not written here; it must ask.

---

## 1. Problem and purpose

Discharge summaries are written for clinicians. Patients go home with a document full of
abbreviations ("s/p lap appy, POD2, tol PO, D/C on abx"), misunderstand their medicines and
warning signs, and come back. DischargeFlow turns a **structured discharge record** into a
**plain-language patient summary**, drafted by the Claude API and **signed off by a reviewing
clinician before any patient ever sees it**.

**The one journey:**

```
Clinician submits a structured discharge record
        → Claude drafts a plain-language patient summary (grounded by reference summaries)
        → A second, reviewing clinician approves or rejects the draft
        → Only an approved draft can be released to the patient
```

**Safety posture (non-negotiable):** the AI is a *drafting assistant*. It never makes the final
decision, never invents clinical facts, and never writes a dose. A human signs every draft.

## 2. Actors

| Actor | Description | Can |
|---|---|---|
| **Submitting clinician** | Doctor who discharges the patient | Create records, request drafts |
| **Reviewing clinician** | A *different* clinician who checks the draft | Approve / reject drafts |
| **Patient** | Receives the released summary | Read the approved summary only |
| **Claude API** | External LLM (Anthropic) | Draft text from masked, fenced data |
| **Discharge agent** (Ex 10) | In-app agent with tools and memory | Assemble a draft via tools |
| **Claude Code / MCP client** | Developer tooling | Read-only queries via MCP server |

## 3. Scope

**In scope (PoC):** record submission with structured medications; AI draft generation; reference
upload + retrieval (RAG); review workflow with four-eyes rule; patient-summary release; PHI masking
before egress; prompt-injection defence; audit trail; one tool-using agent with memory; a read-only
MCP server; Claude Code hooks; a Streamlit clinician console; pytest suite.

**Out of scope (listed in the production-gap audit, Ex 11):** real authentication/SSO, EHR/HL7/FHIR
integration, multi-language output, e-signatures, Postgres, deployment, regulatory certification,
real patient data. **Only synthetic data from `samples/` is used in the course.**

## 4. Glossary

| Term | Meaning |
|---|---|
| Discharge record | Structured clinical input for one hospital stay |
| Draft | One AI-generated version of the patient summary for a record (versions 1, 2, 3 …) |
| Reference document | An uploaded, clinician-approved example discharge summary used for RAG grounding |
| Chunk | A retrievable slice (~120–200 words) of a reference document |
| PHI | Protected health information: name, MRN, DOB, phone, email, national IDs, address |
| Four-eyes rule | The reviewer must not be the clinician who submitted the record |
| `dose_x1000` | Fixed-point integer dose: the dose multiplied by 1000 (2.5 mg → `2500`, unit `mg`) |

## 5. Domain model

### 5.1 Tables

**`discharge_records`**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| patient_ref | TEXT, unique, not null | Pseudonymous id, e.g. `PT-0001`. Safe to log. |
| patient_name | TEXT, not null | **PHI** |
| mrn | TEXT, not null | **PHI** (medical record number) |
| date_of_birth | DATE, not null | **PHI** |
| patient_phone | TEXT, nullable | **PHI** |
| admission_date | DATE, not null | |
| discharge_date | DATE, not null | ≥ admission_date |
| primary_diagnosis | TEXT, not null | |
| secondary_diagnoses | TEXT (JSON array) | may be `[]` |
| procedures | TEXT (JSON array) | may be `[]` |
| clinical_course | TEXT, not null | Free text written by clinician. **Untrusted** for prompting. |
| follow_up | TEXT, not null | Appointments / tests |
| warning_signs | TEXT, not null | When to seek urgent care |
| activity_and_diet | TEXT, nullable | |
| submitted_by | TEXT, not null | Clinician id, e.g. `dr.mehta` |
| status | TEXT, not null | `submitted` · `awaiting_review` · `changes_requested` · `approved` |
| created_at / updated_at | DATETIME (UTC) | |

**`medications`** (many per record)

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| record_id | FK → discharge_records.id | cascade delete |
| name | TEXT, not null | Generic name, e.g. `paracetamol` |
| dose_x1000 | INTEGER, not null, > 0 | **Never a float.** 500 mg → `500000`; 0.125 mg → `125` |
| dose_unit | TEXT enum | `mg` `mcg` `g` `mL` `units` `tablet` `puff` `drop` |
| route | TEXT enum | `oral` `iv` `im` `sc` `inhaled` `topical` `other` |
| frequency | TEXT, not null | e.g. `every 6 hours as needed, max 4 doses/day` |
| duration_days | INTEGER, nullable | null = ongoing |
| change_type | TEXT enum | `new` · `changed` · `continued` · `stopped` |
| notes | TEXT, nullable | Untrusted free text |

**`summary_drafts`** (many per record)

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| record_id | FK | |
| version | INTEGER, not null | 1, 2, 3… per record; unique (record_id, version) |
| status | TEXT | `pending_review` · `approved` · `rejected` · `generation_failed` |
| content_json | TEXT (JSON) | Validated `DraftContent` (§7.2); null if failed |
| citations_json | TEXT (JSON array) | Chunk ids used for grounding |
| safety_flags_json | TEXT (JSON array) | e.g. `["reading_grade_high","unknown_medication:ibuprofen"]` |
| reading_grade | INTEGER (×10) | Flesch–Kincaid grade × 10, e.g. `72` = grade 7.2 |
| model / prompt_version / drafter_mode | TEXT | Provenance; `drafter_mode` = `single` or `agent` |
| input_tokens / output_tokens | INTEGER | Cost telemetry |
| error_code | TEXT, nullable | Set when `generation_failed` |
| created_at | DATETIME (UTC) | |

**`reviews`** — id, draft_id FK (unique: one decision per draft), reviewer_id, decision
(`approved`/`rejected`), reason (required when rejected), created_at.

**`reference_documents`** — id, title, source_filename, uploaded_by, char_count, created_at.
**`reference_chunks`** — id, document_id FK, chunk_index, text, created_at.

**`audit_events`** — id, at (UTC), actor, action, entity_type, entity_id, detail_json.
**No PHI is ever written to `audit_events` or to logs.** Use `patient_ref`, never `patient_name`.

**`agent_memory`** (Ex 10) — id, scope (`global` or a diagnosis keyword), note, source
(`review:<id>`), created_at. Populated from rejection reasons; read by the agent's recall tool.

### 5.2 State machines

```
Record:  submitted ──(draft created)──▶ awaiting_review ──(approve)──▶ approved  [terminal]
                                             │
                                             └──(reject)──▶ changes_requested ──(new draft)──▶ awaiting_review

Draft:   pending_review ──▶ approved | rejected           (terminal, immutable)
         generation_failed                                  (terminal; record status unchanged)
```

Invariants: at most **one** `pending_review` draft per record; an `approved` record accepts no new
drafts; approved/rejected drafts are never edited — a change means a new version.

## 6. Functional requirements

Format: **ID — requirement** · *Acceptance criteria* (Given/When/Then). Status codes are part of the contract.

### Records
- **FR-01 — Submit a discharge record.** `POST /discharges` with the fields in §5.1 and a
  non-empty `medications` array. *Given a valid body, then 201 and the record with `status=submitted`,
  an `id`, and medications echoed with integer `dose_x1000`.*
- **FR-02 — Validate clinical input.** *Then 422 when:* `discharge_date < admission_date`;
  `dose_x1000 ≤ 0` or not an integer; unknown `dose_unit`/`route`/`change_type`; `patient_ref`
  not matching `^PT-\d{4,}$`; empty `primary_diagnosis`, `clinical_course`, `warning_signs` or
  `follow_up`. Duplicate `patient_ref` → 409.
- **FR-03 — Read records.** `GET /discharges/{id}` returns the full record (404 if missing).
  `GET /discharges?status=` lists records **without PHI**: `id, patient_ref, patient_initials,
  primary_diagnosis, discharge_date, status, submitted_by`.

### Drafting
- **FR-04 — Request a draft.** `POST /discharges/{id}/drafts` with `{ "requested_by": "<clinician>" }`.
  *Then 201 with a draft at `version = previous + 1`, `status=pending_review`, and the record
  moves to `awaiting_review`.* 409 if a `pending_review` draft already exists or the record is
  `approved`. 404 if the record is missing.
- **FR-05 — Draft content contract.** Every successful draft stores a `DraftContent` object (§7.2)
  and a server-rendered `medication_table` built **from the `medications` rows, never from model
  output**.
- **FR-06 — Graceful AI failure.** If the Claude call errors, times out, or returns output that
  fails validation after **one** retry, store a draft with `status=generation_failed` and an
  `error_code` (`ai_unavailable` · `ai_invalid_output`), leave the record status unchanged, and
  return **503** `{detail, draft_id}`. Never 500.
- **FR-07 — Draft history.** `GET /discharges/{id}/drafts` returns all versions, newest first.
  `GET /drafts/{draft_id}` returns one (404 if missing).

### Review (clinician-in-the-loop)
- **FR-08 — Approve.** `POST /drafts/{id}/approve` `{ "reviewer_id": "..." }`. *Given a
  `pending_review` draft and a reviewer ≠ `submitted_by`, then 200, draft `approved`, record
  `approved`, a `reviews` row and an audit event are written.*
- **FR-09 — Reject with a reason.** `POST /drafts/{id}/reject` `{ "reviewer_id", "reason" }`.
  `reason` is required, ≥ 10 characters (422 otherwise). Draft → `rejected`, record →
  `changes_requested`. The reason is saved to `agent_memory` (FR-15).
- **FR-10 — Four-eyes rule.** Approve/reject by the submitting clinician → **403**.
- **FR-11 — Decisions are final.** Approve/reject on a draft that is not `pending_review` → **409**.
- **FR-12 — Patient release.** `GET /discharges/{id}/patient-summary` returns the approved draft
  rendered for the patient: real patient name re-inserted locally, medication table, and an
  approval stamp `"Reviewed and approved by <reviewer_id> on <UTC date>"`. **409** if the record is
  not `approved`. The response never includes MRN, DOB or phone.

### RAG grounding
- **FR-13 — Upload a reference.** `POST /references` (multipart `.md`/`.txt`, ≤ 200 KB, UTF-8) with
  `title` and `uploaded_by`. The text is split into chunks on headings/paragraphs (~120–200 words,
  no chunk > 1,500 chars). *Then 201 `{id, title, chunk_count}`.* 415 for other file types,
  413 if too large. `GET /references` lists documents with chunk counts.
- **FR-14 — Retrieve and cite.** Before drafting, retrieve the top **k = 3** chunks by a
  dependency-free BM25 score over `primary_diagnosis + procedures`. Pass them to the model as
  reference material and store their ids in `citations_json`. If no references exist, draft anyway
  with `citations=[]` and flag `no_grounding`. References shape **structure and wording only** —
  patient facts come only from the record (AI-03).

### Agent, memory, MCP (Ex 10)
- **FR-15 — Reviewer-feedback memory.** Each rejection reason is stored as an `agent_memory` note
  scoped to the record's primary-diagnosis keyword. The agent can recall notes for a scope.
- **FR-16 — Agent drafter mode.** When `DRAFTER_MODE=agent`, `POST /discharges/{id}/drafts` uses
  the discharge agent (§8) instead of the single call. Same contract as FR-04..FR-06;
  `drafter_mode='agent'` is recorded.
- **FR-17 — Read-only MCP server.** `mcp_server.py` exposes `list_pending_drafts`, `get_draft`,
  `search_references` and `get_review_stats`. **No tool can approve, reject or create anything.**
  All outputs are PHI-masked.

### Operations
- **FR-18 — Audit trail.** Record created, draft requested/created/failed, approved, rejected,
  reference uploaded, and every agent tool call → one `audit_events` row each (no PHI).
- **FR-19 — Health.** `GET /health` → `{status:"ok", db:"ok", records:<n>, pending_drafts:<n>}`.
- **FR-20 — Review queue.** `GET /review-queue?limit=n` (1 ≤ n ≤ 50, default 10) returns the
  oldest `pending_review` drafts first, and `oldest_wait_hours` (null when the queue is empty).

## 7. AI requirements

### 7.1 Call rules
- **AI-01** Key from `ANTHROPIC_API_KEY`, model from `ANTHROPIC_MODEL` (default `claude-sonnet-4-6`),
  `max_tokens ≤ 1500`, request timeout 30 s. All via `.env` + python-dotenv.
- **AI-02** Output is **strict JSON** matching `DraftContent`, validated with pydantic. One retry on
  invalid output, then FR-06.
- **AI-03** Patient facts (diagnosis, procedures, dates, instructions) come **only** from the
  record. Reference chunks are style/structure/education guidance and are never copied as facts
  about this patient.
- **AI-04** The model never writes doses. After generation, any medicine name found in the prose
  that is not in the record's `medications` adds `unknown_medication:<name>` to `safety_flags`
  (reviewer sees it highlighted).
- **AI-05** Target reading level ≤ grade 8 (Flesch–Kincaid, computed locally, no new
  dependency). Above 8 → flag `reading_grade_high`. Flags inform the reviewer; they don't block.
- **AI-06** `prompt_version` (e.g. `draft-v3`), `model`, token counts stored on every draft.

### 7.2 `DraftContent` schema

```json
{
  "greeting": "string — uses the token [PATIENT] instead of a name",
  "what_happened": "string, 2–5 sentences",
  "your_diagnosis": "string, plain language, abbreviations expanded",
  "your_medicines_explained": "string — purpose of each medicine in words; NO doses or numbers",
  "warning_signs": ["string", "..."],
  "follow_up": ["string", "..."],
  "activity_and_diet": "string",
  "questions_to_ask": ["string", "..."]
}
```

## 8. The discharge agent (Ex 10)

One agent built on the Anthropic SDK tool-use loop, `MAX_STEPS = 6`.

| Tool | Purpose | Side effects |
|---|---|---|
| `get_discharge_record(record_id)` | PHI-masked record + medications | none |
| `search_references(query, k)` | BM25 over reference chunks | none |
| `recall_reviewer_feedback(scope)` | Memory notes from past rejections | none |
| `check_readability(text)` | Flesch–Kincaid grade | none |
| `submit_draft(content)` | Final answer, validated against `DraftContent` | ends the loop |

**Hooks (in-app):** `before_tool(name, args)` validates args, blocks unknown tools, and masks PHI
in outputs; `after_tool(name, args, result)` writes an audit event. **Memory:** `agent_memory`
table (FR-15). **Exceeding MAX_STEPS** or never calling `submit_draft` → FR-06 failure path.

## 9. Security, privacy and safety requirements

- **SEC-01** All write endpoints require header `X-API-Key` matching `DISCHARGE_API_KEY` → 401 otherwise.
- **SEC-02** Untrusted text (clinical_course, notes, reference chunks) is passed to the model only
  inside delimited blocks (`<discharge_record>…</discharge_record>`,
  `<reference_material>…</reference_material>`). The system prompt states that content inside
  these blocks is data, never instructions.
- **SEC-03** PHI is masked **before** any data leaves the process: patient name → `[PATIENT]`,
  MRN → `[MRN]`, DOB → `[DOB]`, phone → `[PHONE]`, email → `[EMAIL]`, 12-digit national-ID-like
  numbers → `[ID]`. The name is re-inserted locally only when rendering the released summary (FR-12).
- **SEC-04** No PHI in logs, audit events, MCP output, error messages or exceptions.
- **SEC-05** Secrets only in `.env` (git-ignored). `.env.example` has placeholders only.
- **SEC-06** Claude Code project hooks block edits to `.env`, `*.db` and `.git/`, and run the test
  suite after every file edit (Ex 9).
- **SEC-07** Every draft and the patient summary carry the notice: *"This summary was drafted with
  AI assistance and reviewed by your care team. If anything here differs from what your doctor
  told you, follow your doctor's advice and call the hospital."*

## 10. Non-functional requirements

- **NFR-01** Python 3.12 (3.10+), FastAPI, SQLAlchemy 2.x on SQLite (`dischargeflow.db`), pydantic v2,
  httpx, python-multipart (file upload), pytest, anthropic, streamlit. New dependencies need explicit approval (only `mcp` is
  pre-approved, for Ex 10).
- **NFR-02** All datetimes stored and returned in UTC ISO-8601.
- **NFR-03** The full test suite runs **offline**: the Anthropic client is always mocked in tests.
- **NFR-04** Type hints on every function; docstrings on every endpoint and module.
- **NFR-05** Error bodies follow FastAPI's `{"detail": ...}` shape; no stack traces to clients.

## 11. API contract summary

| Method | Path | Req | Success | Errors |
|---|---|---|---|---|
| POST | `/discharges` | FR-01/02 | 201 | 401, 409, 422 |
| GET | `/discharges` | FR-03 | 200 (no PHI) | 422 |
| GET | `/discharges/{id}` | FR-03 | 200 | 404 |
| POST | `/discharges/{id}/drafts` | FR-04..06, 16 | 201 | 401, 404, 409, 503 |
| GET | `/discharges/{id}/drafts` | FR-07 | 200 | 404 |
| GET | `/drafts/{draft_id}` | FR-07 | 200 | 404 |
| POST | `/drafts/{draft_id}/approve` | FR-08, 10, 11 | 200 | 401, 403, 404, 409 |
| POST | `/drafts/{draft_id}/reject` | FR-09, 10, 11 | 200 | 401, 403, 404, 409, 422 |
| GET | `/discharges/{id}/patient-summary` | FR-12 | 200 | 404, 409 |
| POST | `/references` | FR-13 | 201 | 401, 413, 415, 422 |
| GET | `/references` | FR-13 | 200 | |
| GET | `/review-queue?limit=n` | FR-20 | 200 | 422 |
| GET | `/health` | FR-19 | 200 | |

## 12. Traceability matrix

| Requirement | Built in | Proven by (pytest, `tests/`) |
|---|---|---|
| FR-01, FR-02 | Ex 4–5 | `test_fr01_submit_record`, `test_fr02_rejects_float_dose`, `test_fr02_discharge_before_admission` |
| FR-03 | Ex 5 | `test_fr03_list_has_no_phi` |
| FR-04, FR-05, FR-07 | Ex 5–6 | `test_fr04_draft_versioning`, `test_fr05_med_table_from_db` |
| FR-06 | Ex 6 | `test_fr06_ai_failure_returns_503_and_failed_draft` |
| FR-08 … FR-11 | Ex 5 | `test_fr08_approve`, `test_fr09_reject_requires_reason`, `test_fr10_four_eyes`, `test_fr11_double_decision_409` |
| FR-12 | Ex 5–7 | `test_fr12_release_only_when_approved`, `test_fr12_release_has_no_mrn_dob` |
| FR-13, FR-14 | Ex 6 | `test_fr13_upload_chunks`, `test_fr14_retrieval_picks_matching_reference` |
| FR-15, FR-16 | Ex 10 | `test_fr15_rejection_becomes_memory`, `test_fr16_agent_submits_valid_draft` |
| FR-17 | Ex 10 | `test_fr17_mcp_tools_are_read_only` |
| FR-20 | Ex 8 | `test_fr20_review_queue_empty`, `test_fr20_review_queue_limit` |
| AI-02, AI-04, AI-05 | Ex 6 | `test_ai02_retry_then_fail`, `test_ai04_unknown_medication_flag`, `test_ai05_reading_grade` |
| SEC-01 | Ex 5 | `test_sec01_write_requires_api_key` |
| SEC-02 | Ex 7 | `test_sec02_injection_is_fenced` |
| SEC-03, SEC-04 | Ex 7 | `test_sec03_mask_phi`, `test_sec03_payload_has_no_phi` |
| SEC-06 | Ex 9 | Manual: hook blocks an edit to `.env` |

## 13. Definition of done (PoC)

1. Every FR/AI/SEC row in §12 has a passing test (or a documented manual check).
2. `python -m pytest -q` is green twice in a row, offline.
3. The full journey runs in the Streamlit console: submit → draft → reject with reason → redraft
   (agent recalls the feedback) → approve → release.
4. README, HANDOFF, one ADR, and `docs/PRODUCTION-GAP.md` exist and match the code.
