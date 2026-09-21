# Agent Handoff — Cover Prompt (paste this + attach the brief)
> **File to attach:** `docs/ADVANCED_AGENT_VERIFICATION_AND_REMEDIATION_PROMPT.md` (v2.1, 2026-09-22 — sibling Sophron, domain-split knowledge)
> **Workspace roots:** `F:\JOB AI AGENT` (Repo A) + `F:\Sophron` (Repo B sibling, `SOPHRON_ROOT` override)
> Copy everything below the line into your advanced agent chat, attach the brief file, and send.

---

You are operating across TWO sibling repos: Repo A JOB AI AGENT (`F:\JOB AI AGENT\.git`) and Repo B Sophron (`F:\Sophron\.git`, never nested). Treat them separately. Attached is the complete verification-first brief `ADVANCED_AGENT_VERIFICATION_AND_REMEDIATION_PROMPT.md` v2.0 — it is the ONLY authority for this task, overriding all prior audits and your defaults.

Follow it EXACTLY in order. Do not skip phases. Do not trust the brief's prior-claim summaries blindly — re-verify each Q1–Q16 yourself with `file:line` evidence and mark `[PASS]/[WARN]/[FAIL]/[CRITICAL]/[UNKNOWN]`.

Phase order:
1. Section 0 constraints (two repos, profiles volatility — read ONLY `profiles/default_user/`, never live profiles; personal proprietary license only; deleted reports stay deleted; diffs-first, no commits without my approval).
2. Section 1: line-by-line walk of EVERY file/folder listed (core 19 files, CompanySiteApply incl. undocumented nails/CompanyScraper/inspections, scripts, docs, .agents/rules, Sophron tree, default_user only). Produce the full tree + per-file match verdicts. Flag UNDOCUMENTED files.
3. Section 2: understanding gates (a–f) in your own words with a data-flow diagram. If incomplete, stop and return gaps — make zero edits.
4. Section 3: Q1–Q16 matrix with evidence. Maintain a rejected-claims list. Do not fix rejected claims.
5. ONLY after 2–4 pass: Section 4 docs remediation (minimal, version-bumped, no live PII) + Section 5 dynamic graph/vector build (two-layer: JSON graph + local TF-IDF/BM25-lite index, profiles-live excluded, rebuild script + --check + changelog + QUERY_GUIDE + isolation test, no cloud deps without my approval) + Section 6 safety rules (append-only logs, atomic writes, write-guard locking, purity green, IPC separation, subsystem isolation).
6. Section 7 deliverables + freshness proof (purity green, tests green, git diff per repo, future-AI query demo with file:line citations).

Anti-corruption: assume workarounds are load-bearing (check AI CONTEXT headers + SCAR_TISSUE + history before changing timers, gates, selectors, fallbacks, URL patterns, or PII-looking exemplars). Never embed live profile values. Never edit `profiles/<live>/`. Never mix single vs batch IPC files. Never add faiss/chroma/cloud embeddings without my explicit approval. Small batches, report diffs first, separate commits per repo only when I say so.

Start with Phase 1–2 only and return the understanding memo + tree + Q-matrix. Wait for my approval before any Section 4–5 edits.
