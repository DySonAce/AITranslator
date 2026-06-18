import numpy as np
from PIL import Image
from typing import List, Tuple, Optional
from PySide6.QtGui import QImage, QPainter, QFont, QColor, QFontMetrics, QPen, QBrush
from PySide6.QtCore import Qt, QRect
from common.protocol import TextBlock

_current_font_lang = "tc"

def set_render_lang(lang: str):
    global _current_font_lang
    _current_font_lang = lang

def pil_to_qimage(pil_img: Image.Image) -> QImage:
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    qim = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format_RGBA8888)
    return qim.copy()

def qimage_to_pil(qimg: QImage) -> Image.Image:
    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
    w, h = qimg.width(), qimg.height()
    ptr = qimg.constBits()
    arr = np.array(ptr).reshape((h, w, 4))
    return Image.fromarray(arr, "RGBA").copy()

def extract_colors(img_np: np.ndarray, box: List[Tuple[int, int]]) -> Tuple[Tuple[int,int,int], Tuple[int,int,int]]:
    xs = [int(p[0]) for p in box]
    ys = [int(p[1]) for p in box]
    x1, x2 = max(0, min(xs)), min(img_np.shape[1], max(xs))
    y1, y2 = max(0, min(ys)), min(img_np.shape[0], max(ys))
    
    if x2 <= x1 or y2 <= y1:
        return (255, 255, 255), (0, 0, 0)
        
    roi = img_np[y1:y2, x1:x2]
    if roi.size == 0:
        return (255, 255, 255), (0, 0, 0)
        
    if roi.shape[0] > 30 or roi.shape[1] > 100:
        roi = roi[::2, ::2]
        
    bg_color = np.median(roi, axis=(0, 1)).astype(int)
    diff = np.abs(roi.astype(int) - bg_color)
    dist = np.sum(diff, axis=2)
    
    flat_roi = roi.reshape(-1, 3)
    flat_dist = dist.flatten()
    
    if len(flat_dist) > 0:
        idx = np.argsort(flat_dist)
        # Take the top 20% most distant pixels from the background
        top_20_percent = int(len(idx) * 0.80)
        top_20_idx = idx[top_20_percent:]
        top_pixels = flat_roi[top_20_idx]
        
        # Quantize to 16-level buckets to group similar colors
        quantized = (top_pixels // 16) * 16
        
        # Find the most frequent color among the high-contrast pixels (usually the text)
        colors, counts = np.unique(quantized, axis=0, return_counts=True)
        most_frequent_idx = np.argmax(counts)
        fg_color = colors[most_frequent_idx]
        
        # Add 8 to recenter the quantized bucket
        fg_color = np.clip(fg_color + 8, 0, 255).tolist()
    else:
        fg_color = [255, 255, 255]
        
    return tuple(bg_color.tolist()), tuple(fg_color)

def merge_rows(blocks: List[TextBlock]) -> List[TextBlock]:
    if not blocks: return []
    
    # 1. Group blocks into rows/lines based on vertical overlap
    # Sort initially by vertical center to process top-to-bottom
    sorted_blocks = sorted(blocks, key=lambda b: (min(p[1] for p in b.box) + max(p[1] for p in b.box)) / 2)
    
    lines = []
    for b in sorted_blocks:
        b_ymin = min(p[1] for p in b.box)
        b_ymax = max(p[1] for p in b.box)
        b_h = b_ymax - b_ymin
        if b_h <= 0:
            continue
            
        # Check if this block fits into any existing row/line
        placed = False
        for line in lines:
            # Check overlap against the overall line vertical bounds
            l_ymin = min(min(p[1] for p in member.box) for member in line)
            l_ymax = max(max(p[1] for p in member.box) for member in line)
            l_h = l_ymax - l_ymin
            
            overlap = min(b_ymax, l_ymax) - max(b_ymin, l_ymin)
            min_overlap_h = min(b_h, l_h)
            if min_overlap_h > 0 and (overlap / min_overlap_h) > 0.4:
                line.append(b)
                placed = True
                break
        if not placed:
            lines.append([b])
            
    # 2. For each row/line, sort from left to right and merge horizontally adjacent words/segments
    merged_blocks = []
    for line in lines:
        # Sort left-to-right (reading order)
        line_sorted = sorted(line, key=lambda b: min(p[0] for p in b.box))
        
        current = line_sorted[0]
        for next_b in line_sorted[1:]:
            c_xmin = min(p[0] for p in current.box)
            c_xmax = max(p[0] for p in current.box)
            c_ymin = min(p[1] for p in current.box)
            c_ymax = max(p[1] for p in current.box)
            c_h = c_ymax - c_ymin
            
            n_xmin = min(p[0] for p in next_b.box)
            n_xmax = max(p[0] for p in next_b.box)
            
            # Horizontal gap between current block and next block
            gap = n_xmin - c_xmax
            
            # If they are close horizontally (within 3 times the character height), merge them
            if gap < c_h * 3.0:
                xs = [p[0] for p in current.box] + [p[0] for p in next_b.box]
                ys = [p[1] for p in current.box] + [p[1] for p in next_b.box]
                new_box = [[min(xs), min(ys)], [max(xs), min(ys)], [max(xs), max(ys)], [min(xs), max(ys)]]
                
                c_text = current.text.strip()
                n_text = next_b.text.strip()
                
                # Check for CJK character presence (Chinese or Japanese which don't use spaces)
                def is_cjk_no_space(text: str) -> bool:
                    for char in text:
                        val = ord(char)
                        # Chinese
                        if 0x4E00 <= val <= 0x9FFF or 0x3400 <= val <= 0x4DBF or 0xF900 <= val <= 0xFAFF:
                            return True
                        # Japanese Hiragana/Katakana
                        if 0x3040 <= val <= 0x309F or 0x30A0 <= val <= 0x30FF:
                            return True
                    return False
                
                separator = "" if is_cjk_no_space(c_text + n_text) else " "
                
                current = TextBlock(
                    box=new_box,
                    text=c_text + separator + n_text,
                    confidence=(current.confidence + next_b.confidence) / 2
                )
            else:
                merged_blocks.append(current)
                current = next_b
        merged_blocks.append(current)
        
    # 3. Sort all merged rows from top to bottom so they read in correct sequence in list mode
    merged_blocks = sorted(merged_blocks, key=lambda b: min(p[1] for p in b.box))
    return merged_blocks


def smart_render(original_pil: Image.Image,
                 img_np: np.ndarray,
                 blocks: List[TextBlock],
                 translated: List[str],
                 inpainted_pil: Optional[Image.Image] = None,
                 custom_font_color: Optional[Tuple[int,int,int]] = None) -> QImage:
    """
    原生 QPainter 渲染引擎：
      - 1x 解析度（放棄 2x 放大，避免模糊）
      - 使用作業系統級別的 ClearType 次像素抗鋸齒
    """
    W, H = original_pil.size
    
    # 決定基底
    base_pil = inpainted_pil if inpainted_pil else original_pil
    base_qim = pil_to_qimage(base_pil)
    
    painter = QPainter(base_qim)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setRenderHint(QPainter.Antialiasing, False)

    # 預先載入對應字型 (使用 _current_font_lang)
    # PySide6 的 QFont 可以直接透過字型名稱呼叫
    # 如果要 100% 準確對應 FONT_PATH，我們可以使用 QFontDatabase
    # 但簡單起見，我們指定 "Microsoft JhengHei" (微軟正黑體) 等系統字型族
    font_family = "Microsoft JhengHei"
    if "ja" in _current_font_lang:
        font_family = "Meiryo"
    elif "ko" in _current_font_lang:
        font_family = "Malgun Gothic"

    items = []
    from PySide6.QtGui import QFontMetrics
    
    # ── ① 計算佈局 ──
    for blk, trans in zip(blocks, translated):
        if not trans:
            continue
        xs = [int(p[0]) for p in blk.box]
        ys = [int(p[1]) for p in blk.box]
        x1 = max(0, min(xs)); x2 = min(W, max(xs))
        y1 = max(0, min(ys)); y2 = min(H, max(ys))
        if x2 <= x1 or y2 <= y1:
            continue
        bw, bh = x2 - x1, y2 - y1

        bg_c, fg_c = extract_colors(img_np, blk.box)
        if custom_font_color:
            fg_c = custom_font_color

        # 找最大適配字體 (允許字體比原框高 25%，增加易讀性)
        max_sz = max(13, int(bh * 1.25))
        best_sz = 8
        low = 8
        high = max(8, max_sz)
        while low <= high:
            mid = (low + high) // 2
            qfont = QFont(font_family, mid)
            qfont.setBold(True)
            fm = QFontMetrics(qfont)
            rect = fm.boundingRect(trans)
            if rect.width() <= bw and rect.height() <= int(bh * 1.3):
                best_sz = mid
                low = mid + 1
            else:
                high = mid - 1
                
        qfont = QFont(font_family, best_sz)
        qfont.setBold(True)
        fm = QFontMetrics(qfont)
        rect = fm.boundingRect(trans)
        tw, th = rect.width(), rect.height()
        ty = y1 + max(0, (bh - th) // 2)

        items.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "tx": x1, "ty": ty, "tw": tw, "th": th,
            "qfont": qfont, "text": trans,
            "bg_c": bg_c, "fg_c": fg_c,
        })

    # ── ② 衝突偵測 ──
    placed: list[tuple] = []
    for item in items:
        tx, ty, tw, th = item["tx"], item["ty"], item["tw"], item["th"]
        rect = [tx, ty, tx + tw, ty + th]
        for _ in range(40):
            hit = next((p for p in placed
                        if not (rect[2] <= p[0] or rect[0] >= p[2]
                                or rect[3] <= p[1] or rect[1] >= p[3])), None)
            if not hit:
                break
            rect[1] = hit[3] + 2
            rect[3] = rect[1] + th
        if rect[3] > H:
            rect[1] = max(0, H - th - 2)
            rect[3] = rect[1] + th
        item["ty"] = rect[1]
        placed.append((rect[0], rect[1], rect[2], rect[3]))

    # ── ③ 繪製背景與文字 ──
    for item in items:
        # 如果沒有 LaMa 背景，畫出色塊覆蓋
        if inpainted_pil is None:
            painter.fillRect(item["x1"], item["y1"], item["x2"]-item["x1"], item["y2"]-item["y1"], 
                             QColor(item["bg_c"][0], item["bg_c"][1], item["bg_c"][2]))
        
        painter.setFont(item["qfont"])
        painter.setPen(QColor(item["fg_c"][0], item["fg_c"][1], item["fg_c"][2]))
        
        # 繪製文字 (QPainter 的 drawText y座標是基準線(baseline)，但如果給定 QRect 就能自動對齊)
        from PySide6.QtCore import QRect, Qt
        # 使用 QRect 讓文字在給定的方框內置中繪製
        text_rect = QRect(item["tx"], item["ty"], item["tw"], item["th"])
        painter.drawText(text_rect, Qt.AlignCenter, item["text"])

    painter.end()
    return base_qim


