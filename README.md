# AITranslator 螢幕即時翻譯工具 / Screen Real-Time Translation Tool

AITranslator is a powerful, GPU-accelerated screen translation tool designed for real-time translation of on-screen text, particularly optimized for manga, games, and applications.
AITranslator 是一款強大、支援 GPU 加速的螢幕即時翻譯工具，專為漫畫、遊戲與應用程式的畫面翻譯所設計。

---

## 🌟 Features / 核心功能

*   **Three UI Modes (三種顯示模式)**:
    *   **Overlay Mode (覆蓋模式)**: Capture a region and display the translated text in a draggable, resizable, borderless window over the original content. / 框選區域後，翻譯結果以無邊框視窗覆蓋於原圖之上。
    *   **List Mode (列表模式)**: Keep a history of all translated text in a scrollable list. / 於獨立視窗中以列表形式記錄所有翻譯歷史。
    *   **Anchor Mode (錨點模式)**: Select a region to monitor in real-time. The application will automatically detect changes, extract text, and translate it dynamically without manual capturing. / 框選持續監控區域，當畫面產生變化時，系統會自動辨識並即時更新翻譯，無需手動重新截圖。
*   **Smoother Resize & Drag in Anchor Mode (錨點模式拖拉與縮放流暢度優化)**:
    *   When you are resizing or dragging the anchor bubble window, any incoming async translation results are automatically suppressed. This ensures 100% fluid dragging and prevents crashes. Once you release the mouse, translation dynamically resumes within 1-2 seconds.
    *   當您正在拖曳移動或拉動邊框放大縮小錨點氣泡框時，系統會自動忽略/暫停非同步翻譯結果的重繪更新，確保拖拉操作 100% 絕對流暢且不卡頓崩潰。當手放開滑鼠（結束互動）後，系統會在 1-2 秒內自動恢復最新翻譯。
*   **Inpainting & Overlay (文字抹除與覆寫)**: Uses advanced AI models (e.g., LaMa) to remove the original text and seamlessly render the translated text back onto the background. / 利用先進 AI 模型抹除原文字，並將翻譯後的文字無縫貼回原圖。
*   **Smart Memory Management (智慧記憶體管理)**: Models are lazily loaded only when requested and automatically released from VRAM when all mode windows are closed, ensuring your system resources remain free when the tool is idle. / 模型採用懶載入機制，並在使用者關閉所有翻譯氣泡框後自動釋放顯示卡記憶體 (VRAM)，確保系統效能不被佔用。
*   **Customizable UI (自訂介面)**: Users can customize the border color and text color for each window, with preferences saved automatically across sessions. / 可自由更改每個視窗的邊框顏色與文字顏色，且系統會自動記憶您的喜好設定。
*   **Multilingual Support (多語系支援)**: Supports dynamic UI language switching. / 支援介面語言動態切換。

---

## 🔮 Translation Engines / 翻譯引擎比較

The application supports three types of translation engines. Below is a detailed comparison of their pros, cons, and free limits.
本工具支援三種翻譯引擎，以下為其優缺點及免費額度的詳細分析：

