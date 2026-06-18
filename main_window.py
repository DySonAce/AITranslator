"""
main_window.py - AI Translation v1.0 (PySide6 + React UI) / AI 翻譯 v1.0
================================================
Python backend entry point / Python 後端主入口
"""

# System imports / 系統匯入
import os, sys, ctypes, threading, re, time
if sys.stdout is None: sys.stdout = open(os.devnull, 'w')
try:
    sys.stderr = open("D:/chrom/screenshot/AITranslator/stderr_log.txt", "w", encoding="utf-8")
except Exception:
    if sys.stderr is None: sys.stderr = open(os.devnull, 'w')

def global_excepthook(exctype, value, tb):
    import traceback
    try:
        with open("D:/chrom/screenshot/AITranslator/crash_log.txt", "w", encoding="utf-8") as f:
            f.write(f"Type: {exctype}\n")
            f.write(f"Value: {value}\n")
            f.write("".join(traceback.format_exception(exctype, value, tb)))
    except:
        pass
    sys.__excepthook__(exctype, value, tb)
sys.excepthook = global_excepthook

# Force disable proxies for whole process / 強制在行程層級停用網路代理，避免本地 127.0.0.1 請求被阻斷
os.environ["QTWEBENGINE_DISABLE_PROXY"] = "1"
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["all_proxy"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["ALL_PROXY"] = ""

from pathlib import Path
import numpy as np
from PIL import Image, ImageGrab

# Windows 11 DPI awareness / Win11 DPI 辨識度設定
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Add NVIDIA DLL paths / 新增 NVIDIA DLL 路徑
site_packages = Path(sys.executable).parent / "Lib" / "site-packages"
for p in site_packages.glob("nvidia/*/bin"):
    os.environ["PATH"] = str(p) + os.pathsep + os.environ["PATH"]
    try:
        os.add_dll_directory(str(p))
    except Exception:
        pass

# Set QML style (must be before QApplication) / 設定 QML 樣式 (必須在 QApplication 之前)
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
os.environ["QT_OPENGL"] = "software"
os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
sys.argv.append("--disable-gpu")
sys.argv.append("--disable-gpu-compositing")
sys.argv.append("--disable-gpu-sandbox")
sys.argv.append("--no-sandbox")

# PySide6 imports / PySide6 模組匯入
from PySide6.QtCore import (
    QObject, Property, Signal, Slot, QTimer, QUrl, Qt, QSettings
)

from common.watchdog import WorkerState

COLOR_LIST = [
    "自動 [Auto]", "白色 [White]", "黑色 [Black]", "紅色 [Red]", 
    "黃色 [Yellow]", "綠色 [Green]", "藍色 [Blue]", "紫色 [Purple]",
    "橘色 [Orange]", "粉色 [Pink]", "青色 [Cyan]"
]

COLOR_MAP = {
    "自動 [Auto]": "white", "白色 [White]": "white", "黑色 [Black]": "black", 
    "紅色 [Red]": "#f38ba8", "黃色 [Yellow]": "#f9e2af", "綠色 [Green]": "#a6e3a1", 
    "藍色 [Blue]": "#89b4fa", "紫色 [Purple]": "#cba6f7", "橘色 [Orange]": "#fab387", 
    "粉色 [Pink]": "#f5c2e7", "青色 [Cyan]": "#94e2d5"
}

ANCHOR_COLOR_MAP = {
    "自動 [Auto]": "black", "白色 [White]": "white", "黑色 [Black]": "black", 
    "紅色 [Red]": "#f38ba8", "黃色 [Yellow]": "#f9e2af", "綠色 [Green]": "#a6e3a1", 
    "藍色 [Blue]": "#89b4fa", "紫色 [Purple]": "#cba6f7", "橘色 [Orange]": "#fab387", 
    "粉色 [Pink]": "#f5c2e7", "青色 [Cyan]": "#94e2d5"
}

from PySide6.QtGui import QGuiApplication, QIcon, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import qInstallMessageHandler
def _qt_message_handler(mode, context, message):
    pass
qInstallMessageHandler(_qt_message_handler)

from PySide6.QtWidgets import QApplication, QWidget

from common.hotkey_manager import GlobalHotkeyManager
from PySide6.QtCore import QThread

class GenericWorkerThread(QThread):
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.target(*self.args, **self.kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()

class AnchorMonitorThread(QThread):
    anchorUpdateRequired = Signal(str, object)

    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.running = True
        self.anchorUpdateRequired.connect(self.backend.handle_anchor_update_required)

    def run(self):
        try:
            import cv2
            import numpy as np
            import time
            from PIL import ImageGrab

            while self.running:
                time.sleep(0.1)
                
                with self.backend.anchor_lock:
                    anchors_to_process = {aid: dict(data) for aid, data in self.backend.anchor_data.items()}

                if not anchors_to_process:
                    continue

                # 超時解鎖檢查
                for aid, data in anchors_to_process.items():
                    if data.get('is_processing'):
                        start_time = data.get('processing_start_time', 0.0)
                        if time.time() - start_time > 4.0:
                            print(f"[AnchorMonitor] Anchor {aid} 處理超時 (4秒)，強制重置 is_processing", flush=True)
                            with self.backend.anchor_lock:
                                if aid in self.backend.anchor_data:
                                    self.backend.anchor_data[aid]['is_processing'] = False
                            data['is_processing'] = False

                try:
                    import ctypes
                    for aid, data in anchors_to_process.items():
                        hwnd = data.get("hwnd")
                        if hwnd:
                            try: ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
                            except: pass
                    
                    pil = ImageGrab.grab(all_screens=True)
                    
                    for aid, data in anchors_to_process.items():
                        hwnd = data.get("hwnd")
                        if hwnd:
                            try: ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0)
                            except: pass
                            
                    screen_np = np.array(pil.convert("RGB"))
                    screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)
                except Exception as e:
                    continue

                for aid, data in anchors_to_process.items():
                    if data.get('is_processing'):
                        continue
                    if data.get('is_interacting'):
                        continue

                    try:
                        x, y, w, h = data['x'], data['y'], data['w'], data['h']
                        
                        px, py = self.backend.get_physical_coords(x, y)
                        px_br, py_br = self.backend.get_physical_coords(x + w, y + h)
                        pw = px_br - px
                        ph = py_br - py
                        
                        sh, sw = screen_gray.shape
                        


                        cx1 = max(0, px); cy1 = max(0, py)
                        cx2 = min(sw, px + pw); cy2 = min(sh, py + ph)
                        
                        if cx2 <= cx1 or cy2 <= cy1:
                            continue
                            
                        current_gray = np.zeros((ph, pw), dtype=np.uint8)
                        current_rgb = np.zeros((ph, pw, 3), dtype=np.uint8)
                        
                        ox = cx1 - px; oy = cy1 - py
                        current_gray[oy:oy+(cy2-cy1), ox:ox+(cx2-cx1)] = screen_gray[cy1:cy2, cx1:cx2]
                        current_rgb[oy:oy+(cy2-cy1), ox:ox+(cx2-cx1)] = screen_np[cy1:cy2, cx1:cx2]
                        
                        need_update = False
                        last_ocr_gray = data.get('last_ocr_gray')
                        if last_ocr_gray is None:
                            need_update = True

                        elif current_gray.shape != last_ocr_gray.shape:
                            need_update = True

                        else:
                            mse = np.mean((current_gray.astype("float") - last_ocr_gray.astype("float")) ** 2)
                            if mse > 100:
                                need_update = True

                            
                        if need_update:
                            with self.backend.anchor_lock:
                                if aid in self.backend.anchor_data:
                                    self.backend.anchor_data[aid]['is_processing'] = True
                                    self.backend.anchor_data[aid]['last_ocr_gray'] = current_gray
                            self.anchorUpdateRequired.emit(aid, current_rgb)
                    except Exception as e:
                        pass
        except Exception as e:
            import traceback
            traceback.print_exc()


