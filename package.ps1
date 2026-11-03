$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' -m pip install 'pyinstaller>=6.12,<7'
if ($LASTEXITCODE -ne 0) { throw 'Could not install packaging tool.' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --windowed --onedir --name FocusGoblin-v0.3 --icon focus_goblin/assets/goblin-logo.png --add-data 'focus_goblin/assets;focus_goblin/assets' --paths . --collect-data mediapipe --collect-binaries mediapipe --exclude-module jax --exclude-module jaxlib --exclude-module pytest --exclude-module torch packaging/entry.py
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed. See console output.' }
Copy-Item -LiteralPath '.\models' -Destination '.\dist\FocusGoblin-v0.3' -Recurse -Force
Write-Host 'Built dist\FocusGoblin-v0.3\FocusGoblin-v0.3.exe. Keep the entire folder together.'
