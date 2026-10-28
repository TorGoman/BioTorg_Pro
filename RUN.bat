@echo off
chcp 65001 > nul
title BioTorg Pro - نظام إدارة الحضور ومسير الرواتب
echo جاري تشغيل برنامج BioTorg Pro...
cd /d "%~dp0"
start "" pythonw attendance_gui.py
if errorlevel 1 (
    echo تعذر تشغيل pythonw، جاري التشغيل عبر python العادي...
    python attendance_gui.py
    pause
)
