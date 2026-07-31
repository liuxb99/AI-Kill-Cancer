# 需求回歸檢查報告（REVIEW-PHASE3F0-R3）

> 檢查範圍：`tasks/requirements.md` 附錄 B 逐條核對
> 檢查日期：2026-07-31

## B.1 P0-01（get_db 移除 auto commit + A 類改由 Service 管理）

- [x] get_db 移除 auto commit（session.py 全文無 `await session.commit()`，僅註解文字提及）
- [x] except rollback + finally close 保留（session.py L27-31）
- [x] A 類 12 檔案 / 21 endpoint 全部改由 Service 管理：
  | 檔案 | endpoint 數 | Service |
  |------|----|------|
  | patients.py | 3 | PatientService |
  | specimens.py | 1 | SpecimenService |
  | sequencing.py | 1 | SequencingTestService |
  | cases.py | 3 | CancerCaseService |
  | case_acl.py | 2 | CaseAccessService |
  | analyses.py | 1 | AnalysisRunService |
  | uploads.py | 1 | UploadService |
  | upload_vcf.py | 1 | VCFUploadService |
  | research.py | 1 | ResearchPaperService |
  | clinical.py | 4 | ClinicalPipelineService |
  | reports.py | 1 | ReportService |
  | ranking.py | 2 | DrugRankingService |
- [x] 支援性 repo 改 flush-only：decision_thread.py / reporting/repository.py / ranking/repository.py / crud.create_research_paper
- [x] API 層無 commit/rollback（grep 無結果）
- [x] REVIEW 註解保留並改 REVIEW-RESOLVED（含 RESOLUTION）

## B.2 P1-02（variants.py 錯誤處理）

- [x] catch-all 不再洩漏 str(e)
- [x] except HTTPException 4xx 透傳
- [x] 固定訊息 + error_id（request.state.request_id / X-Request-ID / uuid4）
- [x] REVIEW 註解保留並改 REVIEW-RESOLVED（含 RESOLUTION）

## B.3 驗證測試

- [x] test_phase3f0_r3_p0_transaction_boundary.py（5 測試，覆蓋 3 項驗證）→ 5 passed
- [x] test_phase3f0_r3_p1_variants_errors.py（2 測試，覆蓋 2 項驗證）→ 2 passed
- [x] 紅燈先行證據：4 FAILED / 3 PASSED → 綠燈：7 passed
- [x] 全量測試：1660 passed / 7 failed（預先存在技術債，git stash 驗證與本次修改無關）/ 23 skipped

## 總結

**全部 PASS → 可進入 Step 7 REVIEWER** ✅
