# -*- coding: utf-8 -*-
"""
BioTorg Pro - نظام بناء الحزم وتوليد ملف التثبيت التلقائي
مطور بواسطة: Ahmed TorGoman (Telegram: @torgoman0)
"""

import os
import sys
import shutil
import zipfile
import subprocess
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist", "BioTorg_Pro")
INSTALLER_DIR = os.path.join(BASE_DIR, "dist_installer")
TOOLS_DIR = os.path.join(BASE_DIR, "tools", "InnoSetup")
ISS_FILE = os.path.join(BASE_DIR, "BioTorg_Pro_Setup.iss")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    print("=" * 60)
    print("      🚀 BioTorg Pro - Build & Packaging System")
    print("=" * 60)

    # 1. تجميع عبر PyInstaller
    print("\n[1/4] جاري تجميع ملفات البرنامج عبر PyInstaller...")
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "-y", "BioTorg_Pro.spec"]
    ret = subprocess.call(cmd, cwd=BASE_DIR)
    if ret != 0:
        print("❌ فشل تجميع ملفات PyInstaller.")
        sys.exit(ret)

    if not os.path.exists(DIST_DIR):
        print(f"❌ لم يتم العثور على مجلد التوزيع: {DIST_DIR}")
        sys.exit(1)

    # نسخ ملفات الإعدادات والنسخة لضمان وجودها
    shutil.copy2(os.path.join(BASE_DIR, "version.json"), os.path.join(DIST_DIR, "version.json"))
    cfg_src = os.path.join(BASE_DIR, "attendance_config.json")
    if os.path.exists(cfg_src):
        shutil.copy2(cfg_src, os.path.join(DIST_DIR, "attendance_config.json"))
    ico_src = os.path.join(BASE_DIR, "app_icon.ico")
    if os.path.exists(ico_src):
        shutil.copy2(ico_src, os.path.join(DIST_DIR, "app_icon.ico"))

    print(f"✅ تم تجميع ملفات البرنامج بنجاح في: {DIST_DIR}")

    # 2. فحص مترجم Inno Setup
    print("\n[2/3] جاري فحص مترجم Inno Setup (ISCC)...")
    iscc_candidates = [
        shutil.which("iscc"),
        os.path.join(TOOLS_DIR, "app", "ISCC.exe"),
        os.path.join(TOOLS_DIR, "ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    iscc_path = None
    for cand in iscc_candidates:
        if cand and os.path.exists(cand):
            iscc_path = cand
            break

    if not iscc_path:
        print("⚠️ لم يتم العثور على Inno Setup في النظام. جاري تنزيله تلقائياً وتثبيته...")
        os.makedirs(TOOLS_DIR, exist_ok=True)
        setup_exe = os.path.join(TOOLS_DIR, "inno_setup.exe")
        inno_url = "https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe"
        try:
            req = urllib.request.Request(inno_url, headers={"User-Agent": "BioTorgPro-Installer-Builder"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(setup_exe, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)

            print("⚙️ جاري تثبيت Inno Setup في مجلد tools...")
            app_dir = os.path.join(TOOLS_DIR, "app")
            install_cmd = [setup_exe, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={app_dir}"]
            subprocess.call(install_cmd)

            local_iscc = os.path.join(app_dir, "ISCC.exe")
            if os.path.exists(local_iscc):
                iscc_path = local_iscc
            elif os.path.exists(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"):
                iscc_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        except Exception as e:
            print(f"تعذر تنزيل Inno Setup تلقائياً: {e}")

    # 3. بناء ملف التثبيت
    if iscc_path and os.path.exists(iscc_path):
        print(f"\n[3/3] جاري تجميع ملف التثبيت بواسطة: {iscc_path}...")
        compile_cmd = [iscc_path, ISS_FILE]
        ret_iscc = subprocess.call(compile_cmd)
        if ret_iscc == 0:
            print("\n" + "=" * 60)
            print("🎉 تم الانتهاء بنجاح! ملف التثبيت الجاهز:")
            print("📦 مثبت البرنامج الرسمي: dist_installer\\BioTorg_Pro_Setup_v2.2.1.exe")
            print("=" * 60)
            return

    print("\n⚠️ تم تجميع البرنامج، ولكن يلزم تشغيل Inno Setup لبناء ملف Setup.exe.")


if __name__ == "__main__":
    main()
