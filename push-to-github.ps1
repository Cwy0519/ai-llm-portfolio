<#
.SYNOPSIS
    把作品集推送到 GitHub。
.DESCRIPTION
    首次使用前，先在 GitHub 网页新建一个空仓库（不要勾选 README / .gitignore / license），
    然后在 GitHub 里生成 Token，或者直接用浏览器弹窗登录。
.EXAMPLE
    .\push-to-github.ps1 -GitHubUser chenguocheng
.EXAMPLE
    .\push-to-github.ps1 -GitHubUser chenguocheng -RepoName ai-llm-portfolio
#>
param(
    [Parameter(Mandatory = $true)][string]$GitHubUser,
    [string]$RepoName = "ai-llm-portfolio"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "✗ 没有检测到 Git。请先安装：https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

$remote = "https://github.com/$GitHubUser/$RepoName.git"
Write-Host "目标仓库：$remote" -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    git init | Out-Null
    Write-Host "✓ 已初始化本地仓库" -ForegroundColor Green
}

git add .
git -c user.name=$GitHubUser -c user.email="$GitHubUser@users.noreply.github.com" commit -m "作品集：4 个个人项目（AI 大模型应用 + 学生成绩管理系统）" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "（没有新改动需要提交，继续推送）" -ForegroundColor Yellow }

git branch -M main
$existing = git remote 2>$null
if ($existing -contains "origin") { git remote remove origin }
git remote add origin $remote

Write-Host "正在推送……首次会弹出 GitHub 登录窗口" -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ 推送成功：https://github.com/$GitHubUser/$RepoName" -ForegroundColor Green
    Write-Host "  把这个链接填进简历的「作品集」一行即可。" -ForegroundColor Green
} else {
    Write-Host "✗ 推送失败：确认网页上已经建好空仓库，并且登录/Token 有 repo 权限" -ForegroundColor Red
}