class AnchorBubbleWidget(QWidget):
    update_image_signal = Signal(object) # To receive QPixmap/QImage
    update_pos_signal = Signal(int, int)

    EDGE = 15

    def __init__(self, x, y, w, h, backend=None):
        super().__init__()
        self.backend = backend
        
        from PySide6.QtCore import QSettings
        settings = QSettings("AITranslator", "Settings")
        self.is_pinned = settings.value("AnchorAlwaysOnTop", False, type=bool)
        
        flags = Qt.Window | Qt.FramelessWindowHint
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.setGeometry(x, y, w, h)
        
        # WDA_EXCLUDEFROMCAPTURE is now dynamically toggled in AnchorMonitorThread
        pass
        
        self.x, self.y, self.w, self.h = x, y, w, h
        self.is_processing = False
        self.last_ocr_gray = None

        screen = self.screen()
        self.dpr = screen.devicePixelRatio() if screen else 1.0
        self.anchor_id = str(id(self))
        if self.backend:
            self.backend.register_anchor(self.anchor_id, x, y, w, h, self.dpr, self)

        # Remove CSS dependency and draw directly in paintEvent / 移除 CSS 依賴，改於 paintEvent 直接繪製

        from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.label.setMouseTracking(True)
        layout.addWidget(self.label)

        self.update_image_signal.connect(self.set_image)
        self.update_pos_signal.connect(self.set_pos)

        self.btn_close = QPushButton("✕", self)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet("background: #f38ba8; color: white; border: none; border-radius: 12px; font-weight: bold;")
        self.btn_close.clicked.connect(self.close_anchor)
        self.btn_close.move(self.width() - 30, 6)

        self.btn_pin = QPushButton("📌", self)
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.setCursor(Qt.PointingHandCursor)
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        self.btn_pin.move(self.width() - 60, 6)
        
        self.color_list = [
            "自動 [Auto]", "白色 [White]", "黑色 [Black]", "紅色 [Red]", 
            "黃色 [Yellow]", "綠色 [Green]", "藍色 [Blue]", "紫色 [Purple]",
            "橘色 [Orange]", "粉色 [Pink]", "青色 [Cyan]"
        ]
        self.fontColor = self.color_list[0]
        
        from PySide6.QtWidgets import QComboBox, QLabel
        
        self.lbl_color = QLabel(self)
        self.lbl_color.setFixedSize(60, 24)
        self.lbl_color.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        self.lbl_color.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_color.move(self.width() - 425, 6)

        self.combo_color = QComboBox(self)
        self.combo_color.addItems(self.color_list)
        self.combo_color.setFixedSize(110, 24)
        self.combo_color.currentIndexChanged.connect(self.on_color_changed)
        self.combo_color.setStyleSheet("""
            QComboBox {
                background: #1e1e2e; color: #cdd6f4; border: 1px solid #cba6f7; border-radius: 4px; padding-left: 5px; font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1e1e2e; color: #cdd6f4; selection-background-color: #cba6f7; selection-color: #11111b;
            }
        """)
        self.combo_color.move(self.width() - 360, 6)
        
        self.borderColor = COLOR_LIST[0]
        
        self.lbl_border = QLabel(self)
        self.lbl_border.setFixedSize(60, 24)
        self.lbl_border.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        self.lbl_border.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_border.move(self.width() - 245, 6)

        self.combo_border = QComboBox(self)
        self.combo_border.addItems(COLOR_LIST)
        self.combo_border.setFixedSize(110, 24)
        self.combo_border.currentIndexChanged.connect(self.on_border_changed)
        self.combo_border.setStyleSheet(self.combo_color.styleSheet())
        self.combo_border.move(self.width() - 180, 6)

        from PySide6.QtCore import QSettings
        settings = QSettings("AITranslator", "Settings")
        c_idx = settings.value("AnchorFontColorIdx", 0, type=int)
        b_idx = settings.value("AnchorBorderColorIdx", 0, type=int)
        if 0 <= c_idx < self.combo_color.count():
            self.combo_color.setCurrentIndex(c_idx)
            self.fontColor = self.color_list[c_idx]
        if 0 <= b_idx < self.combo_border.count():
            self.combo_border.setCurrentIndex(b_idx)
            self.borderColor = COLOR_LIST[b_idx]
        
        if self.backend:
            self.backend.uiLangChanged.connect(self.update_ui_lang)
            self.update_ui_lang()
        
        # Initialize window movement and resizing states / 初始化視窗移動與縮放狀態
        self._moving = False
        self._move_offset = None
        self._resize_edges = None
        self._resize_start = None
        self._resize_geo = None
        self.setMouseTracking(True)
        
        self.dash_offset = 0
        from PySide6.QtCore import QTimer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_border)
        self.anim_timer.start(50)

        # Add ESC shortcut to ensure the window can close / 新增 ESC 快捷鍵以確保視窗可關閉
        from PySide6.QtGui import QShortcut, QKeySequence
        s = QShortcut(QKeySequence("Esc"), self)
        s.setContext(Qt.ApplicationShortcut)
        s.activated.connect(self.close_anchor)

        # ESC shortcut defined below

    def update_border(self):
        self.dash_offset -= 1
        if self.dash_offset < -20:
            self.dash_offset = 0
        self.update()

    def update_ui_lang(self):
        if self.backend:
            lang = getattr(self.backend, "uiLang", "繁體中文")
            if hasattr(self, "lbl"): self.lbl.setText(self.backend.get_translation("翻譯列表", lang))
            if hasattr(self, "lbl_border"): self.lbl_border.setText(self.backend.get_translation("邊框顏色", lang))
            if hasattr(self, "lbl_color"): self.lbl_color.setText(self.backend.get_translation("文字顏色", lang))
            if hasattr(self, "btn_close"): self.btn_close.setToolTip(self.backend.get_translation("關閉", lang))
            if hasattr(self, "btn_pin"):
                tip_key = "取消至頂" if self.is_pinned else "至頂"
                self.btn_pin.setToolTip(self.backend.get_translation(tip_key, lang))
                self.update_pin_button_style()
            if hasattr(self, "combo_border"):
                self.combo_border.blockSignals(True)
                for i, c in enumerate(COLOR_LIST):
                    self.combo_border.setItemText(i, self.backend.get_translation(c, lang))
                self.combo_border.blockSignals(False)

            if hasattr(self, "combo_color"):
                self.combo_color.blockSignals(True)
                for i, c in enumerate(self.color_list):
                    self.combo_color.setItemText(i, self.backend.get_translation(c, lang))
                self.combo_color.blockSignals(False)

    def toggle_always_on_top(self):
        self.is_pinned = not self.is_pinned
        from PySide6.QtCore import QSettings
        QSettings("AITranslator", "Settings").setValue("AnchorAlwaysOnTop", self.is_pinned)
        
        geo = self.geometry()
        flags = self.windowFlags()
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        self.setGeometry(geo)
        self.show()
        self.update_ui_lang()

    def update_pin_button_style(self):
        if hasattr(self, "btn_pin"):
            if self.is_pinned:
                self.btn_pin.setStyleSheet("background: #a6e3a1; color: #11111b; border: none; border-radius: 12px; font-weight: bold; font-size: 11px;")
            else:
                self.btn_pin.setStyleSheet(
                    "background: #45475a; color: white; border: none; border-radius: 12px; font-weight: bold; font-size: 11px;"
                    "hover { background: #585b70; }")
    def on_color_changed(self, idx):
        if idx < 0: return
        self.fontColor = self.color_list[idx]
        from PySide6.QtCore import QSettings
        QSettings("AITranslator", "Settings").setValue("AnchorFontColorIdx", idx)
        self.last_ocr_gray = None  # Force re-render on next tick
        if self.backend:
            self.backend.update_anchor_config(self.anchor_id, last_ocr_gray=None)
        
    def on_border_changed(self, idx):
        if idx < 0: return
        self.borderColor = COLOR_LIST[idx]
        from PySide6.QtCore import QSettings
        QSettings("AITranslator", "Settings").setValue("AnchorBorderColorIdx", idx)
        self.update()

    @property
    def is_interacting(self):
        return getattr(self, '_moving', False) or bool(getattr(self, '_resize_edges', None))

    def get_font_color_tuple(self):
        mapping = {
            "白色": (255, 255, 255), "黑色": (0, 0, 0),
            "紅色": (255, 20, 20), "黃色": (255, 255, 0),
            "綠色": (0, 255, 0), "藍色": (0, 128, 255),
            "紫色": (255, 0, 255), "橘色": (255, 128, 0),
            "粉色": (255, 105, 180), "青色": (0, 255, 255)
        }
        for k, v in mapping.items():
            if k in self.fontColor: return v
        return None

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
        from PySide6.QtCore import Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set translucent background for mouse event tracking / 設置透明背景以進行滑鼠事件追蹤
        painter.fillRect(self.rect(), QColor(0, 0, 0, 2))
        
        bc = ANCHOR_COLOR_MAP.get(self.borderColor, "black")
        pen = QPen(QColor(bc))
        pen.setWidth(4)
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([4, 4])
        pen.setDashOffset(self.dash_offset)
        painter.setPen(pen)
        
        path = QPainterPath()
        path.addRoundedRect(2, 2, self.width()-4, self.height()-4, 8, 8)
        painter.drawPath(path)

    def close_anchor(self):
        if getattr(self, '_closing', False):
            return
        self._closing = True
        if self.backend:
            try:
                self.backend.uiLangChanged.disconnect(self.update_ui_lang)
            except RuntimeError:
                pass
            self.backend.unregister_anchor(self.anchor_id)
            if self in self.backend.anchors:
                self.backend.anchors.remove(self)
        self.close()
        self.deleteLater()

    def closeEvent(self, event):
        self.close_anchor()
        super().closeEvent(event)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        screen = self.screen()
        if screen:
            self.dpr = screen.devicePixelRatio()
        self.btn_close.move(self.width() - 30, 6)
        if hasattr(self, 'btn_pin'):
            self.btn_pin.move(self.width() - 60, 6)
        if hasattr(self, 'lbl_color'):
            self.lbl_color.move(self.width() - 425, 6)
        if hasattr(self, 'combo_color'):
            self.combo_color.move(self.width() - 360, 6)
        if hasattr(self, 'lbl_border'):
            self.lbl_border.move(self.width() - 245, 6)
        if hasattr(self, 'combo_border'):
            self.combo_border.move(self.width() - 180, 6)
        self.w, self.h = self.width(), self.height()
        if self.backend:
            self.backend.update_anchor_config(self.anchor_id, w=self.w, h=self.h, dpr=self.dpr, is_interacting=self.is_interacting)
        
    def moveEvent(self, event):
        super().moveEvent(event)
        self.x = self.pos().x()
        self.y = self.pos().y()
        screen = self.screen()
        if screen:
            self.dpr = screen.devicePixelRatio()
        if self.backend:
            self.backend.update_anchor_config(self.anchor_id, x=self.x, y=self.y, dpr=self.dpr, is_interacting=self.is_interacting)

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt
        if event.key() == Qt.Key_Escape:
            self.close_anchor()

    @Slot(object)
    def set_image(self, qimage):
        if self.is_interacting:
            return
        from PySide6.QtGui import QPixmap
        self.label.setPixmap(QPixmap.fromImage(qimage))

    @Slot(int, int)
    def set_pos(self, x, y):
        self.move(x, y)
        self.x, self.y = x, y

    # Window edge detection for resizing / 用於縮放的視窗邊緣偵測
    def _edge_at(self, pos):
        M = self.EDGE
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        e = []
        if x < M: e.append('L')
        if x > w - M: e.append('R')
        if y < M: e.append('T')
        if y > h - M: e.append('B')
        return tuple(e) if e else None

    def _set_edge_cursor(self, edges):
        from PySide6.QtCore import Qt
        if not edges:
            self.setCursor(Qt.ArrowCursor); return
        s = set(edges)
        if s <= {'L'} or s <= {'R'}:
            self.setCursor(Qt.SizeHorCursor)
        elif s <= {'T'} or s <= {'B'}:
            self.setCursor(Qt.SizeVerCursor)
        elif s in ({'T', 'L'}, {'B', 'R'}):
            self.setCursor(Qt.SizeFDiagCursor)
        elif s in ({'T', 'R'}, {'B', 'L'}):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, ev):
        from PySide6.QtCore import Qt
        if ev.button() == Qt.LeftButton:
            from PySide6.QtGui import QImage
            self.update_image_signal.emit(QImage())
            p = ev.position().toPoint()
            edges = self._edge_at(p)
            if edges:
                self._resize_edges = edges
                self._resize_start = ev.globalPosition().toPoint()
                g = self.geometry()
                self._resize_geo = (g.x(), g.y(), g.width(), g.height())
            else:
                self._moving = True
                self._move_offset = ev.globalPosition().toPoint() - self.pos()
            if self.backend:
                self.backend.update_anchor_config(self.anchor_id, is_interacting=True)
        elif ev.button() == Qt.RightButton:
            self.close_anchor()

    def mouseMoveEvent(self, ev):
        from PySide6.QtCore import Qt
        if self._resize_edges and self._resize_start:
            gp = ev.globalPosition().toPoint()
            dx = gp.x() - self._resize_start.x()
            dy = gp.y() - self._resize_start.y()
            ox, oy, ow, oh = self._resize_geo
            x, y, w, h = ox, oy, ow, oh
            if 'L' in self._resize_edges: x += dx; w -= dx
            if 'R' in self._resize_edges: w += dx
            if 'T' in self._resize_edges: y += dy; h -= dy
            if 'B' in self._resize_edges: h += dy
            if w >= 50 and h >= 50:
                self.setGeometry(x, y, w, h)
                self.x, self.y, self.w, self.h = x, y, w, h
        elif self._moving and self._move_offset:
            p = ev.globalPosition().toPoint() - self._move_offset
            self.move(p)
            self.x, self.y = p.x(), p.y()
        else:
            self._set_edge_cursor(self._edge_at(ev.position().toPoint()))

    def mouseReleaseEvent(self, ev):
        from PySide6.QtCore import Qt
        self._moving = False
        self._resize_edges = None
        self.last_ocr_gray = None
        self.setCursor(Qt.ArrowCursor)
        if self.backend:
            self.backend.update_anchor_config(self.anchor_id, is_interacting=False, last_ocr_gray=None)


