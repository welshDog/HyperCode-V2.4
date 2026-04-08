# BROski Bot v4.0 - GitHub Deployment Script

Write-Host "🐶♾️ BROski Bot v4.0 - Deploying to GitHub" -ForegroundColor Cyan

# Get repo details
$username = Read-Host "GitHub username"
$repoName = Read-Host "Repository name (e.g., BROski-Bot)"

# Initialize git
if (!(Test-Path .git)) {
    git init
    git branch -M main
}

# Add remote
git remote remove origin 2>$null
git remote add origin "https://github.com/$username/$repoName.git"

# Stage and commit
git add .
git commit -m "feat: BROski Bot v4.0 Phase 1 Foundation

- PostgreSQL database (20+ tables)
- Redis caching layer
- Quest system bug fix
- Phase 4B Gig Marketplace
- Complete v4.0 documentation

BREAKING CHANGE: SQLite → PostgreSQL"

# Push
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host "View at: https://github.com/$username/$repoName"
} else {
    Write-Host "❌ Push failed. Check credentials." -ForegroundColor Red
}
