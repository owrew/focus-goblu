$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' -m pip install 'pyinstaller>=6.12,<7'
if ($LASTEXITCODE -ne 0) { throw 'Could not install packaging tool.' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --windowed --onedir --name FocusGoblin --paths . --collect-data mediapipe --collect-binaries mediapipe --exclude-module jax --exclude-module jaxlib --exclude-module pytest --exclude-module torch packaging/entry.py
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed. See console output.' }
Write-Host 'Built dist\FocusGoblin\FocusGoblin.exe. Keep the entire FocusGoblin folder together.'
