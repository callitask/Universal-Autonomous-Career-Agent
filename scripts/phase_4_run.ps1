Write-Host "==== 1. PARSER 7/7 ===="
python -m unittest CompanySiteApply/tests/test_parser_doctor.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==== 2. SOPHRON (external repo — run from F:\Sophron separately) ===="
Write-Host "     Sophron was extracted to F:\Sophron on 2026-09-22. Run its test suite from that directory."
Write-Host "     Skipping to avoid FileNotFoundError. (Fix #9 — 2026-09-23)"
# Note: was: python -m unittest Sophron/tests/test_master_agent_suite.py
# That path no longer exists inside this repo. No exit code check needed.

Write-Host "`n==== 3. BUILD --BUILD ===="
python scripts/build_knowledge_index.py --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==== 4. BUILD --CHECK Exit 0 ===="
python scripts/build_knowledge_index.py --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==== 5. KNOWLEDGE 6/6 ===="
python -m unittest tests/test_knowledge_index.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==== 6. PURITY True[] ===="
python -c "from core.utils.profile_context import ProfileContext; ctx = ProfileContext('profiles/default_user'); print(ctx.verify_codebase_purity())"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==== 7. QUERY DEMO ===="
python scripts/build_knowledge_index.py --query "batch_question IPC" --top 3
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
