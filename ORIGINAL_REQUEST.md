# Original Requirements & Key Constraints / 原始需求與關鍵開發約束

This document records the original key requirements and historical follow-ups of the AITranslator project, cleaned of previous encoding errors.
本文件記錄了 AITranslator 專案的原始關鍵需求與歷史開發沿革，已清除原先因解碼錯誤導致的亂碼。

---

## 📌 Phase 1: Core Clean Build & Execution / 第一階段：核心編譯與獨立執行

### R1. Clean Workspace & Build Check / 清理工作區與編譯檢查
- Remove all temporary testing files (e.g., `test_*.py`, `*.log`, `build/`, `dist/`).
- Clean source directory, preserving only core source code files (`*.py`, `main.spec`, `requirements.txt`, QML directories, and model assets).
- 清理所有測試暫存檔與日誌，保持原始工作目錄乾淨，僅保留必要原始碼與打包檔。

### R2. Pack standalone Release Directory / 封裝獨立執行目錄
- Use PyInstaller to pack `AITranslator.exe` into a standalone folder.
- Ensure that the application runs standalone on other machines without needing python or dependencies installed.
- 建立一個包含 `AITranslator.exe` 與 `_internal` 的獨立 Release 資料夾，不需安裝 Python 亦能一鍵啟動。

---

## 📌 Phase 2: Rapid OCR Engine Update / 第二階段：快速 OCR 引擎更換

- Replace PaddleOCR/PaddlePaddle with **ONNXRuntime OCR (RapidOCR)**.
- Resolve conflicts between CPU and GPU ONNX libraries (make sure `onnxruntime` does not shadow `onnxruntime-gpu`).
- Bundle NVIDIA CUDA and cuDNN runtime DLLs in `_internal/` so that GPU acceleration works out-of-the-box on computers with compatible GPUs and drivers, without manual CUDA installations.
- 將 PaddleOCR 更換為基於 **ONNXRuntime 的 RapidOCR**。
- 解決 CPU 與 GPU 套件衝突，並將 CUDA/cuDNN 的執行期 DLL 打包進 `_internal/`，使符合條件的電腦能開箱即用 GPU 加速，無須手動設定環境。

---

## 📌 Phase 3: Translation Engines & Inpainting / 第三階段：翻譯引擎與文字塗抹

- **R3.1 UI API Key Settings**: Users can input OpenRouter and Gemini API Keys in the React Settings UI.
- **R3.2 Inpainting**: Implement advanced text removal using models like LaMa, removing original texts and rendering translations back onto the background.
- **R3.3 Translation Fallback**: If Gemini or OpenRouter translation fails or rates are limited, fallback automatically to Google Translate.
- **三種翻譯引擎**：支援 Google 翻譯、Gemini API (免費層) 以及 OpenRouter，並實作失敗自動降級 Google 的 Fallback 機制。
- **文字塗抹與覆寫**：藉由 LaMa AI 模型將原圖文字抹除，並把翻譯後的文字完美貼回背景。
