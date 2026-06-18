# Project: AITranslator React Integration and Consolidation / React 整合與整合專案

## Architecture / 架構說明

*   `main_window.py`: Entry point and PySide6 application window. Integrates PyQt WebEngine to render the frontend UI. / 程式進入點與 PySide6 視窗應用程式。內建 PyQt WebEngine 用於渲染前端 React UI。
*   `ui_dist`: Built files of the React UI. Served locally and communicates with Python backend. / React 前端的編譯產出。本機託管並與 Python 後端通訊。
*   IPC (Inter-Process Communication) / WebChannel: Connects React frontend with Python backend for hotkeys, settings, OCR, and translations. / 連接 React 前端與 Python 後端的 WebChannel 機制，用以傳遞熱鍵設定、OCR 辨識與翻譯請求。
*   Workers (`ocr_worker.py`, `translator_worker.py`, `inpaint_worker.py`): Asynchronous processing units for ONNX OCR, LLM/API translations, and image text removal. / 負責 ONNX OCR、大模型/API 翻譯與影像文字塗抹的非同步工作執行緒。

---

## Milestones & History / 里程碑與開發歷史

| # | Milestone Name / 里程碑名稱 | Description & Status / 說明與狀態 |
|---|-----------------------------|------------------------------------|
| 1 | Directory Consolidation / 目錄整合 | Merge source files from `AITranslator_App` into root directory `AITranslator`. / 將 `AITranslator_App` 原始碼完美合併至根目錄 `AITranslator`。 **[DONE]** |
| 2 | React UI & Shortcuts / React 整合與快捷鍵 | Render React UI in WebEngine. Implement WebChannel and fix shortcut capturing bugs. / 於 WebEngine 渲染 React UI，建立 WebChannel 通訊，並修復快捷鍵截圖與錄製失效問題。 **[DONE]** |
| 3 | Translation Flow Restoration / 恢復翻譯功能 | Restore OCR, translate modes (Overlay, List, Anchor), and inpainting logic. / 恢復完整的 OCR、三種翻譯模式以及 LaMa 背景抹除邏輯。 **[DONE]** |
| 4 | Deadlock & Stability Fixes / 死鎖與穩定性修復 | Fix double lock deadlock via `RLock`. Change bubble windows to `Qt.Window` to fix layering and focus issues. / 將 `anchor_lock` 改為 `RLock` 可重入鎖解決死鎖；將氣泡框 flag 改為 `Qt.Window` 解決遮擋與焦點問題。 **[DONE]** |
| 5 | Drag & Resize Smoothness / 拖拉縮放流暢度優化 | Suppress async paint updates during bubble drags or resizing to ensure 100% fluent UI responsiveness. / 當拖拉或縮放氣泡框時，暫停非同步翻譯結果的重繪重新渲染，以達成 100% 極流暢拖拉體驗。 **[DONE]** |
| 6 | Bilingual Documentation / 說明文件雙語化 | Update all `.md` files to align with the current version features, supporting Traditional Chinese and English. / 將專案內所有 `.md` 檔案更新為以最新版本功能為主的繁體中文與英文對照。 **[DONE]** |

---

## Code Layout / 原始碼檔案布局

*   Root directory: `D:\chrom\screenshot\AITranslator`
*   Entry scripts: `launcher.py`, `main_window.py`
*   Workers: `ocr_worker.py`, `translator_worker.py`, `inpaint_worker.py`
*   React build folder: `ui_dist/`
