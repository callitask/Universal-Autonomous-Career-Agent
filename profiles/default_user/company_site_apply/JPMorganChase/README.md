# JPMorganChase workspace (structured-layout contract, 2026-10-14, profile-agnostic)

Inputs — base documents the agent refactors per requisition at runtime (workspace root is `README.md`-only):
- `resumes/BASE.md` — company-framed base resume (product-oriented, same stack)
- `cover_letters/BASE.md` — company base letter (tone reference + token template)
- `cover_letters/` — company input letters (base + references)
- `resumes/` — company input resume variants

Outputs — per-application role folders (profile-agnostic; any new slug, same flow):
- `APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<jobid>/` with FIXED `<Stem>_Resume.pdf` / `<Stem>_Cover_Letter.pdf` (Stem = Title-Cased profile, e.g. `first_last` → `First_Last`), mirrored flat AND inside `resume/` + `cover_letters/` subfolders, plus role `Cover_Letter.txt`/`.html`
- No job-id filename suffixes — requisitions coexist by folder, not by filename. Uploaders never trust DOM draft filenames: remove-if-filled + upload + content/mtime verify on the exact role path (glob legacy fallback only).

Blueprint only — never store live PII here. Live data resolves under `F:\Operations JOB AI AGENT\profiles\<slug>\`.
