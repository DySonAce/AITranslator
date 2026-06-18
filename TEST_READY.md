# E2E Test Suite Ready / E2E 測試套件準備狀態

## Test Runner / 測試執行

*   **Command**: `pytest e2e_tests/`
*   **Expected Outcome**: All tests pass with exit code 0. / 預期結果：所有測試通過且退出碼為 0。

---

## Coverage Summary / 測試覆蓋率摘要

| Tier / 測試層級 | Count / 測試數量 | Description / 說明 |
|----------------|-----------------:|--------------------|
| 1. Feature Coverage | 35 | 5 tests per major feature. / 每個核心功能 5 個測試。 |
| 2. Boundary & Corner | 35 | Boundary conditions and edge cases. / 邊界條件與邊緣測試。 |
| 3. Cross-Feature | 10 | Pairwise interaction testing between features. / 功能間的兩兩組合互動測試。 |
| 4. Real-World Application | 5 | Complex real-world application scenarios. / 實際應用的複雜整合場景。 |
| **Total / 總計** | **85** | |

---

## Feature Checklist / 測試功能查檢表

| Feature / 測試功能 | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|-------------------|:------:|:------:|:------:|:------:|
| Program Startup & Shutdown / 程式啟動與關閉 | 5 | 5 | ✓ | ✓ |
| Clean Build & Isolated Run / 乾淨編譯與獨立執行 | 5 | 5 | ✓ | ✓ |
| ONNXRuntime OCR (CPU/GPU) / OCR 辨識 | 5 | 5 | ✓ | ✓ |
| UI API Key Settings (OpenRouter) / 金鑰設定 | 5 | 5 | ✓ | ✓ |
| Translation Engines (Google, Gemini, Qwen) / 三種翻譯引擎 | 5 | 5 | ✓ | ✓ |
| Translation Fallback (Gemini -> Google) / 翻譯失敗自動降級 | 5 | 5 | ✓ | ✓ |
| Inpainting Basic Functionality / 影像背景文字抹除 | 5 | 5 | ✓ | ✓ |
| Drag Suppress & Deadlock / 拖拉不卡頓與死鎖防禦 | 3 | 3 | ✓ | ✓ |
