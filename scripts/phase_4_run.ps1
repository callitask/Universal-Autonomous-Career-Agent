Write-Host "==== 1. PARSER 7/7 ===="
python -m unittest CompanySiteApply/tests/test_parser_doctor.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==== 2. SOPHRON 9/9 ===="
python -m unittest Sophron/tests/test_master_agent_suite.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

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
