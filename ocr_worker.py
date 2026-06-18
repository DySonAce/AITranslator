"""
ocr_worker.py ─ RapidOCR 辨識引擎 (ONNXRuntime 加速)
=================================
使用 rapidocr-onnxruntime 進行端到端文字檢測與辨識。
"""
import time
import numpy as np
from typing import List
import os
import sys

# 確保多進程下 OpenMP 不會崩潰
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Ensure CUDA DLLs can be found
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    os.environ["PATH"] = sys._MEIPASS + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, 'add_dll_directory'):
        try: os.add_dll_directory(sys._MEIPASS)
        except Exception: pass
    
    # Fallback to global Python nvidia DLLs to keep EXE size small but still use GPU
    fallback_sp = r"C:\Users\user\AppData\Local\Programs\Python\Python312\Lib\site-packages"
    nvidia_path = os.path.join(fallback_sp, "nvidia")
    if os.path.exists(nvidia_path):
        for p in os.listdir(nvidia_path):
            bin_path = os.path.join(nvidia_path, p, "bin")
            if os.path.exists(bin_path):
                os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
                if hasattr(os, 'add_dll_directory'):
                    try: os.add_dll_directory(bin_path)
                    except Exception: pass
else:
    # Source mode: add conda nvidia paths
    site_packages = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Try to find conda env site-packages
    for sp in [os.path.join(sys.prefix, "Lib", "site-packages"), os.path.join(sys.prefix, "lib", "site-packages")]:
        nvidia_path = os.path.join(sp, "nvidia")
        if os.path.exists(nvidia_path):
            for p in os.listdir(nvidia_path):
                bin_path = os.path.join(nvidia_path, p, "bin")
                if os.path.exists(bin_path):
                    os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
                    if hasattr(os, 'add_dll_directory'):
                        try: os.add_dll_directory(bin_path)
                        except Exception: pass

from common.protocol import TextBlock, OCRResult, get_ocr_lang


class OCRWorker:
    """RapidOCR 辨識 Worker"""

    def __init__(self, use_gpu: bool = True):
        self._use_gpu = use_gpu
        self._engine = None
        self._ready = False
        self._lang = None   # 記錄目前載入的語言

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def use_gpu(self) -> bool:
        return self._use_gpu

    def load(self, lang: str = "en") -> None:
        """載入 RapidOCR 模型"""
        if self._ready and self._lang == lang:
            return

        # 語言切換時需要重新載入
        if self._lang and self._lang != lang:
            print(f"[OCR] 語言切換 {self._lang} → {lang}，重新載入…", flush=True)
            self._engine = None
            self._ready = False

        print(f"[OCR] 載入 RapidOCR gpu={self._use_gpu} lang={lang}…", flush=True)
        t0 = time.time()

        try:
            import onnxruntime as ort
            ort.set_default_logger_severity(4) # Suppress warnings/errors to prevent C++ stderr crash in console=False mode
            from rapidocr_onnxruntime import RapidOCR

            try:
                if self._use_gpu:
                    print("[OCR] 嘗試以 GPU 模式載入 RapidOCR...", flush=True)
                    self._engine = RapidOCR(
                        det_use_cuda=True,
                        cls_use_cuda=True,
                        rec_use_cuda=True,
                    )
                    # Warmup
                    dummy = np.zeros((32, 32, 3), dtype=np.uint8)
                    self._engine(dummy)

                    providers = self._engine.text_det.infer.session.get_providers()
                    if 'CUDAExecutionProvider' not in providers:
                        print("[OCR] Warning: CUDAExecutionProvider is not available, falling back to CPU", flush=True)
                        raise RuntimeError("CUDA provider not available in ONNX session")
                    print("[OCR] GPU 模式載入成功！", flush=True)
                else:
                    raise RuntimeError("CPU mode requested")
            except Exception as gpu_err:
                if self._use_gpu:
                    print(f"[OCR] GPU 載入失敗 ({gpu_err})，正在自動降級至 CPU 模式...", flush=True)
                self._engine = RapidOCR(
                    det_use_cuda=False,
                    cls_use_cuda=False,
                    rec_use_cuda=False,
                )
                dummy = np.zeros((32, 32, 3), dtype=np.uint8)
                self._engine(dummy)
                print("[OCR] CPU 模式備用載入成功！", flush=True)

            self._ready = True
            self._lang = lang
            print(f"[OCR] RapidOCR 就緒 ({time.time()-t0:.1f}s)", flush=True)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[OCR] 載入失敗 (CPU 備用載入也失敗): {e}\n{tb}", flush=True)
            self._ready = False
            raise RuntimeError(f"OCR 載入失敗: {e}")

    def unload(self):
        """釋放 RapidOCR 模型與記憶體"""
        if self._engine:
            print("[OCR] 釋放 RapidOCR 模型...", flush=True)
            self._engine = None
            self._lang = None
            self._ready = False
            import gc
            gc.collect()

    def recognize(self, img_np: np.ndarray, lang_display: str = "英文") -> OCRResult:
        """辨識圖片中的文字。"""
        t0 = time.time()

        if not isinstance(img_np, np.ndarray) or img_np.size == 0:
            return OCRResult(blocks=[], lang="en", elapsed=time.time()-t0)

        if img_np.ndim < 2 or img_np.shape[0] < 5 or img_np.shape[1] < 5:
            return OCRResult(blocks=[], lang="auto", elapsed=0.0)

        if not self._ready:
            return OCRResult(blocks=[], lang="en", elapsed=time.time()-t0)

        # 直接送入 numpy array，省去 PIL 轉換開銷
        try:
            result, elapse_list = self._engine(img_np, use_cls=False)
        except Exception as e:
            print(f"[OCR] 辨識失敗: {e}", flush=True)
            return OCRResult(blocks=[], lang="auto", elapsed=time.time()-t0)

        blocks: List[TextBlock] = []
        if not result:
            elapsed = time.time() - t0
            print(f"[OCR] 未偵測到文字 ({elapsed:.2f}s)", flush=True)
            return OCRResult(blocks=[], lang="auto", elapsed=elapsed)

        for res in result:
            box, text, score = res
            if text.strip() and float(score) > 0.5:   # 過濾低信心結果
                blocks.append(TextBlock(box=box, text=text, confidence=float(score)))

        elapsed = time.time() - t0
        print(f"[OCR] {len(blocks)} 區塊 ({elapsed:.2f}s)", flush=True)
        return OCRResult(blocks=blocks, lang="auto", elapsed=elapsed)

    def set_gpu(self, use_gpu: bool):
        """切換 CPU/GPU 模式"""
        if use_gpu != self._use_gpu:
            self._use_gpu = use_gpu
            self._engine = None
            self._ready = False
