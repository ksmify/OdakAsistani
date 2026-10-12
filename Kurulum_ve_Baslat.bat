@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================================
echo   ODAK ASISTANI - OTOMATIK KURULUM VE BASLATICI
echo ============================================================================
echo.

call "%~dp0Baslat.bat"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desk = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut((Join-Path $desk 'Odak Asistanı.lnk')); $s.TargetPath = '%~dp0Baslat.bat'; $s.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0odak_icon.ico') { $s.IconLocation = '%~dp0odak_icon.ico,0' }; $s.Save()" >nul 2>nul

echo [+] Odak Asistani baslatildi ve masaustu kisayolu olusturuldu!
timeout /t 3 >nul
