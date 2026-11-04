$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$compilerCandidates = @('work\inno\ISCC.exe','C:\Program Files\Inno Setup 7\ISCC.exe','C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
$compilerPath = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compilerPath) { throw 'Install Inno Setup from jrsoftware.org first, or put a portable compiler in work\inno.' }
if (-not (Test-Path -LiteralPath 'dist\FocusGoblu-v0.4\FocusGoblu-v0.4.exe')) { throw 'Run package.ps1 first.' }
& $compilerPath 'packaging\installer.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
Write-Host 'Installer: installer\FocusGoblu-Setup-0.4.0.exe'
