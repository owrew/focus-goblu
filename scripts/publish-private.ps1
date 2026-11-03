$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

function Require-Success($step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed." }
}

$env:GCM_INTERACTIVE = 'Never'
$env:GIT_TERMINAL_PROMPT = '0'
$stored = @("protocol=https","host=github.com","") | git credential fill 2>$null
$passwordLine = $stored | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
if (-not $passwordLine) { throw 'No stored GitHub credential was available.' }

$previousToken = $env:GH_TOKEN
try {
    $env:GH_TOKEN = $passwordLine.Substring(9)
    $owner = gh api user --jq .login
    Require-Success 'GitHub authentication'
    $repository = "$owner/focus-goblin-mistwatch"
    if (git remote) { throw 'A remote already exists. Review it before publishing.' }
    if (git status --porcelain) { throw 'Commit or review outstanding files before publishing.' }
    git fsck --full
    Require-Success 'History verification'
    $suspicious = git log --all --format='%h' -G 'github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
    Require-Success 'Credential pattern scan'
    if ($suspicious) { throw 'Potential credential material found in commit history.' }
    $excluded = git rev-list --objects --all | Select-String ' (work/|dist/|build/|installer/|\.venv/)|\.(onnx|weights|pt|exe|sqlite3)$'
    if ($excluded) { throw 'Excluded local data or binaries are tracked in history.' }
    gh repo create $repository --private --description 'Focus Goblin Mistwatch desktop app and browser focus timer' --source . --remote origin --push
    Require-Success 'Private repository creation and push'
    $remote = gh repo view $repository --json url,isPrivate,defaultBranchRef | ConvertFrom-Json
    Require-Success 'Remote verification'
    if (-not $remote.isPrivate -or $remote.defaultBranchRef.target.oid -ne (git rev-parse HEAD)) {
        throw 'Remote visibility or commit does not match.'
    }
    Write-Output $remote.url
    Write-Output "Verified private remote HEAD: $(git rev-parse HEAD)"
    gh api "repos/$repository/commits?per_page=100" --jq '"GitHub-verified signatures: " + ([.[] | select(.commit.verification.verified)] | length | tostring) + "/" + (length | tostring)'
    Require-Success 'GitHub signature check'
} finally {
    $env:GH_TOKEN = $previousToken
}
