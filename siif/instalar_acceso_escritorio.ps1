# Crea un acceso directo en el Escritorio hacia ActualizarCopaGastos.bat
$ErrorActionPreference = "Stop"

$siifDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $siifDir
$batPath = Join-Path $siifDir "ActualizarCopaGastos.bat"

if (-not (Test-Path $batPath)) {
    throw "No se encontro el bat: $batPath"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "Actualizar Copa Gastos.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $batPath
$shortcut.WorkingDirectory = $repoRoot
$shortcut.WindowStyle = 1
$shortcut.Description = "Descarga SIIF Copa Gastos y actualiza la base (solo captcha manual)"
$shortcut.Save()

Write-Host "Acceso creado:"
Write-Host "  $lnkPath"
Write-Host "Apunta a:"
Write-Host "  $batPath"
Write-Host "Working directory:"
Write-Host "  $repoRoot"
