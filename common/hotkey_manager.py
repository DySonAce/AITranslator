import keyboard
from PySide6.QtCore import QObject, Signal, Slot
import logging

logger = logging.getLogger("GlobalHotkeyManager")

def _log(msg):
    logger.debug(msg)

class GlobalHotkeyManager(QObject):
    hotkeyTriggered = Signal()
    hotkeyRegisterFailed = Signal()
    isRecordingChanged = Signal(bool)
    hotkeyDisplayChanged = Signal(str)
    hotkeyChanged = Signal(str)
    tempHotkeyDisplayChanged = Signal(str)

    def __init__(self, default_hotkey="win+shift+d"):
        super().__init__()
        self._default_hotkey = default_hotkey
        self._hotkey = default_hotkey
        self._hotkey_display = self._fmt(self._hotkey)
        self._is_recording = False
        self._rec_keys = set()
        self._hook_callback_ref = None
        self._hotkey_handle = None

    @property
    def isRecording(self):
        return self._is_recording

    @property
    def hotkeyDisplay(self):
        return self._hotkey_display

    @property
    def hotkey(self):
        return self._hotkey

    def _fmt(self, combo_str):
        if not combo_str: return ""
        return " + ".join(p.capitalize() for p in combo_str.split('+'))

    def _reg(self, combo):
        # Remove only this instance's hotkey (not all hotkeys)
        if self._hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_handle)
            except:
                pass
            self._hotkey_handle = None

        self._hotkey = combo
        self._hotkey_display = self._fmt(combo)
        self.hotkeyDisplayChanged.emit(self._hotkey_display)
        self.hotkeyChanged.emit(self._hotkey)

        try:
            _log(f"Registering keyboard.add_hotkey for: {combo}")
            # Do NOT use suppress=True, otherwise it might swallow modifiers like win+shift and break OS shortcuts like win+shift+s
            self._hotkey_handle = keyboard.add_hotkey(combo, self._on_hotkey_triggered, suppress=False)
            _log("Register success.")
        except Exception as e:
            _log(f"Register failed: {e}")
            self.hotkeyRegisterFailed.emit()

    def _on_hotkey_triggered(self):
        _log("[GlobalHotkeyManager] hotkey triggered! Release modifiers...")
        # Fix stuck keys by explicitly releasing modifiers
        try:
            keyboard.release('shift')
            keyboard.release('windows')
            keyboard.release('alt')
            keyboard.release('ctrl')
        except:
            pass
        self.hotkeyTriggered.emit()

    def resetHotkey(self):
        self._cancel_record()
        self._reg(self._default_hotkey)

    def setHotkey(self, combo):
        # Route mode hotkey commands (from frontend via AppBackend.setHotkey)
        if isinstance(combo, str):
            if combo.startswith("MODE_SET:"):
                parts = combo.split(":", 2)
                if len(parts) == 3:
                    _set_mode_hotkey(parts[1], parts[2])
                return
            if combo.startswith("MODE_RESET:"):
                parts = combo.split(":", 1)
                if len(parts) == 2:
                    _reset_mode_hotkey(parts[1])
                return
        self._cancel_record()
        self._reg(combo)

    def start_interactive_record(self):
        if self._is_recording: return
        self._cancel_record()
        # Remove only this instance's hotkey during recording
        if self._hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_handle)
            except:
                pass
            self._hotkey_handle = None
        self._is_recording = True
        self.isRecordingChanged.emit(self._is_recording)
        self._hook_callback_ref = keyboard.hook(self._on_key_event)

    def _on_key_event(self, event):
        if not self._is_recording: return
        name = event.name.lower()
        if name == "windows": name = "win"
        modifiers = {"ctrl", "shift", "alt", "win"}

        if event.event_type == keyboard.KEY_DOWN:
            if name == "esc" and not any(m in self._rec_keys for m in modifiers):
                from PySide6.QtCore import QTimer
                QTimer.singleShot(10, self.cancel_interactive_record)
                return
            self._rec_keys.add(name)
            temp_combo = "+".join(self._rec_keys)
            self._temp_hotkey_display = self._fmt(temp_combo) if temp_combo else ""
            self.tempHotkeyDisplayChanged.emit(self._temp_hotkey_display)

            if name not in modifiers:
                self._temp_hotkey = temp_combo
                from PySide6.QtCore import QTimer
                QTimer.singleShot(10, self.save_interactive_record)
        elif event.event_type == keyboard.KEY_UP:
            if name in self._rec_keys:
                self._rec_keys.remove(name)
            temp_combo = "+".join(self._rec_keys)
            self._temp_hotkey_display = self._fmt(temp_combo) if temp_combo else ""
            self.tempHotkeyDisplayChanged.emit(self._temp_hotkey_display)

    def save_interactive_record(self):
        self._cancel_record()
        if hasattr(self, '_temp_hotkey') and self._temp_hotkey:
            self._hotkey = self._temp_hotkey
        self._reg(self._hotkey)
        self.hotkeyChanged.emit(self._hotkey)

    def cancel_interactive_record(self):
        self._cancel_record()
        self._reg(self._hotkey)

    def _cancel_record(self):
        if self._hook_callback_ref:
            keyboard.unhook(self._hook_callback_ref)
            self._hook_callback_ref = None
        self._is_recording = False
        self._rec_keys.clear()
        self.isRecordingChanged.emit(self._is_recording)

    def toggleRecord(self):
        if self._is_recording:
            self.cancel_interactive_record()
        else:
            self.start_interactive_record()


# ==============================================================
# Mode Hotkey System — managed via AppBackend reference
# ==============================================================

_backend_ref = None

def _get_mode_mgr(mode_name):
    global _backend_ref
    if _backend_ref:
        if mode_name == 'overlay':
            return getattr(_backend_ref, 'hotkey_overlay_mgr', None)
        elif mode_name == 'anchor':
            return getattr(_backend_ref, 'hotkey_anchor_mgr', None)
        elif mode_name == 'list':
            return getattr(_backend_ref, 'hotkey_list_mgr', None)
    return None

def _fmt_display(combo_str):
    """Format a hotkey combo string for display"""
    if not combo_str:
        return ""
    return " + ".join(p.capitalize() for p in combo_str.split('+'))


def _set_mode_hotkey(mode_name, display_combo):
    """Set a mode hotkey from display format (e.g. 'Shift + F1' -> 'shift+f1')"""
    mgr = _get_mode_mgr(mode_name)
    if mgr:
        combo = display_combo.replace(" ", "").replace("+", "+").lower()
        _log(f"[Mode Hotkey] Setting {mode_name} to {combo}")
        mgr.setHotkey(combo)


def _reset_mode_hotkey(mode_name):
    """Reset a mode hotkey to its default"""
    mgr = _get_mode_mgr(mode_name)
    if mgr:
        mgr.resetHotkey()

