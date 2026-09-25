# DischargeFlow — Project Brief (one page)

**What:** A clinician-in-the-loop discharge system. Structured discharge records in, plain-language
patient summaries out, with a reviewing clinician signing off on every draft.
**Type:** Proof of concept for the CellStrat *Claude Code Certified Architect* intensive. Synthetic data only.

## The journey
1. **Clinician submits** a structured discharge record (diagnoses, procedures, medications, follow-up, warning signs).
2. **Claude API drafts** a plain-language patient summary, grounded in uploaded reference summaries (RAG).
3. **A reviewing clinician approves or rejects** the draft. Rejection needs a reason; the agent learns from it.
4. Only an **approved** summary can be released to the patient.

## Extensions built during the day
- **RAG:** upload a sample discharge summary; retrieve its most relevant sections to ground each draft.
- **Agent:** one agent with **tools** (record lookup, reference search, readability check), **memory**
  (reviewer feedback), an **MCP server** (read-only access for Claude Code), and **hooks** (guardrails + audit).

## Stack
Python 3.12 · FastAPI + Uvicorn · SQLAlchemy / SQLite · pydantic v2 · httpx · pytest · Anthropic SDK · Streamlit · (mcp, Ex 10)

## Five rules that shape everything
1. **The AI drafts, a human decides.** No draft reaches a patient without a second clinician's approval.
2. **Doses are never floats and never written by the model.** Stored as integer `dose_x1000`; rendered from the database.
3. **Facts come from the record only.** References guide wording and structure, not patient facts.
4. **PHI never leaves the process unmasked** and never appears in logs.
5. **Untrusted text is data, not instructions** — clinical notes and uploaded references are fenced.

The detailed contract is **`docs/SPEC.md`**. The safety and data-handling policy is **`docs/POLICY.md`**.
