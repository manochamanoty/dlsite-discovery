# One-touch deploy script for Windows PowerShell
# - Updates local dev, runs scraping and export, commits, pushes dev->main, returns to dev.
# - Adjust the paths/files in $filesToAdd if必要なら追加してください。

param(
    [string]$Message = "Update data $(Get-Date -Format yyyyMMdd_HHmm)"
)

set-strictmode -version latest
$ErrorActionPreference = "Stop"

function Run($cmd) {
    Write-Host ">>> $cmd" -ForegroundColor Cyan
    Invoke-Expression $cmd
}

try {
    Run "git checkout dev"
    Run "git pull"

    Run "python scripts/run_bot.py"
    Run "python scripts/export_public_json.py"

    # 必要なファイルだけをステージ（他に変更したファイルがあればここに追加）
    $filesToAdd = @(
        "static/works.json",
        "static/images/no_image.jpg",
        "templates/index.html",
        "src/dlsite_app",
        "scripts",
        ".gitignore"
    )
    $addCmd = "git add " + ($filesToAdd -join " ")
    Run $addCmd

    Run "git commit -m `"$Message`""
    Run "git push origin dev"

    Run "git checkout main"
    Run "git merge dev"
    Run "git push origin main"

    Run "git checkout dev"

    Write-Host "Done. Vercel will deploy from main." -ForegroundColor Green
}
catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
