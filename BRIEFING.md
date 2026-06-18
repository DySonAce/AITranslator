# Briefing & Version History / 開發任務簡報與版本歷程

## Current Mission / 當前任務狀態

Resolved critical issues to stabilize AITranslator modes and UI responsiveness. Fully completed React integration and bilingual translation support.
修復了 AITranslator 各種核心模式切換、死鎖及 UI 互動效能 Bug，並完成 React 整合與說明文件的中英雙語對照。

---

## Key Bug Fixes & Optimizations / 關鍵 Bug 修復與最佳化

### 1. Reentrant Lock Deadlock Fix / 可重入鎖死鎖修復
- **Problem**: Double locking in main thread caused UI freezes and Windows "Not Responding" crashes on anchor region release.
- **Fix**: Replaced `threading.Lock` with `threading.RLock` in `AppBackend`.
- **問題**：在主執行緒中釋放錨點選區時，會觸發重複獲取鎖，造成自我死鎖並引發 Windows「程式沒有回應」崩潰。
- **修復**：將 `AppBackend` 內的 `self.anchor_lock` 更改為 `RLock` 可重入鎖，徹底免除死鎖。

### 2. Suppressed Redraws during Drag & Resize / 拖拉縮放時暫停重繪
- **Problem**: Async translation results returning during window resize/drag forced Qt UI updates, disrupting layout events and making dragging extremely laggy or crashing.
- **Fix**: Added check `if self.is_interacting: return` in `set_image`. SUPPRESSED image updates while resizing/dragging. Resumes after releasing.
- **問題**：在拖拉移動或縮放邊框時，背景異步翻譯結果返回並強制更新 QPixmap 重繪，與 Qt 視窗佈局事件衝突，導致拖曳嚴重卡頓或崩潰。
- **修復**：在 `set_image` 中判斷正在互動時直接 `return` 忽略圖片重繪，等釋放滑鼠後再重啟翻譯。

### 3. Bubble Window Flag Update / 氣泡視窗屬性變更
- **Problem**: Bubble windows were previously `Qt.Tool` type, which could get pushed behind other windows and didn't appear in the Windows taskbar or Alt+Tab menu.
- **Fix**: Upgraded flags to `Qt.Window` standard window.
- **問題**：先前氣泡視窗屬性為 `Qt.Tool`，會被其他置頂視窗遮擋，且在工作列或 Alt+Tab 選單中找不到。
- **修復**：將視窗 flags 提升為標準視窗 `Qt.Window`，確保層級穩定。

---

## Verified Status / 驗證狀態

- Checked via `verify_anchor_deadlock.py` and `verify_anchor_interaction.py`. All tests passed.
- PyInstaller bundling completed successfully, standalone executable compiled and deployed.
- 通過死鎖驗證與拖拉狀態抑制驗證腳本，測試全數順利通過。
- 專案已重新打包並部署至根目錄下。
