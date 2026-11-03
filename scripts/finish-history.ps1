$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

function Commit-Paths($message, $paths) {
    git add -- $paths
    if ($LASTEXITCODE -ne 0) { throw "Staging failed: $message" }
    git commit -m $message
    if ($LASTEXITCODE -ne 0) { throw "Commit failed: $message" }
}

Commit-Paths 'Align desktop version metadata with the 0.3 release' @('focus_goblin/__init__.py','pyproject.toml')
Commit-Paths 'Show the desktop observatory in the README' @('docs/images/desktop-demo.png')
Commit-Paths 'Check private publication and GitHub signature status' @('scripts/publish-private.ps1','scripts/finish-history.ps1')
git fsck --full
if ($LASTEXITCODE -ne 0) { throw 'Git integrity verification failed.' }
git log --format='%h %G? %s'