def render_transparent_overlay(W: int, H: int,
                 img_np: np.ndarray,
                 blocks: List[TextBlock],
                 translated: List[str],
                 custom_font_color: Optional[Tuple[int,int,int]] = None) -> QImage:
    """
    渲染透明覆蓋層（用於錨點模式），將翻譯文字畫在對應對話框座標上。
    背景為全透明，只有文字部分有底色與文字。
    """
    from PySide6.QtGui import QFontMetrics, QFont, QColor, QPainterPath, QPen
    from PySide6.QtCore import Qt, QRect
    from PySide6.QtGui import QImage, QPainter
    base_qim = QImage(W, H, QImage.Format_RGBA8888)
    base_qim.fill(QColor(0, 0, 0, 0)) # Fully transparent

    painter = QPainter(base_qim)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setRenderHint(QPainter.Antialiasing, False)

    font_family = "Microsoft JhengHei"
    if "ja" in _current_font_lang:
        font_family = "Meiryo"
    elif "ko" in _current_font_lang:
        font_family = "Malgun Gothic"

    items = []
    from PySide6.QtGui import QFontMetrics, QFont, QColor, QPainterPath, QPen
    from PySide6.QtCore import Qt, QRect

    for blk, trans in zip(blocks, translated):
        if not trans:
            continue
        xs = [int(p[0]) for p in blk.box]
        ys = [int(p[1]) for p in blk.box]
        x1 = max(0, min(xs)); x2 = min(W, max(xs))
        y1 = max(0, min(ys)); y2 = min(H, max(ys))
        if x2 <= x1 or y2 <= y1:
            continue
        bw, bh = x2 - x1, y2 - y1

        bg_c, fg_c = extract_colors(img_np, blk.box)
        if custom_font_color:
            fg_c = custom_font_color

        max_sz = max(18, int(bh * 1.6))
        best_sz = 9
        low = 8
        high = max(8, max_sz)
        while low <= high:
            mid = (low + high) // 2
            qfont = QFont(font_family, mid)
            qfont.setBold(True)
            fm = QFontMetrics(qfont)
            rect = fm.boundingRect(trans)
            if rect.width() <= int(bw * 1.1) and rect.height() <= int(bh * 1.6):
                best_sz = mid
                low = mid + 1
            else:
                high = mid - 1
                
        qfont = QFont(font_family, best_sz)
        qfont.setBold(True)
        fm = QFontMetrics(qfont)
        rect = fm.boundingRect(trans)
        tw, th = rect.width(), rect.height()
        ty = y1 + max(0, (bh - th) // 2)

        items.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "tx": x1, "ty": ty, "tw": tw, "th": th,
            "qfont": qfont, "text": trans,
            "bg_c": bg_c, "fg_c": fg_c,
            "fm": fm
        })

    for it in items:
        bg = QColor(*it["bg_c"])
        bg.setAlpha(220) # Slightly transparent background
        painter.fillRect(it["tx"], it["ty"], it["tw"], it["th"], bg)
        
        painter.setFont(it["qfont"])
        painter.setPen(QColor(*it["fg_c"]))
        text_rect = QRect(it["tx"], it["ty"], it["tw"], it["th"])
        painter.drawText(text_rect, Qt.AlignCenter, it["text"])

    painter.end()
    return base_qim
