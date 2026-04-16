param(
    [string]$RepoRoot = (Get-Location).Path
)

$hooksDir = Join-Path $RepoRoot ".git/hooks"
if (-not (Test-Path $hooksDir)) {
    Write-Error "No .git/hooks found. Run from repo root."
    exit 1
}

$src = Join-Path $RepoRoot "scripts/git-hooks/post-commit"
$dst = Join-Path $hooksDir "post-commit"

Copy-Item -Force $src $dst
try {
    git update-index --chmod=+x scripts/git-hooks/post-commit | Out-Null
} catch {
}
Write-Output "Installed post-commit hook -> $dst"