| Engine / 翻譯引擎 | Free Limits / 免費額度 | Pros / 優點 | Cons / 缺點 |
| :--- | :--- | :--- | :--- |
| **Google Translate** <br> (Google 傳統翻譯) | **Unlimited & Free** <br> (完全免費，無限制) | - No API Key required.<br>- Fast and stable. <br> - 免金鑰，開箱即用。<br>- 速度快且極為穩定。 | - Basic machine translation.<br>- Lacks context awareness and linguistic polish. <br> - 傳統機器翻譯，缺乏上下文理解與專有名詞語意潤飾。 |
| **Gemini API** <br> (Gemini 1.5 Flash) | **Very Generous Free Tier** <br> (高額免費層) <br> - **15 RPM** (Requests per minute)<br>- **1,500 RPD** (Requests per day) | - Advanced LLM translation.<br>- Excellent context understanding and multi-turn refinement. <br> - 智慧大模型翻譯，上下文語意潤飾極佳。<br>- 免費額度非常充足。 | - Free tier may experience rate limit during peak hours.<br>- Requires network proxy in certain regions (e.g., China). <br> - 高峰期可能遇到頻率限制。<br>- 某些地區（如中國大陸）需要代理網路才能連線。 |
| **OpenRouter / Qwen** <br> (Qwen 2.5 72B / Qwen3) | **100% Free** <br> (完全免費) <br> - All Qwen options in UI map to the **Qwen 2.5 72B / Qwen3 Free** models. <br> - UI 上所有 Qwen 選項底層皆連線至免費模型。 | - Excellent for gaming, anime, and lore terms (especially Warframe).<br>- Free model under OpenRouter. <br> - 對於遊戲、動漫專有名詞翻譯（如星際戰甲術語）極為精準。<br>- 完全免費。 | - Requires creating an OpenRouter account to get a free API Key.<br>- Slightly higher network latency than Google. <br> - 需要申請 OpenRouter 帳號並取得免費 API Key。<br>- 網路延遲比 Google 稍微高一些。 |

> [!NOTE]
> **Regarding OpenRouter / Qwen Free Models:**
> In the settings UI, you will see options like *Qwen2.5-VL-72B-Instruct:free* and *OpenRouter Qwen3-Next-80B:free*. In the backend code, **all of these options are mapped to OpenRouter's official free model (`qwen/qwen3-next-80b-a3b-instruct:free`)**. Therefore, they are 100% free to use and do not consume account balances.
>
> **關於 OpenRouter / Qwen 免費模型：**
> 在設定 UI 中，您會看到 *Qwen2.5-VL-72B-Instruct:free* 與 *OpenRouter Qwen3-Next-80B:free* 等選項。在後端代碼中，**所有這些 Qwen 選項都已統一路由至 OpenRouter 的官方免費模型 (`qwen/qwen3-next-80b-a3b-instruct:free`)**。因此，它們完全免費，不會扣除您的帳戶餘額。

---

## 🚀 Usage / 使用方式

If you are using the pre-compiled version, simply run `AITranslator.exe` from the root directory.
如果您使用的是編譯好的版本，請直接執行根目錄下的 `AITranslator.exe`（程式將在背景靜默運行，無終端 CMD 黑框彈出）。

*   **Ctrl+Alt+S**: Trigger Screen Capture (觸發截圖)
*   **Ctrl+Alt+O**: Toggle Main Window (呼叫/隱藏主視窗)

### ⚡ Portable GPU Acceleration (Zero-Setup) / 便攜式 GPU 加速 (開箱即用，免安裝環境)

> [!IMPORTANT]
> **How to enable GPU mode (Release v1.1+) / 如何啟用 GPU 模式 (v1.1+)：**
> - **Split Files Setup:** To bypass GitHub's 2GB file limit and prevent file corruption, the release is split into:
>   1. **Main App:** `AITranslator-v1.1.zip` (~508MB)
>   2. **GPU Dependencies:** `AITranslator-v1.1-GPU-Dependencies.zip` (~1.52GB)
> - **Installation:** Download and extract both files. Copy all extracted DLL files from the GPU Dependencies package directly into the **`_internal/`** folder of the extracted Main App directory.
> - **NVIDIA Driver Requirement (CUDA 13.1):** The target computer must have an NVIDIA GPU, and the NVIDIA graphics driver must be updated to version **`580.xx` or higher** (e.g. 591.xx+) to support CUDA 13.1. Otherwise, you will encounter a `CUDA failure 801 (cudaErrorNotSupported)` error.
> - **Automatic CPU Fallback:** If the computer lacks an NVIDIA GPU or the drivers are outdated, the app will automatically and silently fall back to CPU mode.
>
> **如何在另一台電腦上啟用 GPU 模式：**
> - **雙檔案組合安裝**：為了繞過 GitHub 單個檔案 2GB 的大小限制並防止損壞，版本已拆分為：
>   1. **CPU 主程式**：`AITranslator-v1.1.zip` (~508MB)
>   2. **GPU 依賴套件**：`AITranslator-v1.1-GPU-Dependencies.zip` (~1.52GB)
> - **安裝方式**：下載並解壓兩個壓縮檔，將 GPU 依賴套件內的所有 DLL 檔案直接複製貼上到主程式的 **`_internal`** 資料夾中即可。
> - **顯卡與驅動要求 (CUDA 13.1)**：目標電腦必須配有 NVIDIA 顯示卡，且 NVIDIA 顯示卡驅動程式必須更新至 **`580.xx` 或更高版本**（例如 591.xx 以上）以支援 CUDA 13.1。若驅動版本低於此限制，將會出現 `CUDA failure 801` 載入失敗錯誤。
> - **自動降級 CPU**：若目標電腦偵測不到 NVIDIA 顯示卡或相容驅動程式，程式會自動無聲地降級至 **CPU 模式** 執行，確保隨時可用。

