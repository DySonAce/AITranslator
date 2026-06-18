"""
inpaint_worker.py ─ LaMa 圖像修復引擎
=======================================
根據 OCR box 位置生成 mask，使用 LaMa 修復原文區域。
修復後的圖像作為翻譯文字的乾淨背景。
"""
import time
import numpy as np
import cv2
from PIL import Image, ImageDraw
from typing import List, Optional, Tuple
from common.protocol import TextBlock


class InpaintWorker:
    """OpenCV 圖像修復 Worker"""

    def __init__(self):
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def load(self, progress_callback=None) -> None:
        """載入 OpenCV 修復模組 (極輕量，瞬間完成)"""
        if progress_callback:
            progress_callback("載入 OpenCV 修復模組…")
        print("[修復] OpenCV Inpaint 就緒", flush=True)
        self._ready = True

    def unload(self):
        """釋放資源"""
        self._ready = False
        import gc
        gc.collect()

    def create_mask(self, img_size: Tuple[int, int],
                    blocks: List[TextBlock],
                    padding: int = 5) -> Image.Image:
        W, H = img_size
        mask = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(mask)

        for blk in blocks:
            xs = [float(p[0]) for p in blk.box]
            ys = [float(p[1]) for p in blk.box]
            x1 = max(0, int(min(xs)) - padding)
            y1 = max(0, int(min(ys)) - padding)
            x2 = min(W, int(max(xs)) + padding)
            y2 = min(H, int(max(ys)) + padding)
            draw.rectangle([x1, y1, x2, y2], fill=255)

        return mask

    def inpaint(self, image_np: np.ndarray,
                blocks: List[TextBlock],
                padding: int = 5) -> Optional[np.ndarray]:
        if not self._ready:
            return None

        if not blocks:
            return image_np

        t0 = time.time()
        try:
            H, W = image_np.shape[:2]
            mask = self.create_mask((W, H), blocks, padding)
            mask_np = np.array(mask)
            
            if mask_np.max() == 0:
                return image_np

            # Ensure image is BGR or RGB (cv2 uses BGR but if it's passed as RGB it's fine)
            if len(image_np.shape) == 2:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2RGB)
            elif image_np.shape[2] == 4:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
            
            result_np = cv2.inpaint(image_np, mask_np, 5, cv2.INPAINT_TELEA)

            elapsed = time.time() - t0
            print(f"[修復] OpenCV 完成 ({elapsed:.3f}s)", flush=True)
            return result_np

        except Exception as e:
            print(f"[修復] OpenCV 錯誤: {e}", flush=True)
            return None
