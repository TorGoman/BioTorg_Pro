@echo off
chcp 65001 > nul
title بناء وتجميع حزمة BioTorg Pro
echo ==========================================================
echo       🚀 جاري تجميع برنامج BioTorg Pro وإنشاء ملف التثبيت
echo ==========================================================
cd /d "%~dp0"
python build_installer.py
if errorlevel 1 (
    echo.
    echo ❌ حدث خطأ أثناء عملية البناء والتجميع.
    pause
    exit /b 1
)
echo.
pause
