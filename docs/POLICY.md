# DischargeFlow — Clinical Safety, Security & Data Policy (PoC)

This policy is binding for humans and for Claude Code working in this repository.

## Clinical safety
- DischargeFlow is **not a medical device** and gives no medical advice. It drafts text for clinician review.
- Every draft is reviewed by a clinician **other than** the one who submitted the record (four-eyes rule).
- The model never produces doses, frequencies or durations. The medication table is rendered from structured data.
- Any medicine mentioned by the model that is not in the record is flagged to the reviewer.
- Reviewer decisions are final and immutable. Changes create a new draft version.

## Data handling
- **Synthetic data only.** Never paste real patient information into this repo, into prompts, or into Claude Code.
- PHI (name, MRN, date of birth, phone, email, national IDs, address) is masked before any call to an external API.
- PHI never appears in logs, audit events, error messages, MCP tool output or commit messages. Use `patient_ref`.
- The list endpoint and the MCP server return masked data only.

## Secrets
- API keys live in `.env` only. `.env` is git-ignored. Never hard-code, log, print or commit a key.
- If a key is exposed, rotate it in the Anthropic Console immediately and tell the trainer.

## AI inputs
- Clinical free text and uploaded reference documents are **untrusted**. They are passed to the model only inside
  delimited data blocks, with a system prompt forbidding the model from following instructions inside them.
- Model output is validated against a schema before it is stored. Invalid output is retried once, then failed safely.

## Engineering guardrails (enforced by Claude Code hooks from Exercise 9)
- Do not edit `.env`, `*.db` or anything in `.git/` directly.
- Do not add third-party dependencies without asking first (`mcp` is pre-approved for Exercise 10).
- Do not invent endpoints, tables or fields that are not in `docs/SPEC.md`. Propose a spec change instead.
- Tests must pass before work is considered done.
