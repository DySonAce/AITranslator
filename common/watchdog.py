"""
common/watchdog.py ─ Worker 狀態管理
=====================================
追蹤各 Worker 的載入狀態，提供 UI 回調。
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional
import threading


class WorkerState(Enum):
    IDLE     = "idle"       # 尚未啟動
    LOADING  = "loading"    # 載入中
    READY    = "ready"      # 就緒
    ERROR    = "error"      # 錯誤
    BUSY     = "busy"       # 處理中


@dataclass
class WorkerInfo:
    name: str
    state: WorkerState = WorkerState.IDLE
    message: str = ""
    error: Optional[str] = None


class WorkerManager:
    """管理所有 Worker 的狀態"""

    def __init__(self):
        self._workers: dict[str, WorkerInfo] = {
            "ocr":        WorkerInfo("OCR"),
            "translator": WorkerInfo("翻譯"),
            "inpaint":    WorkerInfo("修復"),
        }
        self._lock = threading.Lock()
        self._on_change: Optional[Callable] = None

    def set_callback(self, callback: Callable):
        """設定狀態變更回調（UI 更新用）"""
        self._on_change = callback

    def set_state(self, worker_id: str, state: WorkerState,
                  message: str = "", error: str = None):
        with self._lock:
            if worker_id in self._workers:
                w = self._workers[worker_id]
                w.state = state
                w.message = message
                w.error = error
        if self._on_change:
            try:
                self._on_change()
            except Exception:
                pass

    def get_state(self, worker_id: str) -> WorkerInfo:
        with self._lock:
            return self._workers.get(worker_id, WorkerInfo("unknown"))

    def get_all(self) -> dict[str, WorkerInfo]:
        with self._lock:
            return dict(self._workers)

    def all_ready(self) -> bool:
        with self._lock:
            return all(w.state == WorkerState.READY
                       for w in self._workers.values())

    def any_loading(self) -> bool:
        with self._lock:
            return any(w.state == WorkerState.LOADING
                       for w in self._workers.values())

    def get_status_text(self) -> str:
        """取得人類可讀的整體狀態"""
        with self._lock:
            loading = [w.name for w in self._workers.values()
                       if w.state == WorkerState.LOADING]
            errors  = [w.name for w in self._workers.values()
                       if w.state == WorkerState.ERROR]

        if errors:
            return f"⚠ {', '.join(errors)} 載入失敗"
        if loading:
            return f"載入中：{', '.join(loading)}…"
        if self.all_ready():
            return "就緒 ✓  按快捷鍵開始"
        return "啟動中…"

    def get_status_color(self) -> str:
        with self._lock:
            has_error = any(w.state == WorkerState.ERROR
                           for w in self._workers.values())
        if has_error:
            return "#f38ba8"
        if self.all_ready():
            return "#a6e3a1"
        return "#f9e2af"
