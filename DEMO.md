# WHOSE MONEY? — Demo Guide

Live app: https://bbmp-checker.vercel.app
(Open it a minute before a demo so the free-tier backend is awake.)

## 2-minute demo script

1. **Open the app.** Read the subtitle aloud: *"Public spending data already exists, but it's scattered across government datasets. We turn it into an easy-to-read, evidence-backed ward report."*
2. **Search `83`** (or click the suggested chip). Walk through the big amounts, the tender closing dates, and the gray **NO COMPLETION INFORMATION** badges. Key line: *"The public record simply ends at the tender stage, so we say so instead of inventing a status."*
3. **Scroll to work orders:** contractor names and payment amounts from 2021–26 records. Then grievances: *"1,249 grievances in 2024, shown as context, never as proof."*
4. **Click an evidence link.** The real OpenCity dataset opens in a new tab. *"Every claim links to the underlying public source."*
5. **Search `999`** to show the clean not-found card. **Search `Kamakshipalya`** to show the name lookup resolving to Ward 101.
6. **(Optional) Save this ward.** Sign in with the magic-link email, save a second ward, switch between them, and remove one with the ×. *"Auth is additive; the report never needs a login."*
7. Close with the disclaimer: *"A missing update or discrepancy does not by itself establish wrongdoing. This is a transparency tool, not an accusation engine."*

## Talking points

- **Honesty by design:** the checker is rule-based and conservative; it cannot output a status that isn't in the public data. That is the product's integrity story.
- **Transparent findings:** indicators are plain conditionals ("no completion status in public records"), not opaque scores. There are no corruption probabilities anywhere.
- **Full pipeline, no live scraping:** about 208K records are ingested once into Postgres, and each citizen search is 2–3 fast indexed queries.
- **Graceful degradation:** no LLM key means deterministic summaries; no auth variables means auth is hidden; database down means a clean 503 with a retry button.
- **Security:** the service key stays server-side; the browser uses only the anon key; Row Level Security is enabled on every table.
- **Data-quality work:** ward extraction from free text, fuzzy ward-name matching across ward-boundary changes, and safe normalization of amounts and dates (NULL for "Not Available").
