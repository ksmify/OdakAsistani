@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Odak Asistanı - Otomatik Kurulum Sihirbazı (Setup)

echo ============================================================================
echo        ODAK ASİSTANI — OTOMATİK KURULUM VE HAZIRLIK SİHİRBAZI
echo ============================================================================
echo.
echo [*] Sistem ve Python bileşenleri denetleniyor...

set "PY_CMD="
set "PYW_CMD="

:: 1. Sistemde mevcut Python 3.10+ kontrolü
for %%P in ("%LOCALAPPDATA%\Python\pythoncore-3.14-64" "%LOCALAPPDATA%\Programs\Python\Python312" "%LOCALAPPDATA%\Programs\Python\Python311" "%LOCALAPPDATA%\Programs\Python\Python310" "C:\Python312" "C:\Python311" "C:\Python310") do (
    if exist "%%~P\python.exe" (
        set "PY_CMD=%%~P\python.exe"
        set "PYW_CMD=%%~P\pythonw.exe"
        goto :python_found
    )
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if %errorlevel%==0 (
        set "PY_CMD=py -3"
        set "PYW_CMD=pyw -3"
        goto :python_found
    )
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if %errorlevel%==0 (
        set "PY_CMD=python"
        where pythonw >nul 2>nul
        if %errorlevel%==0 (
            set "PYW_CMD=pythonw"
        ) else (
            set "PYW_CMD=python"
        )
        goto :python_found
    )
)

:: 2. Python bulunamadıysa python.org'dan otomatik indir ve kur
echo [!] Sistemde uyumlu Python (3.10+) bulunamadı.
echo [*] Python 3.11 (64-Bit) resmi python.org adresinden otomatik indiriliyor...
set "TEMP_INSTALLER=%TEMP%\python_installer.exe"

powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', '%TEMP_INSTALLER%')"
if not exist "%TEMP_INSTALLER%" (
    echo [X] Python indirme işlemi başarısız oldu. Lütfen manuel kurun: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [*] Python sessiz modda kuruluyor, lütfen 15-30 saniye bekleyin...
"%TEMP_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 Shortcuts=0
del /f /q "%TEMP_INSTALLER%" >nul 2>nul

:: Kurulum sonrası kontrol
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    set "PYW_CMD=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
) else (
    set "PY_CMD=python"
    set "PYW_CMD=pythonw"
)

:python_found
echo [+] Python hazır: %PY_CMD%
echo.

:: 3. Kütüphaneleri kur / güncelle
echo [*] Gerekli Python kütüphaneleri (customtkinter, Pillow, pystray, pywin32) yükleniyor...
%PY_CMD% -m pip install --quiet --upgrade pip
if exist "%~dp0requirements.txt" (
    %PY_CMD% -m pip install --quiet -r "%~dp0requirements.txt"
) else (
    %PY_CMD% -m pip install --quiet customtkinter Pillow pystray pywin32
)

:: 4. Görev Yöneticisinde "OdakAsistani.exe" olarak görünmesi için pythonw'yi kopyala
if exist "%PYW_CMD%" (
    copy /y "%PYW_CMD%" "%~dp0OdakAsistani.exe" >nul 2>nul
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$cmd = (Get-Command pythonw -ErrorAction SilentlyContinue); if ($cmd) { Copy-Item $cmd.Source '%~dp0OdakAsistani.exe' -Force }" >nul 2>nul
)

:: 5. Masaüstü kısayolu oluştur (Odak Asistanı.lnk)
echo [*] Masaüstü kısayolu oluşturuluyor...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desk = [Environment]::GetFolderPath('Desktop'); $lnkPath = Join-Path $desk 'Odak Asistanı.lnk'; $s = $ws.CreateShortcut($lnkPath); if (Test-Path '%~dp0OdakAsistani.exe') { $s.TargetPath = '%~dp0OdakAsistani.exe'; $s.Arguments = '\"%~dp0main.py\"'; } else { $s.TargetPath = '%~dp0Baslat.bat'; }; $s.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0odak_icon.ico') { $s.IconLocation = '%~dp0odak_icon.ico,0' }; $s.Save()" >nul 2>nul

echo.
echo ============================================================================
echo   [+] TEBRİKLER! ODAK ASİSTANI BAŞARIYLA KURULDU.
echo   [+] Masaüstünüze 'Odak Asistanı' kısayolu eklendi.
echo   [*] Uygulama şimdi başlatılıyor...
echo ============================================================================
echo.

:: 6. Uygulamayı başlat
if exist "%~dp0OdakAsistani.exe" (
    start "" "%~dp0OdakAsistani.exe" "%~dp0main.py"
) else (
    start "" "%PYW_CMD%" "%~dp0main.py"
)

timeout /t 3 >nul
exit /b 0
