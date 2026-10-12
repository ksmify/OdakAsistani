@echo off
chcp 65001 >nul
title Odak Asistanı - Kaldırma Aracı
cls
echo =======================================================================
echo                 ODAK ASİSTANI - TEMİZLEME VE KALDIRMA
echo =======================================================================
echo.
echo [1/4] Çalışan Odak Asistanı süreçleri kapatılıyor...
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq Odak*" 2>nul
taskkill /F /IM pythonw.exe 2>nul

echo.
echo [2/4] Windows hosts dosyası temizleniyor ve engeller kaldırılıyor...
python -c "import sys; from blocker_engine import BlockerEngine; e = BlockerEngine(); e.sync_hosts_file(force_clean=True); sys.exit(0)" 2>nul
ipconfig /flushdns >nul

echo.
echo [3/4] Başlangıç kayıtları ve dosya kısıtlamaları kaldırılıyor...
python -c "import sys; from self_defense import cleanup_and_uninstall; cleanup_and_uninstall(); sys.exit(0)" 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "OdakAsistani" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" /v "OdakAsistani" /f 2>nul
del /f /q "%USERPROFILE%\Desktop\Odak Asistanı.lnk" 2>nul
del /f /q "%USERPROFILE%\Desktop\Odak Asistani.lnk" 2>nul

echo.
echo [4/4] Tamamlandı!
echo.
echo =======================================================================
echo [BAŞARILI] Odak Asistanı'na ait tüm kısıtlamalar ve kayıtlar temizlendi.
echo Artık bu klasörü dilediğiniz gibi silebilir veya taşıyabilirsiniz.
echo =======================================================================
echo.
pause
