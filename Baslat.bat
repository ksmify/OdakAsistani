@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYW_EXE="
set "PY_EXE="

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" (
    set "PYW_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe"
    set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
)

if "%PYW_EXE%"=="" (
    for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-*") do (
        if exist "%%D\pythonw.exe" (
            set "PYW_EXE=%%D\pythonw.exe"
            set "PY_EXE=%%D\python.exe"
        )
    )
)

if "%PYW_EXE%"=="" (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
        if exist "%%D\pythonw.exe" (
            set "PYW_EXE=%%D\pythonw.exe"
            set "PY_EXE=%%D\python.exe"
        )
    )
)

if "%PYW_EXE%"=="" (
    where pythonw >nul 2>nul
    if %errorlevel%==0 (
        set "PYW_EXE=pythonw"
        set "PY_EXE=python"
    )
)

if "%PYW_EXE%"=="" (
    echo [!] Python bulunamadi. Lutfen Python 3.10+ yukleyin: https://www.python.org/downloads/
    pause
    exit /b 1
)

"%PY_EXE%" -c "import customtkinter, PIL, pystray" >nul 2>nul
if not %errorlevel%==0 (
    echo [*] Ilk kurulum: Gerekli kutuphaneler yukleniyor...
    "%PY_EXE%" -m pip install -r "%~dp0requirements.txt"
)

if exist "%~dp0OdakAsistani.exe" (
    start "" "%~dp0OdakAsistani.exe" "%~dp0main.py"
) else (
    if exist "%PYW_EXE%" copy /y "%PYW_EXE%" "%~dp0OdakAsistani.exe" >nul 2>nul
    if exist "%~dp0OdakAsistani.exe" (
        start "" "%~dp0OdakAsistani.exe" "%~dp0main.py"
    ) else (
        start "" "%PYW_EXE%" "%~dp0main.py"
    )
)

