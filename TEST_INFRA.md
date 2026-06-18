# E2E Test Infra: AITranslator / 端到端測試架構

## Test Philosophy / 測試哲學

*   Opaque-box, requirement-driven. No dependency on internal implementation details. / 黑箱操作、需求驅動。不依賴內部具體程式碼設計。
*   Methodology: Category-Partition + BVA + Pairwise + Workload Testing. / 測試方法：分類劃分法、邊界值分析法、兩兩組合測試與工作負載測試。
*   Rigorous lifecycle testing from startup to shutdown. / 嚴格驗證從啟動到關閉的完整生命週期。

---

## Feature Inventory / 測試功能清單

| # | Feature / 測試功能 | Source Requirement / 需求來源 | Tier 1 | Tier 2 | Tier 3 |
|---|-------------------|-----------------------------|:------:|:------:|:------:|
| 1 | Startup & Shutdown / 程式啟動與關閉 | ORIGINAL_REQUEST Urgent Update | 5 | 5 | ✓ |
| 2 | Clean Build & Isolated Run / 乾淨編譯與獨立執行 | ORIGINAL_REQUEST R1, R2 | 5 | 5 | ✓ |
| 3 | ONNXRuntime OCR (CPU/GPU) / OCR 辨識 | ORIGINAL_REQUEST Follow-up 1 R1, R3 | 5 | 5 | ✓ |
| 4 | UI API Key Settings / API 金鑰設定 | ORIGINAL_REQUEST Follow-up 2 R4.1 | 5 | 5 | ✓ |
| 5 | Translation Engines / 翻譯引擎 (Google/Gemini/Qwen) | ORIGINAL_REQUEST Follow-up 2 R4.3 | 5 | 5 | ✓ |
| 6 | Translation Fallback / 翻譯備份機制 (Gemini -> Google) | ORIGINAL_REQUEST Follow-up 2 R4.4 | 5 | 5 | ✓ |
| 7 | Inpainting Text Removal / 影像文字塗抹抹除 | ORIGINAL_REQUEST Follow-up 2 R4.2 | 5 | 5 | ✓ |
| 8 | Reentrant Lock Deadlock Prevention / 死鎖防禦 | RLock Threading Bug Fix | 3 | 3 | ✓ |
| 9 | Interaction Drag & Suppress / 拖拉暫停重繪 | Suppress redraws during resize/drag | 4 | 4 | ✓ |

---

## Test Architecture & Invocation / 測試架構與執行

*   **Test Runner**: `pytest`
*   **Test Command**: `pytest e2e_tests/`
*   **Execution Flow**:
    1. Tests locate the built `AITranslator.exe`.
    2. Isolate executable and assets in a clean sandbox.
    3. Launch the application.
    4. Perform UI interaction checks (via pywinauto or checking logs/IPC channels).
    5. Gracefully terminate.
    6. Verify no resources or file locks are leaked.

*   **Directory Layout**:
    *   `e2e_tests/`
        *   `conftest.py`
        *   `test_tier1_feature_coverage.py`
        *   `test_tier2_boundary_corner.py`
        *   `test_tier3_cross_feature.py`
        *   `test_tier4_real_world.py`
