@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m focus_goblin --demo
if errorlevel 1 pause