### ⚠️ Troubleshooting / 常見問題與排查

> [!NOTE]
> **Hotkey Unresponsiveness when System Windows are Focused / 當前台焦點為系統視窗時快捷鍵失效：**
> - **The Issue:** Windows disables low-level keyboard hooks (user-mode hotkeys) when focusing on high-privilege system windows (e.g., **Task Manager**, Administrator command prompts, or UAC prompts) to prevent keylogging. Under these circumstances, hotkeys like capture or mode switching will have no response.
> - **Solutions:**
>   1. **Temporary Fix:** Simply click on your desktop or a normal application window to lose focus from Task Manager. The hotkeys will automatically work again.
>   2. **Permanent Fix:** Right-click `AITranslator.exe` and select **"Run as administrator"**. This elevates the process integrity level to match Task Manager, allowing hotkeys to work even when Task Manager is focused.
>
> **當前台焦點為高權限視窗時快捷鍵與切換失效：**
> - **問題原因**：當您點擊 **工作管理員**、以管理員身分執行的 CMD/PowerShell 視窗、或 UAC 系統提示框時，Windows 基於安全保護機制（UIPI），會強制封鎖所有一般權限程式的全域鍵盤監聽（防止密碼被竊取）。此時按下截圖或模式切換快捷鍵將沒有任何反應。
> - **解決方法**：
>   1. **臨時解決**：只需點擊一下桌面、瀏覽器或其他一般程式，讓工作管理員失去焦點，快捷鍵即會立刻恢復作用。
>   2. **永久解決**：對 `AITranslator.exe` 按右鍵，選擇 **「以系統管理員身分執行」**。程式提升至高權限後，即可在工作管理員前台焦點下正常觸發快捷鍵與模式切換。

---


## 🛠️ Developer Guide / 開發者指南

### GPU Installation for Developers / 開發者 GPU 相依性安裝
If you are building or running from source, you MUST install dependencies correctly to avoid ONNX CPU/GPU conflicts. `rapidocr-onnxruntime` inherently pulls `onnxruntime` (CPU), which will shadow `onnxruntime-gpu` and break GPU support.
如果您是從源碼運行或編譯，必須正確安裝相依套件以避免 ONNX CPU/GPU 衝突。`rapidocr-onnxruntime` 會自動拉取 `onnxruntime` (CPU) 版本，這會覆蓋 `onnxruntime-gpu` 並導致 GPU 加速失效。

**Do NOT just run `pip install -r requirements.txt` directly. / 請勿直接執行 `pip install -r requirements.txt`**

Instead, run the provided installation script (Windows):
請改為執行以下批次檔 (Windows)：
```cmd
install_gpu.bat
```

### Building / 打包編譯
To build the standalone executable with PyInstaller, run:
若要使用 PyInstaller 打包獨立執行檔，請執行：
```cmd
python -m PyInstaller --clean -y main.spec
```
After compilation, sync the outputs to the root directory using the synchronization helper script:
編譯完成後，使用同步腳本將產出同步回根目錄：
```cmd
python C:/Users/user/.gemini/antigravity/brain/ae71f81b-4f83-437b-b333-b191c8e2c53a/scratch/deploy.py
```
And clean up temporary directories (`build`, `dist`). / 並清理暫存目錄。
