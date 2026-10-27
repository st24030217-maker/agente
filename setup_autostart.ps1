# Script de instalación de auto-inicio 24/7 para Sebax
$wsh = New-Object -ComObject WScript.Shell
$startupFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$shortcutPath = Join-Path $startupFolder "Sebax24_7.lnk"
$vbsPath = Join-Path $PSScriptRoot "start_24_7.vbs"

$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$vbsPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "Sebax AI Agent 24/7 Background Service"
$shortcut.Save()

Write-Host "Auto-inicio configurado exitosamente en: $shortcutPath" -ForegroundColor Green
Write-Host "Sebax iniciará automáticamente cada vez que inicies sesión en Windows." -ForegroundColor Cyan
