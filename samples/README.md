# Sample data — SYNTHETIC ONLY

Every name, MRN, date of birth, phone number and ID in this folder is **invented** for training.
Any resemblance to a real person is coincidental. The reference summaries are illustrative teaching
material, **not clinical guidance**.

| File | Used in |
|---|---|
| `records/appendectomy_record.json` | Ex 5 (first POST), Ex 6 (first draft) |
| `records/pneumonia_record.json` | Ex 5–6 (second record; shows retrieval picking a different reference) |
| `references/ref_laparoscopic_appendectomy.md` | Ex 6 RAG upload |
| `references/ref_community_acquired_pneumonia.md` | Ex 6 RAG upload |
| `references/ref_heart_failure.md` | Ex 6 RAG upload (distractor: should NOT be retrieved for the two records) |
| `attack/injection_record.json` | Ex 7 direct prompt injection via clinical notes |
| `attack/poisoned_reference.md` | Ex 7 indirect injection via an uploaded reference (RAG poisoning) |

Doses use fixed-point integers: `dose_x1000` = dose × 1000. `500 mg` → `"dose_x1000": 500000, "dose_unit": "mg"`.
