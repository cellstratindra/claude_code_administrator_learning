# DischargeFlow — CCA Intensive course repo

**Course repo:** https://github.com/cellstratindra/claude_code_administrator_learning.git

Course repository for the CellStrat **Claude Code Certified Architect (CCA)** full-day intensive.
You will build **DischargeFlow**, a clinician-in-the-loop discharge system, *spec-first*, by directing Claude Code.

> This repo starts with **specifications and sample data only**. There is no application code yet — you build it
> in Exercises 4–11. Proof of concept, synthetic data, not a medical device.

## Start here
| File | What it is |
|---|---|
| `docs/BRIEF.md` | One-page product brief — read first |
| `docs/SPEC.md` | The contract: data model, requirements (FR/AI/SEC), API, traceability |
| `docs/POLICY.md` | Clinical safety, PHI and security rules |
| `samples/records/` | Synthetic discharge records to POST |
| `samples/references/` | Sample plain-language discharge summaries for RAG upload |
| `samples/attack/` | Payloads for the prompt-injection lab (Exercise 7) |
| `labs/` | Exercise 1–11 handouts |

## Setup (pre-work)
```bash
git clone https://github.com/cellstratindra/claude_code_administrator_learning.git dischargeflow
cd dischargeflow
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then put your real ANTHROPIC_API_KEY in .env
claude --version && claude doctor
```

## Target layout (what you will build)
```
app/
  main.py  db.py  models.py  schemas.py  routes.py
  drafting.py   # Claude API drafter (Ex 6)
  rag.py        # chunking + BM25 retrieval (Ex 6)
  sanitize.py   # PHI masking (Ex 7)
  safety.py     # medication cross-check + readability (Ex 6)
  agent.py      # tool-using discharge agent with memory + hooks (Ex 10)
mcp_server.py   # read-only MCP server (Ex 10)
ui/app.py       # Streamlit clinician console (Ex 11)
tests/          # pytest, one test per requirement ID (Ex 9)
.claude/        # Claude Code hooks (Ex 9)
```
