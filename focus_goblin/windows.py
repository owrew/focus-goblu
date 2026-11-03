"""Native global pause and optional per-user startup registration."""
import os
import sys
import ctypes
from ctypes import wintypes
from pathlib import Path
from PySide6.QtCore import QAbstractNativeEventFilter, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

SHORTCUTS = {'Ctrl+Alt+P':(3,0x50),'Ctrl+Shift+P':(6,0x50),'Ctrl+Alt+Space':(3,0x20)}


class GlobalPause(QAbstractNativeEventFilter):
    identifier = 0x4852
    def __init__(self,window,callback):
        super().__init__(); self.window = window; self.callback = callback; self.registered = False
        self.hwnd = None
        QApplication.instance().installNativeEventFilter(self)

    def register(self,enabled=True,shortcut='Ctrl+Alt+P'):
        self.unregister()
        if not enabled: return 'Global pause disabled'
        if os.name != 'nt' or QGuiApplication.platformName() != 'windows': return 'Global pause requires Windows desktop'
        self.hwnd = int(self.window.winId()); mods,key = SHORTCUTS.get(shortcut,SHORTCUTS['Ctrl+Alt+P'])
        user32 = ctypes.windll.user32
        user32.RegisterHotKey.argtypes = [wintypes.HWND,ctypes.c_int,wintypes.UINT,wintypes.UINT]
        self.registered = bool(user32.RegisterHotKey(self.hwnd,self.identifier,mods|0x4000,key))
        return f'Global pause: {shortcut}' if self.registered else 'Shortcut is already in use. Choose another combination.'

    def nativeEventFilter(self,event_type,message):
        if self.registered:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x312 and msg.wParam == self.identifier:
                QTimer.singleShot(0,self.callback); return True,0
        return False,0

    def unregister(self):
        if self.registered:
            ctypes.windll.user32.UnregisterHotKey(wintypes.HWND(self.hwnd),self.identifier)
        self.registered = False

    def close(self):
        self.unregister(); QApplication.instance().removeNativeEventFilter(self)


def startup_enabled():
    if os.name != 'nt': return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
            return bool(winreg.QueryValueEx(key,'FocusGoblin')[0])
    except OSError: return False


def set_startup(enabled):
    if os.name != 'nt': return
    import winreg
    if getattr(sys,'frozen',False): command = f'"{sys.executable}" --pet-only'
    else:
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        command = f'"{pythonw}" "{Path(__file__).resolve().parent.parent / "launch.py"}" --pet-only'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled: winreg.SetValueEx(key,'FocusGoblin',0,winreg.REG_SZ,command)
        else:
            try: winreg.DeleteValue(key,'FocusGoblin')
            except FileNotFoundError: pass