class SnippingWidget(QWidget):
    snip_completed = Signal(int, int, int, int, object)
    snip_cancelled = Signal()

    def __init__(self, backend=None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setCursor(Qt.CrossCursor)

        self.start_point = None
        self.current_point = None
        self.is_snipping = False

        from PIL import ImageGrab
        self.screen_img = ImageGrab.grab(all_screens=True)
        
        from common.render import pil_to_qimage
        from PySide6.QtGui import QPixmap, QGuiApplication
        from PySide6.QtCore import QRect

        self.bg_pixmap = QPixmap.fromImage(pil_to_qimage(self.screen_img))
        dpr = QGuiApplication.primaryScreen().devicePixelRatio()
        self.bg_pixmap.setDevicePixelRatio(dpr)

        rect = QRect()
        for screen in QGuiApplication.screens():
            rect = rect.united(screen.geometry())
        self.setGeometry(rect)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen, QRegion
        from PySide6.QtCore import Qt, QRect
        painter = QPainter(self)
        
        # Draw screen capture to achieve "freeze frame" effect / 繪製螢幕畫面以達到「凍結螢幕」效果
        painter.drawPixmap(0, 0, self.bg_pixmap)
        
        # Calculate mask region for screen selection / 計算螢幕選取的遮罩區域
        mask_region = QRegion(self.rect())
        selection_rect = None
        if self.start_point and self.current_point:
            selection_rect = QRect(self.start_point, self.current_point).normalized()
            mask_region = mask_region.subtracted(QRegion(selection_rect))
            
        painter.setClipRegion(mask_region)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        painter.setClipping(False)

        if selection_rect:
            pen = QPen(QColor("#0078D7"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawRect(selection_rect)

            w = selection_rect.width()
            h = selection_rect.height()
            dim_text = f"{w} x {h}"
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            
            fm = painter.fontMetrics()
            text_rect = fm.boundingRect(dim_text)
            text_rect.adjust(-5, -2, 5, 2)
            
            tooltip_x = self.current_point.x() + 10
            tooltip_y = self.current_point.y() + 10
            
            if tooltip_x + text_rect.width() > self.width():
                tooltip_x = self.current_point.x() - text_rect.width() - 10
            if tooltip_y + text_rect.height() > self.height():
                tooltip_y = self.current_point.y() - text_rect.height() - 10
                
            text_rect.moveTo(tooltip_x, tooltip_y)
            painter.drawRoundedRect(text_rect, 3, 3)
            
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_rect, Qt.AlignCenter, dim_text)

    def mousePressEvent(self, event):
        from PySide6.QtCore import Qt
        if event.button() == Qt.LeftButton:
            self.start_point = event.position().toPoint()
            self.current_point = self.start_point
            self.is_snipping = True
            self.update()
        elif event.button() == Qt.RightButton:
            self.snip_cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event):
        if self.is_snipping:
            self.current_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        from PySide6.QtCore import Qt, QRect
        if event.button() == Qt.LeftButton and self.is_snipping:
            self.is_snipping = False
            self.current_point = event.position().toPoint()
            
            selection_rect = QRect(self.start_point, self.current_point).normalized()
            
            if selection_rect.width() > 10 and selection_rect.height() > 10:
                l = selection_rect.x()
                t = selection_rect.y()
                r = selection_rect.x() + selection_rect.width()
                b = selection_rect.y() + selection_rect.height()
                
                screen = self.screen()
                dpr = screen.devicePixelRatio() if screen else 1.0
                
                global_l = l + self.x()
                global_t = t + self.y()
                global_r = r + self.x()
                global_b = b + self.y()
                
                if self.backend:
                    pl, pt = self.backend.get_physical_coords(global_l, global_t)
                    pr, pb = self.backend.get_physical_coords(global_r, global_b)
                else:
                    pl = int(global_l * dpr)
                    pt = int(global_t * dpr)
                    pr = int(global_r * dpr)
                    pb = int(global_b * dpr)
                
                cropped_img = self.screen_img.crop((pl, pt, pr, pb))
                
                self.snip_completed.emit(global_l, global_t, global_r, global_b, cropped_img)
            else:
                self.snip_cancelled.emit()
            self.close()

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt
        if event.key() == Qt.Key_Escape:
            self.snip_cancelled.emit()
            self.close()


# AppBackend QML Bridge (Exposes Python API to React/QML) / AppBackend 橋接器 (將 Python API 暴露給 React/QML)

from PySide6.QtWidgets import QFrame

class ResultWindow(QFrame):
    """Translation Result Window - borderless, draggable, resizable, stay-on-top / 翻譯結果視窗 - 無邊框、可移動、可調整大小、置頂"""

    TITLE_H = 34
    EDGE = 15

    def paintEvent(self, event):
        from PySide6.QtWidgets import QStyleOption, QStyle
        from PySide6.QtGui import QPainter
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, p, self)

    def __init__(self, qim, l, t, r, b, backend):
        super().__init__()
        self.backend = backend
        self.qim = qim
        
        from PySide6.QtCore import QSettings
        settings = QSettings("AITranslator", "Settings")
        self.is_pinned = settings.value("ResultAlwaysOnTop", False, type=bool)
        
        flags = Qt.Window | Qt.FramelessWindowHint
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setMinimumSize(200, 120)

        self.setObjectName("MainWindow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import QPoint
        screen = QGuiApplication.screenAt(QPoint(l, t))
        if not screen:
            screen = QGuiApplication.primaryScreen()
        screen_geo = screen.geometry()
        
        img_w, img_h = r - l, b - t
        target_y = t - self.TITLE_H
        if target_y < screen_geo.top():
            target_y = screen_geo.top()
            
        self.setGeometry(l, target_y, img_w, img_h + self.TITLE_H)
        self.setStyleSheet(f"\n            #MainWindow {{\n                background-color: #1e1e2e; \n                border: 2px solid white;\n                border-radius: 4px;\n            }}\n        ")

        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PySide6.QtGui import QPixmap

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(4, 4, 4, 4)  # Adjust margins to show borders / 調整邊距以正常顯示外框
        main_lay.setSpacing(0)

        # Title bar / 標題列
        tb = QWidget()
        tb.setFixedHeight(self.TITLE_H)
        tb.setStyleSheet("background:#181825; border-bottom:1px solid #45475a;")
        tb_lay = QHBoxLayout(tb)
        tb_lay.setContentsMargins(10, 0, 4, 0)
        self.lbl = QLabel(self.backend.get_translation("翻譯結果", getattr(self.backend, "uiLang", "繁體中文")) if self.backend else "翻譯結果")
        self.lbl.setStyleSheet("color:#cdd6f4; font:13px 'Microsoft JhengHei'; border:none; background:transparent;")
        tb_lay.addWidget(self.lbl)
        tb_lay.addStretch()
        from PySide6.QtWidgets import QComboBox
        self.lbl_border = QLabel(self.backend.get_translation("邊框顏色", getattr(self.backend, "uiLang", "繁體中文")) if self.backend else "邊框顏色")
        self.lbl_border.setStyleSheet("color:#cdd6f4; font:12px 'Microsoft JhengHei'; border:none; background:transparent;")
        tb_lay.addWidget(self.lbl_border)
        self.combo_border = QComboBox()
        self.combo_border.addItems(COLOR_LIST)
        self.combo_border.setFixedSize(110, 24)
        self.combo_border.setStyleSheet("""
            QComboBox {
                background: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding-left: 5px; font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1e1e2e; color: #cdd6f4; selection-background-color: #cba6f7; selection-color: #11111b;
            }
        """)
        self.combo_border.currentIndexChanged.connect(self.on_border_changed)
        tb_lay.addWidget(self.combo_border)
        from PySide6.QtCore import QSettings
        settings = QSettings("AITranslator", "Settings")
        b_idx = settings.value("ResultBorderColorIdx", 0, type=int)
        if 0 <= b_idx < self.combo_border.count():
            self.combo_border.setCurrentIndex(b_idx)
            if b_idx == 0:
                self.on_border_changed(0)
        self.btn_save = QPushButton("💾")
        self.btn_save.setFixedSize(26, 26)
        self.btn_save.setToolTip(self.backend.get_translation("另外儲存圖", getattr(self.backend, "uiLang", "繁體中文")) if self.backend else "另外儲存圖")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(
            "QPushButton{background:#89b4fa;color:white;border:none;border-radius:4px;font-size:14px}"
            "QPushButton:hover{background:#74c7ec}")
        self.btn_save.clicked.connect(self.save_image)
        tb_lay.addWidget(self.btn_save)

        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(26, 26)
        self.btn_pin.setCursor(Qt.PointingHandCursor)
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        tb_lay.addWidget(self.btn_pin)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setToolTip(self.backend.get_translation("關閉", getattr(self.backend, "uiLang", "繁體中文")) if self.backend else "關閉")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "QPushButton{background:#f38ba8;color:white;border:none;border-radius:4px;font-size:14px;font-weight:bold}"
            "QPushButton:hover{background:#eba0ac}")
        self.btn_close.clicked.connect(self.close_window)
        tb_lay.addWidget(self.btn_close)
        main_lay.addWidget(tb)
        if self.backend:
            self.backend.uiLangChanged.connect(self.update_ui_lang)
            self.update_ui_lang()

        # Image display label / 圖片顯示標籤
        self.label = QLabel()
        self.label.setPixmap(QPixmap.fromImage(qim))
        self.label.setScaledContents(True)
        self.label.setStyleSheet("border:none; background:transparent;")
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        main_lay.addWidget(self.label)

        # Window dragging and resizing state / 視窗拖曳與縮放狀態
        self._moving = False
        self._move_offset = None
        self._resize_edges = None
        self._resize_start = None
        self._resize_geo = None
        self.setMouseTracking(True)

        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.close_window)

    # Window edge detection for resizing / 視窗邊緣偵測 (用於縮放)
    def _edge_at(self, pos):
        M = self.EDGE
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        e = []
        if x < M: e.append('L')
        if x > w - M: e.append('R')
        if y < M: e.append('T')
        if y > h - M: e.append('B')
        return tuple(e) if e else None

    def _set_edge_cursor(self, edges):
        if not edges:
            self.setCursor(Qt.ArrowCursor); return
        s = set(edges)
        if s <= {'L'} or s <= {'R'}:
            self.setCursor(Qt.SizeHorCursor)
        elif s <= {'T'} or s <= {'B'}:
            self.setCursor(Qt.SizeVerCursor)
        elif s in ({'T', 'L'}, {'B', 'R'}):
            self.setCursor(Qt.SizeFDiagCursor)
        elif s in ({'T', 'R'}, {'B', 'L'}):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            p = ev.position().toPoint()
            edges = self._edge_at(p)
            if edges:
                self._resize_edges = edges
                self._resize_start = ev.globalPosition().toPoint()
                g = self.geometry()
                self._resize_geo = (g.x(), g.y(), g.width(), g.height())
            elif p.y() <= self.TITLE_H:
                self._moving = True
                self._move_offset = ev.globalPosition().toPoint() - self.pos()
        elif ev.button() == Qt.RightButton:
            self.close_window()

    def mouseMoveEvent(self, ev):
        if self._resize_edges and self._resize_start:
            gp = ev.globalPosition().toPoint()
            dx = gp.x() - self._resize_start.x()
            dy = gp.y() - self._resize_start.y()
            ox, oy, ow, oh = self._resize_geo
            x, y, w, h = ox, oy, ow, oh
            if 'L' in self._resize_edges: x += dx; w -= dx
            if 'R' in self._resize_edges: w += dx
            if 'T' in self._resize_edges: y += dy; h -= dy
            if 'B' in self._resize_edges: h += dy
            if w >= self.minimumWidth() and h >= self.minimumHeight():
                self.setGeometry(x, y, w, h)
        elif self._moving and self._move_offset:
            self.move(ev.globalPosition().toPoint() - self._move_offset)
        else:
            self._set_edge_cursor(self._edge_at(ev.position().toPoint()))

    def mouseReleaseEvent(self, ev):
        self._moving = False
        self._resize_edges = None
        self.setCursor(Qt.ArrowCursor)

    def on_border_changed(self, idx):
        if idx < 0: return
        color = COLOR_MAP.get(COLOR_LIST[idx], "white")
        from PySide6.QtCore import QSettings
        QSettings("AITranslator", "Settings").setValue("ResultBorderColorIdx", idx)
        self.setStyleSheet(f"\n            #MainWindow {{\n                background-color: #1e1e2e; \n                border: 2px solid {color};\n                border-radius: 4px;\n            }}\n        ")

    def save_image(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save Image / 儲存圖片", "", "Images (*.png *.jpg)")
        if path:
            self.qim.save(path)

    def close_window(self):
        self.close()

    def closeEvent(self, event):
        if self.backend:
            try:
                self.backend.uiLangChanged.disconnect(self.update_ui_lang)
            except RuntimeError:
                pass
            if self in self.backend.windows:
                try:
                    self.backend.windows.remove(self)
                except ValueError:
                    pass
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def update_ui_lang(self):
        if self.backend:
            lang = getattr(self.backend, "uiLang", "繁體中文")
            if hasattr(self, "lbl"): self.lbl.setText(self.backend.get_translation("翻譯結果", lang))
            if hasattr(self, "lbl_border"): self.lbl_border.setText(self.backend.get_translation("邊框顏色", lang))
            if hasattr(self, "btn_save"): self.btn_save.setToolTip(self.backend.get_translation("另外儲存圖", lang))
            if hasattr(self, "btn_close"): self.btn_close.setToolTip(self.backend.get_translation("關閉", lang))
            if hasattr(self, "btn_pin"):
                tip_key = "取消至頂" if self.is_pinned else "至頂"
                self.btn_pin.setToolTip(self.backend.get_translation(tip_key, lang))
                self.update_pin_button_style()
            
            if hasattr(self, "combo_border"):
                self.combo_border.blockSignals(True)
                for i, c in enumerate(COLOR_LIST):
                    self.combo_border.setItemText(i, self.backend.get_translation(c, lang))
                self.combo_border.blockSignals(False)

    def toggle_always_on_top(self):
        self.is_pinned = not self.is_pinned
        from PySide6.QtCore import QSettings
        QSettings("AITranslator", "Settings").setValue("ResultAlwaysOnTop", self.is_pinned)
        
        geo = self.geometry()
        flags = self.windowFlags()
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        self.setGeometry(geo)
        self.show()
        self.update_ui_lang()

    def update_pin_button_style(self):
        if hasattr(self, "btn_pin"):
            if self.is_pinned:
                self.btn_pin.setStyleSheet("QPushButton{background:#a6e3a1;color:#11111b;border:none;border-radius:4px;font-size:14px}")
            else:
                self.btn_pin.setStyleSheet(
                    "QPushButton{background:#45475a;color:white;border:none;border-radius:4px;font-size:14px}"
                    "QPushButton:hover{background:#585b70}")




class ListResultWindow(QFrame):
    """Translation List Window - borderless, draggable, stay-on-top / 翻譯列表視窗 - 無邊框、可移動、置頂"""

    TITLE_H = 30

    def paintEvent(self, event):
        from PySide6.QtWidgets import QStyleOption, QStyle
        from PySide6.QtGui import QPainter
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, p, self)

    def __init__(self, translated, colors, l, t, r, b, backend):
        super().__init__()
        self.backend = backend
        
        from PySide6.QtCore import QSettings
        settings = QSettings("AITranslator", "Settings")
        self.is_pinned = settings.value("ListAlwaysOnTop", False, type=bool)
        
        flags = Qt.Window | Qt.FramelessWindowHint
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.setMouseTracking(True)
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import QPoint
        screen = QGuiApplication.screenAt(QPoint(l, t))
        if not screen:
            screen = QGuiApplication.primaryScreen()
        screen_geo = screen.geometry()
        
        h = max(200, min(300, b - t))
        w = max(300, r - l)
        target_y = t - h
        if target_y < screen_geo.top():
            target_y = screen_geo.top()
            
        self.setGeometry(l, target_y, w, h)
        
        self._resize_edges = None
        self._resize_start = None
        self._resize_geo = None
        self.setMinimumSize(200, 100)

        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser

        self.setObjectName("MainWindow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet("""
            #MainWindow {
                background-color: rgba(30, 30, 46, 240);
                border: 2px solid white;
                border-radius: 8px;
            }
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 4, 10, 10)  # Increase margins so borders are grabbable
        main_lay.setSpacing(0)

        # Title bar / 標題列
        tb = QWidget()
        tb.setFixedHeight(self.TITLE_H)
        tb.setStyleSheet("background:transparent; border:none; border-bottom:1px solid #45475a;")
        tb_lay = QHBoxLayout(tb)
        tb_lay.setContentsMargins(10, 0, 4, 0)
        self.lbl = QLabel(self.backend.get_translation("翻譯列表", getattr(self.backend, "uiLang", "繁體中文")) if self.backend else "翻譯列表")
        self.lbl.setStyleSheet("color:#cdd6f4; font:12px 'Microsoft JhengHei'; border:none; background:transparent;")
        tb_lay.addWidget(self.lbl)
        tb_lay.addStretch()
        from PySide6.QtWidgets import QComboBox
        self.lbl_border = QLabel(self.backend.get_translation("邊框顏色", getattr(self.backend, "uiLang", "繁體中文")) if self.backend else "邊框顏色")
        self.lbl_border.setStyleSheet("color:#cdd6f4; font:12px 'Microsoft JhengHei'; border:none; background:transparent;")
        tb_lay.addWidget(self.lbl_border)
        self.combo_border = QComboBox()
        self.combo_border.addItems(COLOR_LIST)
        self.combo_border.setFixedSize(110, 24)
        self.combo_border.setStyleSheet("""
            QComboBox {
                background: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding-left: 5px; font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1e1e2e; color: #cdd6f4; selection-background-color: #cba6f7; selection-color: #11111b;
            }
        """)
        self.combo_border.currentIndexChanged.connect(self.on_border_changed)
        tb_lay.addWidget(self.combo_border)
        from PySide6.QtCore import QSettings
        settings = QSettings("AITranslator", "Settings")
        b_idx = settings.value("ListBorderColorIdx", 0, type=int)
        if 0 <= b_idx < self.combo_border.count():
            self.combo_border.setCurrentIndex(b_idx)
            if b_idx == 0:
                self.on_border_changed(0)
        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setCursor(Qt.PointingHandCursor)
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        tb_lay.addWidget(self.btn_pin)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setToolTip(self.backend.get_translation("關閉", getattr(self.backend, "uiLang", "繁體中文")) if self.backend else "關閉")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "QPushButton{background:#f38ba8;color:white;border:none;border-radius:11px;font-weight:bold}"
            "QPushButton:hover{background:#eba0ac}")
        self.btn_close.clicked.connect(self.close_window)
        tb_lay.addWidget(self.btn_close)
        main_lay.addWidget(tb)
        if self.backend:
            self.backend.uiLangChanged.connect(self.update_ui_lang)
            self.update_ui_lang()

        # Translation content area / 翻譯內容顯示區域
        content_tb = QTextBrowser()
        content_tb.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                color: #cdd6f4;
                font-family: 'Microsoft JhengHei';
                font-size: 14px;
                border: none;
            }
        """)

        html = ""
        for color_hex, trans in zip(colors, translated):
            if trans:
                html += f"<div style='color:{color_hex}; padding:2px; margin-bottom:5px;'>{trans}</div>"

        content_tb.setHtml(html)
        main_lay.addWidget(content_tb)

        # Resize handle control / 縮放控制項
        from PySide6.QtWidgets import QSizeGrip
        bottom_lay = QHBoxLayout()
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.addStretch()
        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        grip.setStyleSheet("background: transparent;")
        bottom_lay.addWidget(grip)
        main_lay.addLayout(bottom_lay)

        # Window dragging and resizing state / 視窗拖曳與縮放狀態
        self._moving = False
        self._move_offset = None

        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.close_window)

    def on_border_changed(self, idx):
        if idx < 0: return
        color = COLOR_MAP.get(COLOR_LIST[idx], "white")
        from PySide6.QtCore import QSettings
        QSettings("AITranslator", "Settings").setValue("ListBorderColorIdx", idx)
        self.setStyleSheet(f"""
            #MainWindow {{
                background-color: rgba(30, 30, 46, 240);
                border: 2px solid {color};
                border-radius: 8px;
            }}
        """)

    def close_window(self):
        self.close()

    def closeEvent(self, event):
        if self.backend:
            try:
                self.backend.uiLangChanged.disconnect(self.update_ui_lang)
            except RuntimeError:
                pass
            if self in self.backend.windows:
                try:
                    self.backend.windows.remove(self)
                except ValueError:
                    pass
        super().closeEvent(event)

    def _edge_at(self, p):
        M = 10
        w, h = self.width(), self.height()
        x, y = p.x(), p.y()
        e = []
        if x < M: e.append('L')
        if x > w - M: e.append('R')
        if y < M: e.append('T')
        if y > h - M: e.append('B')
        return tuple(e) if e else None

    def _set_edge_cursor(self, edges):
        if not edges:
            self.setCursor(Qt.ArrowCursor); return
        s = set(edges)
        if s <= {'L'} or s <= {'R'}:
            self.setCursor(Qt.SizeHorCursor)
        elif s <= {'T'} or s <= {'B'}:
            self.setCursor(Qt.SizeVerCursor)
        elif s in ({'T', 'L'}, {'B', 'R'}):
            self.setCursor(Qt.SizeFDiagCursor)
        elif s in ({'T', 'R'}, {'B', 'L'}):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            p = ev.position().toPoint()
            edges = self._edge_at(p)
            if edges:
                self._resize_edges = edges
                self._resize_start = ev.globalPosition().toPoint()
                g = self.geometry()
                self._resize_geo = (g.x(), g.y(), g.width(), g.height())
            elif p.y() <= self.TITLE_H:
                self._moving = True
                self._move_offset = ev.globalPosition().toPoint() - self.pos()
        elif ev.button() == Qt.RightButton:
            self.close_window()

    def mouseMoveEvent(self, ev):
        if self._resize_edges and self._resize_start:
            gp = ev.globalPosition().toPoint()
            dx = gp.x() - self._resize_start.x()
            dy = gp.y() - self._resize_start.y()
            ox, oy, ow, oh = self._resize_geo
            x, y, w, h = ox, oy, ow, oh
            if 'L' in self._resize_edges: x += dx; w -= dx
            if 'R' in self._resize_edges: w += dx
            if 'T' in self._resize_edges: y += dy; h -= dy
            if 'B' in self._resize_edges: h += dy
            if w >= self.minimumWidth() and h >= self.minimumHeight():
                self.setGeometry(x, y, w, h)
        elif self._moving and self._move_offset:
            self.move(ev.globalPosition().toPoint() - self._move_offset)
        else:
            self._set_edge_cursor(self._edge_at(ev.position().toPoint()))

    def mouseReleaseEvent(self, ev):
        self._moving = False
        self._resize_edges = None
        self.setCursor(Qt.ArrowCursor)

    def update_ui_lang(self):
        if self.backend:
            lang = getattr(self.backend, "uiLang", "繁體中文")
            if hasattr(self, "lbl"): self.lbl.setText(self.backend.get_translation("翻譯列表", lang))
            if hasattr(self, "lbl_border"): self.lbl_border.setText(self.backend.get_translation("邊框顏色", lang))
            if hasattr(self, "lbl_color"): self.lbl_color.setText(self.backend.get_translation("文字顏色", lang))
            if hasattr(self, "btn_close"): self.btn_close.setToolTip(self.backend.get_translation("關閉", lang))
            if hasattr(self, "btn_pin"):
                tip_key = "取消至頂" if self.is_pinned else "至頂"
                self.btn_pin.setToolTip(self.backend.get_translation(tip_key, lang))
                self.update_pin_button_style()

            if hasattr(self, "combo_border"):
                self.combo_border.blockSignals(True)
                for i, c in enumerate(COLOR_LIST):
                    self.combo_border.setItemText(i, self.backend.get_translation(c, lang))
                self.combo_border.blockSignals(False)

    def toggle_always_on_top(self):
        self.is_pinned = not self.is_pinned
        from PySide6.QtCore import QSettings
        QSettings("AITranslator", "Settings").setValue("ListAlwaysOnTop", self.is_pinned)
        
        geo = self.geometry()
        flags = self.windowFlags()
        if self.is_pinned:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        self.setGeometry(geo)
        self.show()
        self.update_ui_lang()

    def update_pin_button_style(self):
        if hasattr(self, "btn_pin"):
            if self.is_pinned:
                self.btn_pin.setStyleSheet("QPushButton{background:#a6e3a1;color:#11111b;border:none;border-radius:11px;font-size:12px}")
            else:
                self.btn_pin.setStyleSheet(
                    "QPushButton{background:#45475a;color:white;border:none;border-radius:11px;font-size:12px}"
                    "QPushButton:hover{background:#585b70}")
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class AppBackend(QObject):
    """Expose Python backend methods and properties to React/QML / 暴露後端屬性與方法給 React/QML"""

    # Define Qt Signals / 定義 Qt 信號
    hardwareChanged = Signal()
    engineChanged = Signal()
    srcLangChanged = Signal()
    tgtLangChanged = Signal()
    modeChanged = Signal()
    hotkeyDisplayChanged = Signal()
    tempHotkeyDisplayChanged = Signal()
    isRecordingChanged = Signal()
    ocrStateChanged = Signal()
    transStateChanged = Signal()
    transLabelChanged = Signal()
    inpaintStateChanged = Signal()
    statusTextChanged = Signal()
    statusColorChanged = Signal()
    uiLangChanged = Signal()
    openRouterKeyChanged = Signal()
    geminiKeyChanged = Signal()
    soundEnabledChanged = Signal()
    modeSoundEnabledChanged = Signal()
    fontColorChanged = Signal()
    themeNameChanged = Signal()
    # Mode hotkey signals / 模式快捷鍵信號
    overlayHotkeyDisplayChanged = Signal()
    anchorHotkeyDisplayChanged = Signal()
    listHotkeyDisplayChanged = Signal()
    overlayHotkeyRecordingChanged = Signal()
    anchorHotkeyRecordingChanged = Signal()
    listHotkeyRecordingChanged = Signal()
    # Fix 4: Create cross-thread signals / 修正 4: 建立跨線程信號
    _showOverlayResult = Signal(QImage, int, int, int, int)
    _showListResult = Signal(object, object, int, int, int, int)
    _workerStateChangedMain = Signal()

    def register_anchor(self, aid, x, y, w, h, dpr, anchor_widget=None):
        with self.anchor_lock:
            self.anchor_data[aid] = {
                "x": x, "y": y, "w": w, "h": h, "dpr": dpr,
                "is_processing": False,
                "processing_start_time": 0.0,
                "last_ocr_gray": None,
                "anchor": anchor_widget,
                "hwnd": int(anchor_widget.winId()) if anchor_widget else 0
            }

    def unregister_anchor(self, aid):
        with self.anchor_lock:
            if aid in self.anchor_data:
                del self.anchor_data[aid]
            
            # 如果是錨點模式且所有氣泡框都關閉了，立即釋放模型
            if self._mode == "anchor" and len(self.anchor_data) == 0:
                print("[主線程] 所有錨點氣泡框已關閉，釋放模型資源", flush=True)
                self._do_unload_models()

    def update_anchor_config(self, aid, **kwargs):
        with self.anchor_lock:
            if aid in self.anchor_data:
                for k, v in kwargs.items():
                    self.anchor_data[aid][k] = v

    
    def get_translation(self, text, lang=None):
        if not lang:
            lang = getattr(self, "uiLang", "繁體中文")
        
        # Map frontend language strings to UI_TRANSLATIONS keys
        lang_map = {
            "繁體中文": "繁體中文",
            "简体中文": "簡體中文",
            "English": "英文",
            "日本語": "日文",
            "한국어": "韓文",
            "Español": "西班牙文",
            "Français": "法文",
            "Deutsch": "德文",
            "Italiano": "義大利文",
            "Русский": "俄文",
            "العربية": "阿拉伯文",
            "हिन्दी": "印地文",
            "ไทย": "泰文",
            "Tiếng Việt": "越南文",
            "Português": "葡萄牙文",
            "Bahasa Indonesia": "印尼文",
            "Türkçe": "土耳其文"
        }
        
        mapped_lang = lang
        if isinstance(lang, str):
            for k, v in lang_map.items():
                if k in lang:
                    mapped_lang = v
                    break

        try:
            from common.i18n import UI_TRANSLATIONS
            return UI_TRANSLATIONS.get(mapped_lang, {}).get(text, text)
        except Exception:
            return text

    def cleanup(self):
        # Stop hotkey managers to release keyboard hooks
        for mgr_name in ['hotkey_mgr', 'hotkey_overlay_mgr', 'hotkey_anchor_mgr', 'hotkey_list_mgr']:
            mgr = getattr(self, mgr_name, None)
            if mgr:
                try:
                    mgr._cancel_record()
                except: pass
                if mgr._hotkey_handle is not None:
                    try:
                        import keyboard
                        keyboard.remove_hotkey(mgr._hotkey_handle)
                    except: pass
                setattr(self, mgr_name, None)
            
        # Stop anchor monitor thread
        if hasattr(self, 'anchor_monitor') and self.anchor_monitor:
            self.anchor_monitor.running = False
            self.anchor_monitor.wait(2000)
            self.anchor_monitor = None

        # Shutdown IPC Manager (cleans up OCR/Translator workers)
        if hasattr(self, 'ipc_manager') and self.ipc_manager:
            self.ipc_manager.shutdown()
            self.ipc_manager = None

    def __init__(self, parent=None):
        super().__init__(parent)
        from common.watchdog import WorkerManager
        self._wm = WorkerManager()
        self._wm.set_callback(self._workerStateChangedMain.emit)
        from threading import Lock, RLock
        self.anchor_lock = RLock()
        self.anchor_data = {}
        self.screen_lock = Lock()
        self.screen_infos = []
        self.jobs_lock = Lock()

        # Internal properties / 內部屬性初始化
        self._hardware = "gpu"

        self.anchors = []
        self.windows = []
        
        self.virtual_left = 0
        self.virtual_top = 0
        self._update_virtual_geometry()
        app = QGuiApplication.instance()
        if app:
            app.screenAdded.connect(self._update_virtual_geometry)
            app.screenRemoved.connect(self._update_virtual_geometry)

        self.anchor_monitor = AnchorMonitorThread(self)
        self.anchor_monitor.start()

        import common.hotkey_manager as hk_mod
        hk_mod._backend_ref = self

        # Initialize hotkey manager / 初始化快捷鍵管理器
        self.hotkey_mgr = GlobalHotkeyManager(default_hotkey="win+shift+d")
        self.hotkey_mgr.hotkeyDisplayChanged.connect(lambda _: self.hotkeyDisplayChanged.emit())
        self.hotkey_mgr.tempHotkeyDisplayChanged.connect(lambda _: self.tempHotkeyDisplayChanged.emit())
        self.hotkey_mgr.isRecordingChanged.connect(lambda _: self.isRecordingChanged.emit())
        self.hotkey_mgr.hotkeyTriggered.connect(self.check_hotkey)
        self.hotkey_mgr.hotkeyRegisterFailed.connect(self._on_hotkey_failed)

        # Initialize mode hotkey managers / 初始化模式快捷鍵管理器
        self.hotkey_overlay_mgr = GlobalHotkeyManager(default_hotkey="shift+f1")
        self.hotkey_overlay_mgr.hotkeyDisplayChanged.connect(lambda _: self.overlayHotkeyDisplayChanged.emit())
        self.hotkey_overlay_mgr.isRecordingChanged.connect(lambda _: self.overlayHotkeyRecordingChanged.emit())
        self.hotkey_overlay_mgr.hotkeyTriggered.connect(lambda: self._on_mode_hotkey_triggered("overlay"))

        self.hotkey_anchor_mgr = GlobalHotkeyManager(default_hotkey="shift+f2")
        self.hotkey_anchor_mgr.hotkeyDisplayChanged.connect(lambda _: self.anchorHotkeyDisplayChanged.emit())
        self.hotkey_anchor_mgr.isRecordingChanged.connect(lambda _: self.anchorHotkeyRecordingChanged.emit())
        self.hotkey_anchor_mgr.hotkeyTriggered.connect(lambda: self._on_mode_hotkey_triggered("anchor"))

        self.hotkey_list_mgr = GlobalHotkeyManager(default_hotkey="shift+f3")
        self.hotkey_list_mgr.hotkeyDisplayChanged.connect(lambda _: self.listHotkeyDisplayChanged.emit())
        self.hotkey_list_mgr.isRecordingChanged.connect(lambda _: self.listHotkeyRecordingChanged.emit())
        self.hotkey_list_mgr.hotkeyTriggered.connect(lambda: self._on_mode_hotkey_triggered("list"))


        self._ocr_state = "idle"
        self._trans_state = "idle"
        self._inpaint_state = "idle"
        self._status_text = "Waiting / 等待..."
        self._status_color = "#00f3ff"

        # Load configurations / 讀取設定
        app_data_dir = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~\\AppData\\Local'), 'AITranslator')
        os.makedirs(app_data_dir, exist_ok=True)
        self._settings = QSettings(os.path.join(app_data_dir, 'config.ini'), QSettings.IniFormat)

        self._engine = self._settings.value("engine", "Google 翻譯")
        if self._engine == "Gemini AI 翻譯":
            self._engine = "Google 翻譯"
            self._settings.setValue("engine", "Google 翻譯")
            self._settings.sync()

        self._src_lang = self._settings.value("src_lang", "英文 [English]")
        self._tgt_lang = self._settings.value("tgt_lang", "繁體中文 [Traditional Chinese]")
        self._ui_lang = self._settings.value("ui_lang", "繁體中文 [Traditional Chinese]")
        self._mode = self._settings.value("display_mode", "overlay")
        self._font_color = self._settings.value("font_color", "自動 [Auto]")
        self._open_router_key = self._settings.value("open_router_key", "")
        self._gemini_key = self._settings.value("gemini_key", "")
        self._sound_enabled = self._settings.value("sound_enabled", False, type=bool)
        self._mode_sound_enabled = self._settings.value("mode_sound_enabled", False, type=bool)
        self._theme_name = self._settings.value("theme_name", "cyan")
        self._hardware = self._settings.value("hardware", "gpu")

        # 自動釋放模型計時器 (60秒)
        self._auto_unload_timer = QTimer(self)
        self._auto_unload_timer.setSingleShot(True)
        self._auto_unload_timer.timeout.connect(self._do_unload_models)
        self._is_loading_models = False
        self._ocr_ready = False
        self._translator_ready = False
        self._inpaint_ready = False

        # Ensure config.ini is created on disk
        saved_hotkey = self._settings.value("hotkey", "win+shift+d")
        self.hotkey_mgr.setHotkey(saved_hotkey)
        
        def save_hotkey(h):
            self._settings.setValue("hotkey", h)
            self._settings.sync()
            
        self.hotkey_mgr.hotkeyChanged.connect(save_hotkey)

        # Load and persist mode hotkeys / 載入並持久化模式快捷鍵
        for mode_name, mgr, default_hk in [
            ("overlay", self.hotkey_overlay_mgr, "shift+f1"),
            ("anchor", self.hotkey_anchor_mgr, "shift+f2"),
            ("list", self.hotkey_list_mgr, "shift+f3"),
        ]:
            saved = self._settings.value(f"hotkey_{mode_name}", default_hk)
            mgr.setHotkey(saved)
            key = f"hotkey_{mode_name}"
            mgr.hotkeyChanged.connect(lambda h, k=key: (self._settings.setValue(k, h), self._settings.sync()))

        self._settings.setValue("open_router_key", self._open_router_key)
        self._settings.setValue("gemini_key", self._gemini_key)
        self._settings.setValue("theme_name", self._theme_name)
        self._settings.setValue("display_mode", self._mode)
        self._settings.setValue("engine", self._engine)
        self._settings.setValue("src_lang", self._src_lang)
        self._settings.setValue("tgt_lang", self._tgt_lang)
        self._settings.setValue("ui_lang", self._ui_lang)
        self._settings.setValue("font_color", self._font_color)
        self._settings.setValue("hardware", self._hardware)
        self._settings.sync()

        # Worker thread management
        self.ipc_manager = None
        self._init_ipc_manager()

        self.jobs = {}
        self.is_busy = False

        # Connect overlay/list result signals
        self._showOverlayResult.connect(self._show_overlay_result)
        self._showListResult.connect(self._show_list_result)
        if hasattr(self, '_showAnchorResult'):
            self._showAnchorResult.connect(self._show_anchor_result)

    def _init_ipc_manager(self):
        from common.ipc_manager import IPCManager
        use_gpu = (self._hardware == "gpu")
        self.ipc_manager = IPCManager(
            ocr_kwargs={"use_gpu": use_gpu},
            translator_kwargs={"use_gpu": use_gpu},
            inpaint_kwargs={}
        )
        self.ipc_manager.ocr_ready.connect(self._on_ocr_ready)
        self.ipc_manager.translator_ready.connect(self._on_translator_ready)
        self.ipc_manager.inpaint_ready.connect(self._on_inpaint_ready)

        self.ipc_manager.ocr_result.connect(self._on_ocr_result)
        self.ipc_manager.translate_result.connect(self._on_translate_result)
        self.ipc_manager.inpaint_result.connect(self._on_inpaint_result)
        self.ipc_manager.error_occurred.connect(self._on_ipc_error)
        self.ipc_manager.progress_update.connect(self._on_progress_update)

    def _do_unload_models(self):
        """定時或手動觸發：釋放所有 worker 模型"""
        print("[主線程] 釋放模型資源...", flush=True)
        if self.ipc_manager:
            self.ipc_manager.stop_processes()
        self._init_ipc_manager()
        self._ocr_ready = False
        self._translator_ready = False
        self._inpaint_ready = False
        self._is_loading_models = False

    def _ensure_models_loaded(self, callback):
        """確保模型載入，未載入則先載入，載入完成後呼叫 callback"""
        try:
            if self._ocr_ready and self._translator_ready:
                callback()
                return
            
            if self._is_loading_models:
                # 已經在載入中，這裡可以選擇忽略或註冊多個 callback
                # 簡單起見，我們如果正在載入，就直接提示並返回
                self._set_status("模型載入中，請稍候...")
                return

            self._is_loading_models = True
            self._set_status("模型載入中，請稍候...", "#ffcc00")
            
            # 發送 load 指令
            print("[主線程] 正在發送 load 指令...", flush=True)
            if self.ipc_manager:
                self.ipc_manager.start_processes()
                self.ipc_manager.send_translator("set_open_router_key", key=self._open_router_key)
                self.ipc_manager.send_translator("set_gemini_key", key=self._gemini_key)
                self.ipc_manager.send_translator("load", kwargs={"engine": self._get_engine_code()})
                self.ipc_manager.send_inpaint("load", kwargs={})
                self.ipc_manager.send_ocr("load", kwargs={"lang": self._get_ocr_lang(self._src_lang)})
            print("[主線程] load 指令已發送。", flush=True)
                
            # 設置一個輪詢檢查是否就緒
            self._load_check_timer = QTimer(self)
            self._load_check_timer.setInterval(200)
            def check():
                if self._ocr_ready and self._translator_ready:
                    self._load_check_timer.stop()
                    self._is_loading_models = False
                    self._set_status("模型載入完成")
                    callback()
            self._load_check_timer.timeout.connect(check)
            self._load_check_timer.start()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[_ensure_models_loaded Error] {e}\n{tb}", flush=True)

    @Property(str, notify=engineChanged)
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, val):
        if self._engine != val:
            self._engine = val
            self._settings.setValue("engine", val)
            self._settings.sync()
            self.engineChanged.emit()

    @Property(str, notify=srcLangChanged)
    def srcLang(self):
        return self._src_lang

    @srcLang.setter
    def srcLang(self, val):
        if self._src_lang != val:
            self._src_lang = val
            self._settings.setValue("src_lang", val)
            self._settings.sync()
            self.srcLangChanged.emit()

    @Property(str, notify=tgtLangChanged)
    def tgtLang(self):
        return self._tgt_lang

    @tgtLang.setter
    def tgtLang(self, val):
        if self._tgt_lang != val:
            self._tgt_lang = val
            self._settings.setValue("tgt_lang", val)
            self._settings.sync()
            self.tgtLangChanged.emit()

    @Property(str, notify=uiLangChanged)
    def uiLang(self):
        return self._ui_lang

    @uiLang.setter
    def uiLang(self, val):
        if self._ui_lang != val:
            self._ui_lang = val
            self._settings.setValue("ui_lang", val)
            self._settings.sync()
            self.uiLangChanged.emit()

    @Property(str, notify=fontColorChanged)
    def fontColor(self):
        return self._font_color

    @fontColor.setter
    def fontColor(self, val):
        if self._font_color != val:
            self._font_color = val
            self._settings.setValue("font_color", val)
            self._settings.sync()
            self.fontColorChanged.emit()

    @Property(str, notify=openRouterKeyChanged)
    def openRouterKey(self):
        return self._open_router_key

    @openRouterKey.setter
    def openRouterKey(self, val):
        if self._open_router_key != val:
            self._open_router_key = val
            self._settings.setValue("open_router_key", val)
            self._settings.sync()
            self.openRouterKeyChanged.emit()
            self.ipc_manager.send_translator("set_open_router_key", key=val)

    @Property(str, notify=geminiKeyChanged)
    def geminiKey(self):
        return self._gemini_key

    @geminiKey.setter
    def geminiKey(self, val):
        if self._gemini_key != val:
            self._gemini_key = val
            self._settings.setValue("gemini_key", val)
            self._settings.sync()
            self.geminiKeyChanged.emit()
            self.ipc_manager.send_translator("set_gemini_key", key=val)

    @Property(bool, notify=soundEnabledChanged)
    def soundEnabled(self):
        return self._sound_enabled

    @soundEnabled.setter
    def soundEnabled(self, val):
        if self._sound_enabled != val:
            self._sound_enabled = val
            self._settings.setValue("sound_enabled", val)
            self._settings.sync()
            self.soundEnabledChanged.emit()

    @Property(bool, notify=modeSoundEnabledChanged)
    def modeSoundEnabled(self):
        return self._mode_sound_enabled

    @modeSoundEnabled.setter
    def modeSoundEnabled(self, val):
        if self._mode_sound_enabled != val:
            self._mode_sound_enabled = val
            self._settings.setValue("mode_sound_enabled", val)
            self._settings.sync()
            self.modeSoundEnabledChanged.emit()

    @Property(str, notify=themeNameChanged)
    def themeName(self):
        return self._theme_name

    @themeName.setter
    def themeName(self, val):
        if self._theme_name != val:
            self._theme_name = val
            self._settings.setValue("theme_name", val)
            self._settings.sync()
            self.themeNameChanged.emit()

    @Property(str, notify=modeChanged)
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, val):
        if self._mode != val:
            # 1. Close all active translation windows (overlay/list result windows)
            if hasattr(self, 'windows') and self.windows:
                for win in list(self.windows):
                    try:
                        win.close_window()
                    except Exception:
                        pass
                self.windows.clear()

            # 2. If leaving anchor mode, clear all existing anchors
            if self._mode == "anchor" and val != "anchor":
                if hasattr(self, 'anchors'):
                    for anchor in list(self.anchors):
                        try:
                            anchor.close_anchor()
                        except Exception:
                            pass
                    self.anchors.clear()
            
            self._mode = val
            self._settings.setValue("display_mode", val)
            self._settings.sync()
            self.modeChanged.emit()

            # 3. Immediately release models
            print(f"[主線程] 偵測到模式切換至 {val}，立刻釋放模型資源", flush=True)
            self._do_unload_models()

    @Property(str, notify=hardwareChanged)
    def hardware(self):
        return self._hardware

    @hardware.setter
    def hardware(self, val):
        if self._hardware != val:
            self._hardware = val
            self._settings.setValue("hardware", val)
            self._settings.sync()
            self.hardwareChanged.emit()
            # 立即非同步重新載入 worker (套用 CPU/GPU 變更)
            self._trigger_reload_workers()

    @Property(str, notify=hotkeyDisplayChanged)
    def hotkeyDisplay(self):
        return self.hotkey_mgr.hotkeyDisplay

    @Property(str, notify=tempHotkeyDisplayChanged)
    def tempHotkeyDisplay(self):
        return getattr(self.hotkey_mgr, '_temp_hotkey_display', "")

    @Property(bool, notify=isRecordingChanged)
    def isRecording(self):
        return self.hotkey_mgr.isRecording

    # Mode hotkey properties / 模式快捷鍵屬性
    @Property(str, notify=overlayHotkeyDisplayChanged)
    def overlayHotkeyDisplay(self):
        return self.hotkey_overlay_mgr.hotkeyDisplay

    @Property(str, notify=anchorHotkeyDisplayChanged)
    def anchorHotkeyDisplay(self):
        return self.hotkey_anchor_mgr.hotkeyDisplay

    @Property(str, notify=listHotkeyDisplayChanged)
    def listHotkeyDisplay(self):
        return self.hotkey_list_mgr.hotkeyDisplay

    @Property(bool, notify=overlayHotkeyRecordingChanged)
    def overlayHotkeyRecording(self):
        return self.hotkey_overlay_mgr.isRecording

    @Property(bool, notify=anchorHotkeyRecordingChanged)
    def anchorHotkeyRecording(self):
        return self.hotkey_anchor_mgr.isRecording

    @Property(bool, notify=listHotkeyRecordingChanged)
    def listHotkeyRecording(self):
        return self.hotkey_list_mgr.isRecording

    @Property(str, notify=ocrStateChanged)
    def ocrState(self):
        return self._ocr_state

    @Property(str, notify=transStateChanged)
    def transState(self):
        return self._trans_state

    @Property(str, notify=transLabelChanged)
    def transLabel(self):
        label = "本機翻譯" if self._engine == "Google 翻譯" else "雲端翻譯"
        return self.tr(label, self._ui_lang)

    @Property(str, notify=inpaintStateChanged)
    def inpaintState(self):
        return self._inpaint_state

    @Property(str, notify=statusTextChanged)
    def statusText(self):
        raw = getattr(self, '_raw_status_text', self._status_text)
        return self.tr(raw, self._ui_lang)

    @Property(str, notify=statusColorChanged)
    def statusColor(self):
        return self._status_color
    @Slot(str, object)
    def handle_anchor_update_required(self, aid, current_rgb):
        with self.anchor_lock:
            if aid in self.anchor_data:
                anchor = self.anchor_data[aid]["anchor"]
                self._spawn_anchor_update(anchor, current_rgb)

    def _update_virtual_geometry(self):
        with self.screen_lock:
            from PySide6.QtGui import QGuiApplication
            screens = QGuiApplication.screens()
            if not screens:
                self.virtual_left = 0
                self.virtual_top = 0
                self.virtual_phys_left = 0.0
                self.virtual_phys_top = 0.0
                self.screen_infos = []
                return
            
            phys_lefts = []
            phys_tops = []
            self.screen_infos = []
            
            self.virtual_left = min((s.geometry().x() for s in screens), default=0)
            self.virtual_top = min((s.geometry().y() for s in screens), default=0)
            
            for s in screens:
                g = s.geometry()
                dpr = s.devicePixelRatio()
                phys_lefts.append(g.x() * dpr)
                phys_tops.append(g.y() * dpr)
                self.screen_infos.append({
                    "x": g.x(), "y": g.y(),
                    "w": g.width(), "h": g.height(),
                    "dpr": dpr
                })
                
            self.virtual_phys_left = min(phys_lefts, default=0)
            self.virtual_phys_top = min(phys_tops, default=0)

    def get_physical_coords(self, vx, vy):
        with self.screen_lock:
            dpr = 1.0
            for s in self.screen_infos:
                if s["x"] <= vx < s["x"] + s["w"] and s["y"] <= vy < s["y"] + s["h"]:
                    dpr = s["dpr"]
                    break
            px = int(vx * dpr - getattr(self, 'virtual_phys_left', 0))
            py = int(vy * dpr - getattr(self, 'virtual_phys_top', 0))
            return px, py


    # Slots (Invoked from QML/React) / 槽函數 (自 QML/React 呼叫)
    @Slot()
    def toggleRecord(self):
        self.hotkey_mgr.toggleRecord()

    @Slot()
    def startInteractiveRecord(self):
        self.hotkey_mgr.start_interactive_record()

    @Slot()
    def saveInteractiveRecord(self):
        self.hotkey_mgr.save_interactive_record()

    @Slot()
    def cancelInteractiveRecord(self):
        self.hotkey_mgr.cancel_interactive_record()

    @Slot()
    def forceEngineUpdate(self):
        self.engineChanged.emit()

    @Slot()
    def resetHotkey(self):
        self.hotkey_mgr.resetHotkey()
        
    @Slot(str)
    def setHotkey(self, combo):
        self.hotkey_mgr.setHotkey(combo)

    # Mode hotkey handler / 模式快捷鍵處理
    def _on_mode_hotkey_triggered(self, mode_name):
        """Switch to the specified mode when mode hotkey is pressed"""
        print(f"[模式快捷鍵] 切換至 {mode_name} 模式", flush=True)
        self.mode = mode_name
        if getattr(self, '_mode_sound_enabled', False):
            try:
                import winsound
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except:
                pass

    # Mode hotkey slots / 模式快捷鍵槽函數
    @Slot()
    def startRecordOverlayHotkey(self):
        self.hotkey_overlay_mgr.start_interactive_record()

    @Slot()
    def startRecordAnchorHotkey(self):
        self.hotkey_anchor_mgr.start_interactive_record()

    @Slot()
    def startRecordListHotkey(self):
        self.hotkey_list_mgr.start_interactive_record()

    @Slot()
    def cancelRecordOverlayHotkey(self):
        self.hotkey_overlay_mgr.cancel_interactive_record()

    @Slot()
    def cancelRecordAnchorHotkey(self):
        self.hotkey_anchor_mgr.cancel_interactive_record()

    @Slot()
    def cancelRecordListHotkey(self):
        self.hotkey_list_mgr.cancel_interactive_record()

    @Slot()
    def resetOverlayHotkey(self):
        self.hotkey_overlay_mgr.resetHotkey()

    @Slot()
    def resetAnchorHotkey(self):
        self.hotkey_anchor_mgr.resetHotkey()

    @Slot()
    def resetListHotkey(self):
        self.hotkey_list_mgr.resetHotkey()

    @Slot(str)
    def setOverlayHotkey(self, combo):
        self.hotkey_overlay_mgr.setHotkey(combo)

    @Slot(str)
    def setAnchorHotkey(self, combo):
        self.hotkey_anchor_mgr.setHotkey(combo)

    @Slot(str)
    def setListHotkey(self, combo):
        self.hotkey_list_mgr.setHotkey(combo)

    @Slot(str)
    def copyToClipboard(self, text):
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            print(f"[Backend] Copied to clipboard: {text}", flush=True)

    @Slot(str, result=str)
    def getEngineCode(self, display_name):
        name_lower = display_name.lower()
        if "google" in name_lower: return "google"
        if "gemini" in name_lower: return "gemini"
        if "qwen3" in name_lower: return "qwen3"
        
        is_sc = "簡" in display_name or "sc" in name_lower
        is_free = "free" in name_lower
        is_instruct = "instruct" in name_lower
        
        if is_free: return "qwen_free_sc" if is_sc else "qwen_free_tc"
        if is_instruct: return "qwen_instruct_sc" if is_sc else "qwen_instruct_tc"
        
        if "qwen" in name_lower: return "qwen_sc" if is_sc else "qwen_tc"
        return "google"

    # Status updates (Thread-safe) / 狀態更新 (線程安全)

    def _set_status(self, text, color="#00f3ff"):
        self._raw_status_text = text
        self._status_text = text
        self._status_color = color
        self.statusTextChanged.emit()
        self.statusColorChanged.emit()

    def _set_worker_state(self, key, state_str):
        if key == "ocr":
            self._ocr_state = state_str
            self.ocrStateChanged.emit()
        elif key == "translator":
            self._trans_state = state_str
            self.transStateChanged.emit()
        elif key == "inpaint":
            self._inpaint_state = state_str
            self.inpaintStateChanged.emit()

    def _on_worker_change(self):
        """Watchdog callback / Watchdog 回調"""
        self._workerStateChangedMain.emit()

    @Slot()
    def _update_worker_states_on_main(self):
        from common.watchdog import WorkerState
        for key in ["ocr", "translator", "inpaint"]:
            info = self._wm.get_state(key)
            self._set_worker_state(key, info.state.value)
        # Update UI status / 更新介面狀態
        self._set_status(self._wm.get_status_text(), self._wm.get_status_color())

    def _trigger_reload_workers(self):
        from common.watchdog import WorkerState
        for key in ["ocr", "translator", "inpaint"]:
            self._wm.set_state(key, WorkerState.LOADING, "模型載入中...")
            
        if not hasattr(self, '_reload_timer'):
            self._reload_timer = QTimer(self)
            self._reload_timer.setSingleShot(True)
            self._reload_timer.timeout.connect(self._do_reload_workers)
        self._reload_timer.start(500)

    def _do_reload_workers(self):
        if not hasattr(self, '_threads'): self._threads = []
        self._threads = [t for t in self._threads if t.isRunning()]
        worker = GenericWorkerThread(self._reload_workers)
        self._threads.append(worker)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    # Hotkeys / 快捷鍵管理

    @Slot()
    def _on_hotkey_failed(self):
        from common.hotkey_manager import _log
        _log("[_on_hotkey_failed] Hotkey registration failed!")
        self._set_status("快捷鍵註冊失敗 (可能被佔用)", "#ff3366")

    def check_hotkey(self):
        from common.hotkey_manager import _log
        _log(f"[check_hotkey] invoked! is_busy={self.is_busy}, isRecording={self.hotkey_mgr.isRecording}")
        if not self.is_busy and not self.hotkey_mgr.isRecording:
            # 關閉任何已開啟的出圖視窗，避免置頂遮擋與滑鼠焦點衝突
            if hasattr(self, 'windows') and self.windows:
                for win in list(self.windows):
                    try:
                        win.close()
                    except Exception as e:
                        _log(f"[check_hotkey] 關閉舊視窗失敗: {e}")

            # 停止任何運行中的 unload timer
            if hasattr(self, '_auto_unload_timer') and self._auto_unload_timer.isActive():
                self._auto_unload_timer.stop()
            
            if getattr(self, '_sound_enabled', False):
                try:
                    import winsound
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except:
                    pass
            
            _log("[check_hotkey] ensuring models loaded...")
            self._ensure_models_loaded(self._start_snip)

    def _on_busy_timeout(self):
        if self.is_busy:
            print("[主線程] 警告：檢測到翻譯/框選任務逾時 (15秒) 未完成，強制執行 _reset_all() 重置狀態", flush=True)
            self._reset_all()

    # Screenshot Area Selection (PySide6) / 螢幕截圖區域框選 (PySide6)

    def _start_snip(self):
        from common.hotkey_manager import _log
        try:
            self.is_busy = True
            self._set_status("背景處理中...", "#f9e2af")
            
            # 啟動 15 秒安全防護定時器，防範任何非同步工作流卡死導致 is_busy 被永久鎖定
            if hasattr(self, '_busy_watchdog_timer'):
                try: self._busy_watchdog_timer.stop()
                except: pass
            from PySide6.QtCore import QTimer
            self._busy_watchdog_timer = QTimer(self)
            self._busy_watchdog_timer.setSingleShot(True)
            self._busy_watchdog_timer.timeout.connect(self._on_busy_timeout)
            self._busy_watchdog_timer.start(15000) # 15 秒
            
            _log("[_start_snip] creating SnippingWidget...")

            self.snipping_widget = SnippingWidget(self)

            def on_snip_completed(l, t, r, b, snip_img):
                _log("[_start_snip] on_snip_completed")
                if self._mode == "anchor":
                    try:
                        bubble = AnchorBubbleWidget(l, t, r - l, b - t, self)
                        self.anchors.append(bubble)
                        bubble.show()
                    except Exception as e:
                        import traceback
                        with open("D:/chrom/screenshot/AITranslator/crash_log.txt", "w", encoding="utf-8") as f:
                            f.write(f"Build failed: {e}\n")
                            f.write(traceback.format_exc())
                        _log(f"[Selection] Build failed: {e}")
                    self._reset_all()
                else:
                    self._bg_process(l, t, r, b, snip_img)

            def on_snip_cancelled():
                _log("[_start_snip] on_snip_cancelled")
                self._reset_all()

            self.snipping_widget.snip_completed.connect(on_snip_completed)
            self.snipping_widget.snip_cancelled.connect(on_snip_cancelled)
            _log("[_start_snip] calling snipping_widget.show()...")
            self.snipping_widget.show()
            _log("[_start_snip] snipping_widget shown")
        except Exception as e:
            import traceback
            _log(f"[_start_snip] CRITICAL EXCEPTION: {e}\n{traceback.format_exc()}")
            self.is_busy = False

    # OCR Correction / OCR 修正

    def _fix_ocr(self, text: str) -> str:
        text = re.sub(r'11[38]', 'May', text)
        text = re.sub(r'[MN]lay', 'May', text)
        text = re.sub(r'\bl\b', 'I', text)
        return text

    # Auxiliary helpers / 輔助工具方法

    def _get_font_color_tuple(self):
        mapping = {
            "白色": (255, 255, 255),
            "White": (255, 255, 255),
            "黑色": (0, 0, 0),
            "Black": (0, 0, 0),
            "紅色": (255, 51, 102),
            "Red": (255, 51, 102),
            "黃色": (255, 215, 0),
            "Yellow": (255, 215, 0),
            "綠色": (166, 227, 161),
            "Green": (166, 227, 161),
            "藍色": (137, 180, 250),
            "Blue": (137, 180, 250)
        }
        for k, v in mapping.items():
            if k in self._font_color:
                return v
        return None

    def _bg_process(self, l, t, r, b, frozen_img=None):
        """Background processing: OCR, Translation + Inpainting (parallel execution) and rendering / 背景處理：OCR、翻譯 + 嵌字 (並行執行與渲染)"""
        try:
            import uuid
            job_id = str(uuid.uuid4())
            with self.jobs_lock:
                self.jobs[job_id] = {
                    "l": l, "t": t, "r": r, "b": b,
                    "pil": frozen_img,
                    "img_np": None,
                    "start_time": time.time(),
                    "mode": self._mode,
                    "blocks": None,
                    "raw_texts": None,
                    "translated": None,
                    "inpainted": None,
                    "trans_done": False,
                    "inpaint_done": False,
                    "src_display": self._src_lang,
                    "tgt_display": self._tgt_lang
                }
            
            self._set_status("OCR 進行中", "#89b4fa")

            if frozen_img:
                pil = frozen_img
            else:
                from PIL import ImageGrab
                pil = ImageGrab.grab(bbox=(l, t, r, b), all_screens=True)
                with self.jobs_lock:
                    if job_id in self.jobs:
                        self.jobs[job_id]["pil"] = pil
                
            # Save temp screenshot to satisfy requirements
            try:
                import os
                temp_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AITranslator')
                os.makedirs(temp_dir, exist_ok=True)
                pil.save(os.path.join(temp_dir, 'temp_screenshot.png'))
            except Exception as e:
                print(f"[Warning] Failed to save screenshot: {e}")

            img_np = np.array(pil.convert("RGB"))
            with self.jobs_lock:
                if job_id in self.jobs:
                    self.jobs[job_id]["img_np"] = img_np

            if not self.ipc_manager:
                self._set_status("IPCManager initialization failed", "#ff3366")
                self._reset_all()
                return

            self.ipc_manager.send_ocr("recognize", job_id=job_id, img=img_np, lang_display=self._src_lang)
            
        except Exception as e:
            print(f"[Error] {e}")
            import traceback; traceback.print_exc()
            self._reset_all()

    @Slot(str, object)
    def _on_ocr_result(self, job_id, ocr_result):
        with self.jobs_lock:
            if job_id not in self.jobs: return
            job = self.jobs[job_id]
        try:
            if job.get("is_anchor"):
                anchor = job["anchor"]
                import shiboken6
                if not shiboken6.isValid(anchor):
                    with self.jobs_lock:
                        self.jobs.pop(job_id, None)
                    return
                with self.anchor_lock:
                    adata = self.anchor_data.get(anchor.anchor_id, {})
                    is_interacting = adata.get('is_interacting', False)
                    last_ocr_gray = adata.get('last_ocr_gray', None)
                if last_ocr_gray is None:
                    anchor.is_processing = False
                    self.update_anchor_config(anchor.anchor_id, is_processing=False)
                    with self.jobs_lock:
                        self.jobs.pop(job_id, None)
                    return
                    
                blocks = getattr(ocr_result, 'blocks', [])
                if not blocks:
                    from PySide6.QtGui import QImage
                    anchor.update_image_signal.emit(QImage())
                    anchor.just_updated = True
                    anchor.is_processing = False
                    self.update_anchor_config(anchor.anchor_id, is_processing=False)
                    with self.jobs_lock:
                        self.jobs.pop(job_id, None)
                    return
                
                from common.render import merge_rows
                blocks = merge_rows(ocr_result.blocks)
                raw_texts = [self._fix_ocr(b.text) for b in blocks]
                
                if not raw_texts:
                    from PySide6.QtGui import QImage
                    anchor.update_image_signal.emit(QImage())
                    anchor.just_updated = True
                    anchor.is_processing = False
                    self.update_anchor_config(anchor.anchor_id, is_processing=False)
                    with self.jobs_lock:
                        self.jobs.pop(job_id, None)
                    return
                    
                with self.jobs_lock:
                    if job_id in self.jobs:
                        job["blocks"] = blocks
                        job["raw_texts"] = raw_texts
                self.ipc_manager.send_translator("translate_batch", job_id=job_id, texts=raw_texts, src_display=job["src_display"], tgt_display=job["tgt_display"])
                return

            if not getattr(ocr_result, 'blocks', []):
                self._set_status("等待中", "#fab387")
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1500, self._reset_all)
                with self.jobs_lock:
                    self.jobs.pop(job_id, None)
                return

            from common.render import merge_rows
            blocks = merge_rows(ocr_result.blocks)
            raw_texts = [self._fix_ocr(blk.text) for blk in blocks]

            with self.jobs_lock:
                if job_id in self.jobs:
                    job["blocks"] = blocks
                    job["raw_texts"] = raw_texts
            
            self._set_status("翻譯 + 繪圖中", "#89b4fa")
            
            self.ipc_manager.send_translator("translate_batch", job_id=job_id, texts=raw_texts, src_display=job["src_display"], tgt_display=job["tgt_display"])
            
            if job.get("mode") == "overlay":
                self.ipc_manager.send_inpaint("inpaint", job_id=job_id, img=job["img_np"], blocks=blocks)
            else:
                with self.jobs_lock:
                    if job_id in self.jobs:
                        job["inpaint_done"] = True
                self._check_job_complete(job_id)

        except Exception as e:
            print(f"[OCR Callback Error] {e}")
            import traceback; traceback.print_exc()
            self._reset_all()

    @Slot(str, object)
    def _on_translate_result(self, job_id, trans_result):
        with self.jobs_lock:
            if job_id not in self.jobs: return
            job = self.jobs[job_id]
        
        try:
            if job.get("is_anchor"):
                anchor = job["anchor"]
                import shiboken6
                if not shiboken6.isValid(anchor):
                    with self.jobs_lock:
                        self.jobs.pop(job_id, None)
                    return
                with self.anchor_lock:
                    adata = self.anchor_data.get(anchor.anchor_id, {})
                    is_interacting = adata.get('is_interacting', False)
                    last_ocr_gray = adata.get('last_ocr_gray', None)
                if last_ocr_gray is None:
                    anchor.is_processing = False
                    self.update_anchor_config(anchor.anchor_id, is_processing=False)
                    with self.jobs_lock:
                        self.jobs.pop(job_id, None)
                    return
                    
                translated = trans_result if trans_result else job["raw_texts"]
                if translated:
                    from common.render import render_transparent_overlay
                    c_color = anchor.get_font_color_tuple()
                    pw = job["img_np"].shape[1]
                    ph = job["img_np"].shape[0]
                    
                    qimg = render_transparent_overlay(pw, ph, job["img_np"], job["blocks"], translated, c_color)
                    dpr = getattr(anchor, 'dpr', 1.0)
                    qimg.setDevicePixelRatio(dpr)
                    

                        
                    anchor.update_image_signal.emit(qimg)
                else:
                    from PySide6.QtGui import QImage
                    anchor.update_image_signal.emit(QImage())
                
                anchor.just_updated = True
                anchor.is_processing = False
                self.update_anchor_config(anchor.anchor_id, is_processing=False)
                with self.jobs_lock:
                    self.jobs.pop(job_id, None)
                return

            with self.jobs_lock:
                if job_id in self.jobs:
                    job["translated"] = trans_result if trans_result else job["raw_texts"]
                    job["trans_done"] = True
            self._check_job_complete(job_id)
        except Exception as e:
            print(f"[Translation Callback Error] {e}")
            import traceback; traceback.print_exc()
            self._reset_all()

    @Slot(str, object)
    def _on_inpaint_result(self, job_id, inpaint_result):
        with self.jobs_lock:
            if job_id not in self.jobs: return
            job = self.jobs[job_id]
        try:
            with self.jobs_lock:
                if job_id in self.jobs:
                    job["inpainted"] = inpaint_result
                    job["inpaint_done"] = True
            self._check_job_complete(job_id)
        except Exception as e:
            print(f"[Inpaint Callback Error] {e}")
            import traceback; traceback.print_exc()
            self._reset_all()

    def _check_job_complete(self, job_id):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
        if not job: return
        if job.get("trans_done") and job.get("inpaint_done"):
            self._finish_job(job_id)

    def _finish_job(self, job_id):
        try:
            with self.jobs_lock:
                if job_id not in self.jobs: return
                job = self.jobs.pop(job_id)
            blocks = job["blocks"]
            translated = job["translated"]
            inpainted = job["inpainted"]
            pil = job["pil"]
            img_np = job["img_np"]
            mode = job.get("mode")
            
            if inpainted is not None:
                from PIL import Image
                inpainted = Image.fromarray(inpainted)
            
            from common.render import set_render_lang
            set_render_lang(job["tgt_display"])

            if mode == "overlay":
                from common.render import smart_render
                c_color = self._get_font_color_tuple()
                qim = smart_render(pil, img_np, blocks, translated, inpainted, c_color)
                self._showOverlayResult.emit(qim, job["l"], job["t"], job["r"], job["b"])
            else:
                from common.render import extract_colors
                colors = []
                for blk in blocks:
                    _, fg = extract_colors(img_np, blk.box)
                    colors.append(f"#{fg[0]:02X}{fg[1]:02X}{fg[2]:02X}")
                self._showListResult.emit(translated, colors, job["l"], job["t"], job["r"], job["b"])

            self._set_status("翻譯完成", "#a6e3a1")
            # 任務完成，啟動閒置自動釋放計時器 (60秒)
            if hasattr(self, '_auto_unload_timer'):
                self._auto_unload_timer.start(60000)
                print("[主線程] 啟動 60 秒閒置自動釋放計時器", flush=True)
        except Exception as e:
            print(f"[翻譯錯誤] {e}")
            import traceback; traceback.print_exc()
        finally:
            self._reset_all()

    @Slot(str, str)
    def _on_ipc_error(self, worker, error):
        print(f"[IPC Error] {worker}: {error}")
        self._set_status(f"Error: {worker}", "#ff3366")
        from common.watchdog import WorkerState
        wid = "ocr" if "OCR" in worker else "translator" if "Trans" in worker else "inpaint"
        self._wm.set_state(wid, WorkerState.ERROR, error=error)
        self._reset_all()
        # Automatically stop current crashed processes and recreate the manager to allow clean recovery on next snip
        try:
            if self.ipc_manager:
                self.ipc_manager.stop_processes()
        except:
            pass
        self._init_ipc_manager()

    def _spawn_anchor_update(self, anchor, img_np):
        """Background active update: when the screen changes, automatically recognize new regions and translate / 背景主動更新：當畫面變化時自動辨識新區域並翻譯"""
        if not self.ipc_manager:
            return
            
        import uuid
        job_id = f"anchor_{id(anchor)}_{uuid.uuid4()}"
        with self.anchor_lock:
            if anchor.anchor_id in self.anchor_data:
                self.anchor_data[anchor.anchor_id]["processing_start_time"] = time.time()
                
        with self.jobs_lock:
            self.jobs[job_id] = {
                "is_anchor": True,
                "anchor": anchor,
                "img_np": img_np,
                "src_display": self._src_lang,
                "tgt_display": self._tgt_lang
            }
        self.ipc_manager.send_ocr("recognize", job_id=job_id, img=img_np, lang_display=self._src_lang)

    # Result Windows (Signal slots on the main thread) / 結果視窗 (在主線程執行的信號槽)

    @Slot(QImage, int, int, int, int)
    def _show_overlay_result(self, qim, l, t, r, b):
        """Show overlay mode result window (called by background thread signal) / 顯示覆蓋模式結果視窗 (由背景執行緒信號呼叫)"""
        try:
            from PySide6.QtGui import QGuiApplication
            from PySide6.QtCore import QPoint
            screen = QGuiApplication.screenAt(QPoint(l, t))
            if not screen:
                screen = QGuiApplication.primaryScreen()
            dpr = screen.devicePixelRatio()
            qim.setDevicePixelRatio(dpr)
            
            win = ResultWindow(qim, l, t, r, b, self)
            self.windows.append(win)
            win.show()
            win.raise_()
            win.activateWindow()
        except Exception as e:
            print(f"[Show Overlay Result] Failed: {e}")

    @Slot(object, object, int, int, int, int)
    def _show_list_result(self, translated, colors, l, t, r, b):
        """Show list mode result window (called by background thread signal) / 顯示列表模式結果視窗 (由背景執行緒信號呼叫)"""
        try:
            win = ListResultWindow(translated, colors, l, t, r, b, self)
            self.windows.append(win)
            win.show()
            win.raise_()
            win.activateWindow()
        except Exception as e:
            print(f"[Show List Result] Failed: {e}")

    def _reset_all(self):
        if hasattr(self, '_busy_watchdog_timer'):
            try: self._busy_watchdog_timer.stop()
            except: pass
        if hasattr(self, "jobs"):
            with self.jobs_lock:
                jobs_list = list(self.jobs.items())
            for job_id, job in jobs_list:
                if job.get("is_anchor"):
                    anchor = job["anchor"]
                    import shiboken6
                    if shiboken6.isValid(anchor):
                        anchor.is_processing = False
                        self.update_anchor_config(anchor.anchor_id, is_processing=False)
            with self.jobs_lock:
                self.jobs.clear()
        self.is_busy = False
        self.trigger_snip = False
        self._set_status("已複製到剪貼簿", "#a6e3a1")

    # Helpers / 輔助函數

    def _get_engine_code(self):
        return self.getEngineCode(self._engine)

    def _get_ocr_lang(self, display):
        from common.protocol import get_ocr_lang
        return get_ocr_lang(display)

    @Slot(bool)
    def _on_ocr_ready(self, r):
        from common.watchdog import WorkerState
        self._ocr_ready = r
        self._wm.set_state("ocr", WorkerState.READY if r else WorkerState.ERROR)

    @Slot(bool)
    def _on_translator_ready(self, r):
        from common.watchdog import WorkerState
        self._translator_ready = r
        self._wm.set_state("translator", WorkerState.READY if r else WorkerState.ERROR)

    @Slot(bool)
    def _on_inpaint_ready(self, r):
        from common.watchdog import WorkerState
        self._inpaint_ready = r
        self._wm.set_state("inpaint", WorkerState.READY if r else WorkerState.ERROR)

    @Slot(str, str)
    def _on_progress_update(self, worker, msg):
        from common.watchdog import WorkerState
        wid = "ocr" if "OCR" in worker else "translator" if "Trans" in worker else "inpaint"
        self._wm.set_state(wid, WorkerState.LOADING, msg)

    def start_bg_loading(self):
        """Called by main() to start loading workers in the background / 由 main() 呼叫以在背景啟動工作進程"""
        if not hasattr(self, '_threads'): self._threads = []
        self._threads = [t for t in self._threads if t.isRunning()]
        worker = GenericWorkerThread(self._bg_startup)
        self._threads.append(worker)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _bg_startup(self):
        from common.watchdog import WorkerState
        t0 = time.time()

        # 1. Hotkeys (already registered in main() via RegisterHotKey, skipped here) / 1. 快捷鍵 (已在主線程 main() 中註冊，此處略過)
        self._set_status("快捷鍵已綁定")
        print(f"startup begin: {time.time()-t0:.2f}s")
        self.ipc_manager.start_processes()
        
        self.ipc_manager.send_translator("set_open_router_key", key=self._open_router_key)
        # self.ipc_manager.send_translator("load", kwargs={"engine": self._get_engine_code()})
        # self.ipc_manager.send_inpaint("load", kwargs={})
        # self.ipc_manager.send_ocr("load", kwargs={"lang": self._get_ocr_lang(self._src_lang)})

        total = time.time() - t0
        print(f"Background startup completed in {total:.2f}s")
        self._set_status("已複製到剪貼簿", "#a6e3a1")

    def _reload_workers(self):
        from common.watchdog import WorkerState
        use_gpu = (self._hardware == "gpu")

        for wid in ["ocr", "translator", "inpaint"]:
            self._wm.set_state(wid, WorkerState.LOADING, "正在載入中")

        if self.ipc_manager:
            self.ipc_manager.send_ocr("set_gpu", use_gpu=use_gpu)
            self.ipc_manager.send_translator("set_gpu", use_gpu=use_gpu)
            self.ipc_manager.send_translator("set_open_router_key", key=self._open_router_key)
            self.ipc_manager.send_translator("load", kwargs={"engine": self._get_engine_code()})
            self.ipc_manager.send_inpaint("load", kwargs={})
            self.ipc_manager.send_ocr("load", kwargs={"lang": self._get_ocr_lang(self._src_lang)})




# Main Entry Point / 程式主入口

def main():
    print(">>> AI 翻譯 v1.0 (PySide6 + QML)")

    app = QApplication(sys.argv)
    
    # Disable Qt application network proxy / 停用 Qt 應用程式網路代理，避免本地環回地址走代理伺服器
    from PySide6.QtNetwork import QNetworkProxy
    QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.NoProxy))
    
    # Prevent multiple instances
    from PySide6.QtCore import QSharedMemory
    app._shared_memory = QSharedMemory("AITranslator_SingleInstance_v2")
    if not app._shared_memory.create(1):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(None, "AI Translator", "程式已經在執行中了！請查看系統右下角系統匣。")
        sys.exit(0)

    # Setup application icon / 設定應用程式圖示
    base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    icon_path = Path(base_dir) / "EXEimage.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Initialize backend / 建立後端實例
    backend = AppBackend()

    import subprocess
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineProfile
    from PySide6.QtWidgets import QMainWindow
    from PySide6.QtCore import QUrl, QFile, QTextStream

    # Startup React UI local web server (AITranslator-UI) / 啟動 React 網頁本地伺服器 (AITranslator-UI)
    base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    ui_dir = Path(base_dir) / "ui_dist"

    import http.server
    import socketserver
    import threading

    class SPAHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.path = '/index.html'
            path = self.translate_path(self.path)
            if not os.path.exists(path):
                self.path = '/index.html'
            try:
                super().do_GET()
            except Exception:
                pass

        def do_POST(self):
            if self.path == '/api/translate':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                import json
                try:
                    payload = json.loads(post_data.decode('utf-8'))
                except Exception:
                    payload = {}
                
                text = payload.get('text', '')
                source_lang_raw = payload.get('sourceLang', 'en')
                target_lang_raw = payload.get('targetLang', 'zh-TW')
                
                def map_lang(lang_str):
                    if not lang_str:
                        return "auto"
                    from common.protocol import LANGUAGES
                    for key, entry in LANGUAGES.items():
                        if lang_str == key or lang_str == entry.display:
                            return entry.google_code
                    lang_lower = lang_str.lower()
                    if "繁中" in lang_str or "traditional" in lang_lower or lang_lower in ("zh-tw", "zho-hant", "zho_hant"):
                        return "zh-TW"
                    if "簡中" in lang_str or "简体" in lang_str or "simplified" in lang_lower or lang_lower in ("zh-cn", "zho-hans", "zho_hans"):
                        return "zh-CN"
                    if "英文" in lang_str or "english" in lang_lower or lang_lower == "en":
                        return "en"
                    if "日文" in lang_str or "japanese" in lang_lower or lang_lower == "ja":
                        return "ja"
                    if "韓文" in lang_str or "korean" in lang_lower or lang_lower == "ko":
                        return "ko"
                    for key, entry in LANGUAGES.items():
                        if lang_lower == entry.google_code.lower() or lang_lower == entry.paddle_ocr.lower():
                            return entry.google_code
                    return lang_str

                sl = map_lang(source_lang_raw)
                tl = map_lang(target_lang_raw)
                
                # Force Google Translate for live translator in UI / 對於 UI 實時翻譯測試台，強制固定使用 Google 翻譯
                import urllib.request
                import urllib.parse
                
                url = 'https://translate.googleapis.com/translate_a/single'
                params = {
                    'client': 'gtx',
                    'sl': sl,
                    'tl': tl,
                    'dt': 't',
                    'q': text
                }
                
                try:
                    encoded_params = urllib.parse.urlencode(params)
                    full_url = f"{url}?{encoded_params}"
                    req = urllib.request.Request(
                        full_url,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        res_data = response.read().decode('utf-8')
                        data = json.loads(res_data)
                        translated = ''.join(seg[0] for seg in data[0] if seg[0]) if data[0] else text
                except Exception:
                    translated = text
                
                response_payload = json.dumps({'translated': translated})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_payload)))
                self.end_headers()
                self.wfile.write(response_payload.encode('utf-8'))
            else:
                self.send_error(404, "File not found")

    server_ready = threading.Event()
    actual_port = [3000]

    def run_local_server(directory):
        class Handler(SPAHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)
        class ReuseTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
        try:
            with ReuseTCPServer(("127.0.0.1", 0), Handler) as httpd:
                actual_port[0] = httpd.server_address[1]
                print(f"[Server] HTTP server bound successfully to 127.0.0.1:{actual_port[0]}", flush=True)
                server_ready.set()
                httpd.serve_forever()
        except Exception as e:
            print(f"[Server] Failed to start HTTP server: {e}", flush=True)
            actual_port[0] = 3000
            server_ready.set()

    server_thread = threading.Thread(target=run_local_server, args=(str(ui_dir),), daemon=True)
    server_thread.start()

    main_win = QMainWindow()
    main_win.resize(1200, 800)
    def update_main_win_title():
        lang = getattr(backend, "uiLang", "繁體中文")
        title = backend.get_translation("AI 翻譯", lang)
        main_win.setWindowTitle(title)

    backend.uiLangChanged.connect(update_main_win_title)
    update_main_win_title()
    if icon_path.exists():
        main_win.setWindowIcon(QIcon(str(icon_path)))
        
    # Set persistent storage path for WebEngine (for localStorage settings) / 設定 WebEngine 永續儲存路徑 (用於保存 localStorage 設定)
    profile = QWebEngineProfile.defaultProfile()
    if "LOCALAPPDATA" in os.environ:
        storage_path = str(Path(os.environ["LOCALAPPDATA"]) / "AITranslator" / "webengine")
    else:
        storage_path = str(Path(os.path.expanduser("~")) / ".aitranslator_cache" / "webengine")
    profile.setPersistentStoragePath(storage_path)
    profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
    profile.clearHttpCache()  # Force clear cache to load the latest React UI

    view = QWebEngineView()
    
    class WebEnginePage(view.page().__class__):
        def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
            msg = f"[JS] {message} (line {lineNumber})"
            print(msg)

    page = WebEnginePage(view)
    view.setPage(page)
    view._page_ref = page # Prevent garbage collection / 防止被垃圾回收
    
    channel = QWebChannel()
    channel.registerObject("backend", backend)
    view.page().setWebChannel(channel)
    view._channel_ref = channel # Prevent garbage collection / 防止被垃圾回收

    # 注入 qwebchannel.js
    qwebchannel_js = QFile(":/qtwebchannel/qwebchannel.js")
    if qwebchannel_js.open(QFile.ReadOnly):
        script = QWebEngineScript()
        code = QTextStream(qwebchannel_js).readAll()
        code += """
        window.backend_ready = false;
        new QWebChannel(qt.webChannelTransport, function(channel) {
            window.backend = channel.objects.backend;
            window.backend_ready = true;
            window.dispatchEvent(new Event('backendReady'));
        });
        """
        script.setSourceCode(code)
        script.setName("qwebchannel.js")
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        script.setRunsOnSubFrames(True)
        view.page().profile().scripts().insert(script)
        view.page().profile()._qwebchannel_script = script # Prevent garbage collection / 防止被垃圾回收
        qwebchannel_js.close()

    server_ready.wait(timeout=3.0)
    server_port = actual_port[0]
    time.sleep(0.05)  # Safe delay to ensure serve_forever loop is ready

    html_file = Path(ui_dir) / "index.html"
    if html_file.exists():
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            view.setHtml(html_content, QUrl(f"http://127.0.0.1:{server_port}/"))
        except Exception:
            view.load(QUrl(f"http://127.0.0.1:{server_port}"))
    else:
        view.load(QUrl(f"http://127.0.0.1:{server_port}"))
    
    main_win.setCentralWidget(view)
    main_win._view_ref = view # Prevent garbage collection / 防止被垃圾回收
    app._main_win_ref = main_win # Prevent garbage collection / 防止被垃圾回收
    main_win.show()

    # Load worker processes in the background / 於背景載入工作進程
    backend.start_bg_loading()

    # Set main window Win32 HWND / 設定主視窗 Win32 視窗控制碼 (HWND)
    backend.hwnd = int(main_win.winId())

    # Hotkey registration is handled inside GlobalHotkeyManager / 快捷鍵註冊由 GlobalHotkeyManager 內部處理


    # Setup System Tray to prevent exit when main window closes / 設定系統匣以防主視窗關閉時結束
    from PySide6.QtWidgets import QSystemTrayIcon, QMenu
    from PySide6.QtGui import QAction
    
    
    tray_icon = QSystemTrayIcon(QIcon(str(icon_path)), app)
    tray_menu = QMenu()
    
    show_action = QAction("顯示主視窗 (Show Main Window)", app)
    show_action.triggered.connect(main_win.show)
    tray_menu.addAction(show_action)
    
    quit_action = tray_menu.addAction("退出")
    
    def force_quit():
        backend.cleanup()
        if hasattr(app, '_shared_memory'):
            app._shared_memory.detach()
        app.quit()
        import os
        os._exit(0)
        
    quit_action.triggered.connect(force_quit)
    tray_menu.addAction(quit_action)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.DoubleClick:
            main_win.show()
            main_win.activateWindow()
    tray_icon.activated.connect(on_tray_activated)
    
    # Store reference so it's not garbage collected
    main_win._tray_icon = tray_icon

    app.aboutToQuit.connect(force_quit)


    sys.exit(app.exec())


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()


