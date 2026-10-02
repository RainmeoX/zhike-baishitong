@echo off
rem RAGGO 自动提交推送：双击或在项目目录执行 autogit.cmd
cd /d "%~dp0"
git add -A
git commit -m "auto: %date% %time% 项目进度" --allow-empty-message -q 2>nul
git push
if errorlevel 1 (
  echo [!] 推送失败，检查网络或 GitCode 凭据
  pause
) else (
  echo [OK] 已自动提交并推送
)
