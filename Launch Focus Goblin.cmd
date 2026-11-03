@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run setup.ps1 first. Python 3.11 is required.
  pause
  exit /b 1
)
start "Focus Goblin" ".venv\Scripts\pythonw.exe" -m focus_goblin
