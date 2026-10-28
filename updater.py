"""
نظام التحديث التلقائي الذكي - BioTorg Pro
مطور بواسطة: Ahmed TorGoman (Telegram: @torgoman0)
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
import urllib.request
import threading
import webbrowser
from typing import Optional, Dict, Any, Tuple
import customtkinter as ctk

def get_app_dir() -> str:
    """الحصول على المجلد الأساسي للبرنامج سواء كان يعمل ككود أو كملف تنفيذي EXE"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_app_dir()
VERSION_FILE = os.path.join(BASE_DIR, "version.json")
STATE_FILE = os.path.join(BASE_DIR, "updater_state.json")
TEMP_UPDATE_DIR = os.path.join(BASE_DIR, "update_temp")

DEFAULT_REPO_OWNER = "TorGoman"
DEFAULT_REPO_NAME = "BioTorg_Pro"


def get_local_version_info() -> Dict[str, Any]:
    """قراءة بيانات الإصدار الحالي من ملف version.json"""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "version": "2.2.1",
        "release_date": "2026-10-28",
        "repo_owner": DEFAULT_REPO_OWNER,
        "repo_name": DEFAULT_REPO_NAME,
        "changelog": []
    }


def get_updater_state() -> Dict[str, Any]:
    """قراءة حالة التحديثات المحلية"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_seen_version": "2.2.1", "pending_changelog": False}


def save_updater_state(state: Dict[str, Any]) -> None:
    """حفظ حالة التحديثات"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving updater state:", e)


def parse_version_tuple(v_str: str) -> Tuple[int, ...]:
    """تحويل نص الإصدار مثل '2.2.0' إلى أرقام للمقارنة الدقيقة"""
    try:
        clean = v_str.strip().lstrip("vV")
        return tuple(int(x) for x in clean.split("."))
    except Exception:
        return (0, 0, 0)


def is_newer_version(remote_v: str, local_v: str) -> bool:
    """مقارنة هل الإصدار البعيد أحدث من الحالي"""
    return parse_version_tuple(remote_v) > parse_version_tuple(local_v)


def check_for_updates_background(callback):
    """فحص توفر تحديث من GitHub في خيط عمل خلفي هادئ وبدون أي تعطيل"""
    def _worker():
        local_info = get_local_version_info()
        owner = local_info.get("repo_owner", DEFAULT_REPO_OWNER)
        repo = local_info.get("repo_name", DEFAULT_REPO_NAME)
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/version.json"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "BioTorgPro-Attendance-Updater"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    remote_info = json.loads(response.read().decode("utf-8"))
                    remote_ver = remote_info.get("version", "0.0.0")
                    local_ver = local_info.get("version", "0.0.0")

                    if is_newer_version(remote_ver, local_ver):
                        callback(True, remote_info)
                        return
        except Exception:
            # تجاهل أخطاء انقطاع الإنترنت أو عدم وجود اتصال للهدوء التام
            pass

        callback(False, None)

    threading.Thread(target=_worker, daemon=True).start()


def download_and_install_update(remote_info: Dict[str, Any], progress_callback=None, finish_callback=None):
    """تنزيل التحديث من GitHub واستبدال الملفات البرمجية بأمان ثم إعادة التشغيل (يدعم الكود والـ EXE)"""
    def _worker():
        local_info = get_local_version_info()
        owner = remote_info.get("repo_owner", local_info.get("repo_owner", DEFAULT_REPO_OWNER))
        repo = remote_info.get("repo_name", local_info.get("repo_name", DEFAULT_REPO_NAME))
        is_frozen = getattr(sys, 'frozen', False)

        try:
            if os.path.exists(TEMP_UPDATE_DIR):
                shutil.rmtree(TEMP_UPDATE_DIR, ignore_errors=True)
            os.makedirs(TEMP_UPDATE_DIR, exist_ok=True)

            installer_url = remote_info.get("installer_url")
            exe_download_url = remote_info.get("exe_download_url")

            # حالة 1: التطبيق مجمع كـ EXE ويتوفر ملف تثبيت أو حزمة تحديث مجمعة
            if is_frozen:
                candidate_urls = []
                if installer_url:
                    candidate_urls.append(installer_url)

                ver = remote_info.get("version", "")
                raw_url = f"https://github.com/{owner}/{repo}/raw/main/BioTorg_Pro_Setup_v{ver}.exe"
                if raw_url not in candidate_urls:
                    candidate_urls.append(raw_url)

                rel_url = f"https://github.com/{owner}/{repo}/releases/download/v{ver}/BioTorg_Pro_Setup_v{ver}.exe"
                if rel_url not in candidate_urls:
                    candidate_urls.append(rel_url)

                inst_dest = os.path.join(TEMP_UPDATE_DIR, "BioTorg_Pro_Setup.exe")
                downloaded = False
                last_err = None

                for target_url in candidate_urls:
                    try:
                        if progress_callback:
                            progress_callback("جاري تنزيل ملف التثبيت المحدث من GitHub...")
                        req = urllib.request.Request(target_url, headers={"User-Agent": "BioTorgPro-Attendance-Updater"})
                        with urllib.request.urlopen(req, timeout=120) as resp, open(inst_dest, "wb") as f_out:
                            shutil.copyfileobj(resp, f_out)
                        if os.path.exists(inst_dest) and os.path.getsize(inst_dest) > 1000000:
                            downloaded = True
                            break
                    except Exception as err:
                        last_err = err
                        continue

                if not downloaded:
                    raise Exception(f"{last_err or 'تعذر تنزيل ملف التثبيت'}")

                    # تسجيل الحالة
                    state = {
                        "last_seen_version": remote_info.get("version", "2.2.0"),
                        "pending_changelog": True,
                        "changelog": remote_info.get("changelog", [])
                    }
                    save_updater_state(state)

                    if progress_callback:
                        progress_callback("جاري تشغيل مثبت التحديث وإعادة التشغيل...")

                    bat_path = os.path.join(TEMP_UPDATE_DIR, "apply_installer.bat")
                    with open(bat_path, "w", encoding="utf-8") as f:
                        f.write(f'@echo off\ntimeout /t 2 /nobreak > nul\nstart "" "{inst_dest}" /SILENT /CLOSEAPPLICATIONS\ndel "%~f0"\n')

                    subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    sys.exit(0)

                elif exe_download_url:
                    if progress_callback:
                        progress_callback("جاري تنزيل حزمة التحديث من GitHub...")
                    zip_dest = os.path.join(TEMP_UPDATE_DIR, "update.zip")
                    req = urllib.request.Request(exe_download_url, headers={"User-Agent": "BioTorgPro-Attendance-Updater"})
                    with urllib.request.urlopen(req, timeout=60) as resp, open(zip_dest, "wb") as f_out:
                        shutil.copyfileobj(resp, f_out)

                    if progress_callback:
                        progress_callback("جاري فك الضغط وتطبيق التحديثات...")

                    extract_dest = os.path.join(TEMP_UPDATE_DIR, "extracted")
                    with zipfile.ZipFile(zip_dest, "r") as zf:
                        zf.extractall(extract_dest)

                    subfolders = [os.path.join(extract_dest, d) for d in os.listdir(extract_dest) if os.path.isdir(os.path.join(extract_dest, d))]
                    source_dir = subfolders[0] if subfolders else extract_dest

                    state = {
                        "last_seen_version": remote_info.get("version", "2.2.0"),
                        "pending_changelog": True,
                        "changelog": remote_info.get("changelog", [])
                    }
                    save_updater_state(state)

                    bat_path = os.path.join(TEMP_UPDATE_DIR, "apply_update.bat")
                    with open(bat_path, "w", encoding="utf-8") as f:
                        f.write(f'@echo off\nchcp 65001 > nul\ntimeout /t 2 /nobreak > nul\nxcopy /s /e /y "{source_dir}\\*" "{BASE_DIR}\\"\nstart "" "{sys.executable}"\nrd /s /q "{TEMP_UPDATE_DIR}"\ndel "%~f0"\n')

                    subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    sys.exit(0)

                else:
                    # في حال كان EXE ولم يرفع المطور ملفات release ثنائية بعد، نفتح صفحة GitHub
                    if progress_callback:
                        progress_callback("جاري فتح صفحة التحديثات على GitHub...")
                    webbrowser.open(f"https://github.com/{owner}/{repo}/releases")
                    if finish_callback:
                        finish_callback(False, "يرجى تنزيل أحدث ملف تثبيت من صفحة Releases على GitHub.")
                    return

            # حالة 2: التطبيق يعمل عبر Python العادي (تحديث مباشر من مستودع الكود)
            zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
            if progress_callback:
                progress_callback("جاري تنزيل ملفات التحديث من GitHub...")

            zip_dest = os.path.join(TEMP_UPDATE_DIR, "update.zip")
            req = urllib.request.Request(
                zip_url,
                headers={"User-Agent": "BioTorgPro-Attendance-Updater"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(zip_dest, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)

            if progress_callback:
                progress_callback("جاري فك الضغط وتطبيق التحديثات البرمجية...")

            extract_dest = os.path.join(TEMP_UPDATE_DIR, "extracted")
            with zipfile.ZipFile(zip_dest, "r") as zf:
                zf.extractall(extract_dest)

            # تحديد مجلد الأرشيف المستخرج (مثل BioTorg_Pro-main)
            subfolders = [os.path.join(extract_dest, d) for d in os.listdir(extract_dest) if os.path.isdir(os.path.join(extract_dest, d))]
            source_dir = subfolders[0] if subfolders else extract_dest

            # الملفات المحمية التي لا يتم مسحها أو استبدالها أبداً للحفاظ على بيانات وإعدادات المستخدم
            PROTECTED_FILES = {
                "attendance_config.json",
                "attendance_adjustments.json",
                "updater_state.json",
                ".git"
            }

            for item in os.listdir(source_dir):
                if item in PROTECTED_FILES:
                    continue

                if item.endswith(".TXT") or item.endswith(".xlsx") or item.endswith(".csv"):
                    continue

                src_path = os.path.join(source_dir, item)
                dst_path = os.path.join(BASE_DIR, item)

                if os.path.isdir(src_path):
                    if os.path.exists(dst_path):
                        shutil.rmtree(dst_path, ignore_errors=True)
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)

            state = {
                "last_seen_version": remote_info.get("version", "2.2.0"),
                "pending_changelog": True,
                "changelog": remote_info.get("changelog", [])
            }
            save_updater_state(state)

            if progress_callback:
                progress_callback("تم التحديث بنجاح! جاري إعادة تشغيل البرنامج...")

            shutil.rmtree(TEMP_UPDATE_DIR, ignore_errors=True)

            if finish_callback:
                finish_callback(True)

            restart_application()

        except Exception as e:
            print("Error during update installation:", e)
            if finish_callback:
                finish_callback(False, str(e))

    threading.Thread(target=_worker, daemon=True).start()


def restart_application():
    """إعادة تشغيل البرنامج في عملية مستقلة متوافقة مع الكود وملفات EXE"""
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable])
    else:
        python_exe = sys.executable
        main_script = os.path.join(BASE_DIR, "attendance_gui.py")
        subprocess.Popen([python_exe, main_script])
    sys.exit(0)


class UpdateDialog(ctk.CTkToplevel):
    """نافذة أنيقة لإعلام المستخدم بتوفر تحديث جديد مع خيار التنزيل والتشغيل الفوري"""
    def __init__(self, parent, current_ver: str, remote_info: Dict[str, Any]):
        super().__init__(parent)
        self.title("🔔 تحديث جديد متوفر")
        self.geometry("540x500")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        new_ver = remote_info.get("version", "2.3.0")
        changelog = remote_info.get("changelog", [])

        # ترويسة أنيقة
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("#F1F5F9", "#18130C"))
        header_frame.pack(fill="x")

        ctk.CTkLabel(
            header_frame,
            text=f"🚀 يتوفر إصدار جديد من البرنامج: v{new_ver}",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#F59E0B"
        ).pack(pady=(15, 4))

        ctk.CTkLabel(
            header_frame,
            text=f"الإصدار الحالي: v{current_ver}  ←  الإصدار المتاح: v{new_ver}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#475569", "#D1A562")
        ).pack(pady=(0, 12))

        # صندوق محتويات ومميزات التحديث
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=20, pady=12)

        ctk.CTkLabel(
            body_frame,
            text="✨ ما الجديد في هذا الإصدار:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#1E293B", "#F8FAFC")
        ).pack(anchor="e", pady=(0, 8))

        scroll_box = ctk.CTkScrollableFrame(body_frame, height=200, fg_color=("#FFFFFF", "#1E1810"), corner_radius=8)
        scroll_box.pack(fill="both", expand=True)

        if changelog:
            for item in changelog:
                row = ctk.CTkFrame(scroll_box, fg_color="transparent")
                row.pack(fill="x", pady=4, anchor="e")
                ctk.CTkLabel(
                    row,
                    text=f"• {item}",
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color=("#334155", "#E2E8F0"),
                    wraplength=460,
                    justify="right"
                ).pack(side="right", padx=5)
        else:
            ctk.CTkLabel(
                scroll_box,
                text="تحسينات في الأداء وإصلاحات استقرار عامة للنظام.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=("#64748B", "#94A3B8")
            ).pack(pady=20)

        # شريط حالة التحميل
        self.status_label = ctk.CTkLabel(
            self,
            text="هل ترغب في تنزيل التحديث والتثبيت الآن؟",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748B", "#D1A562")
        )
        self.status_label.pack(pady=(4, 8))

        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal", mode="indeterminate")

        # أزرار الإجراء
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_cancel = ctk.CTkButton(
            btn_box,
            text="تذكيري لاحقاً",
            width=110,
            fg_color="transparent",
            border_width=1,
            border_color=("#CBD5E1", "#4A3E2D"),
            text_color=("#64748B", "#D1A562"),
            command=self.destroy
        )
        self.btn_cancel.pack(side="left", padx=5)

        self.btn_update = ctk.CTkButton(
            btn_box,
            text="تحديث وتثبيت الآن ⚡",
            width=160,
            fg_color="#F59E0B",
            hover_color="#D97706",
            text_color="#18130C",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda: self.start_update(remote_info)
        )
        self.btn_update.pack(side="right", padx=5)

    def start_update(self, remote_info: Dict[str, Any]):
        self.btn_update.configure(state="disabled")
        self.btn_cancel.configure(state="disabled")
        self.progress_bar.pack(fill="x", padx=25, pady=(0, 10))
        self.progress_bar.start()

        def _on_progress(msg):
            self.after(0, lambda: self.status_label.configure(text=msg))

        def _on_finish(success, error=None):
            if not success:
                self.after(0, lambda: self.handle_failure(error))

        download_and_install_update(
            remote_info,
            progress_callback=_on_progress,
            finish_callback=_on_finish
        )

    def handle_failure(self, error):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_cancel.configure(state="normal", text="إغلاق")
        self.status_label.configure(text=f"فشل التحديث: {error or 'تعذر الاتصال'}", text_color="#EF4444")


class WhatsNewDialog(ctk.CTkToplevel):
    """نافذة منبثقة تظهر لمرة واحدة فقط بعد التحديث الناجح لاستعراض كافة المميزات الجديدة"""
    def __init__(self, parent, version: str, changelog: list):
        super().__init__(parent)
        self.title("🎉 مرحباً بك في الإصدار الجديد!")
        self.geometry("520x460")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # رأس النافذة
        top_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("#F1F5F9", "#18130C"))
        top_frame.pack(fill="x")

        ctk.CTkLabel(
            top_frame,
            text=f"✨ تم تحديث البرنامج بنجاح إلى الإصدار v{version}",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#F59E0B"
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            top_frame,
            text="إليك أهم الميزات والتحسينات المضافة في هذا الإصدار:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#475569", "#D1A562")
        ).pack(pady=(0, 12))

        # قائمة المميزات
        scroll_box = ctk.CTkScrollableFrame(self, height=240, fg_color=("#FFFFFF", "#1E1810"), corner_radius=8)
        scroll_box.pack(fill="both", expand=True, padx=20, pady=15)

        if changelog:
            for item in changelog:
                row = ctk.CTkFrame(scroll_box, fg_color="transparent")
                row.pack(fill="x", pady=6, anchor="e")

                ctk.CTkLabel(
                    row,
                    text=f"✅ {item}",
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color=("#1E293B", "#F8FAFC"),
                    wraplength=440,
                    justify="right"
                ).pack(side="right", padx=5)
        else:
            ctk.CTkLabel(
                scroll_box,
                text="تحسينات عامة على الأداء والمظهر.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=("#64748B", "#94A3B8")
            ).pack(pady=20)

        # زر التأكيد والبدء
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(0, 15))

        btn_start = ctk.CTkButton(
            btn_box,
            text="بدء العمل 🚀",
            height=36,
            fg_color="#F59E0B",
            hover_color="#D97706",
            text_color="#18130C",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.on_close
        )
        btn_start.pack(fill="x")

    def on_close(self):
        state = get_updater_state()
        state["pending_changelog"] = False
        save_updater_state(state)
        self.destroy()


def check_and_show_whats_new(parent_window):
    """التحقق مما إذا كان هناك إشعار 'ما الجديد' يحتاج للعرض لأول مرة بعد التحديث"""
    state = get_updater_state()
    if state.get("pending_changelog", False):
        version = state.get("last_seen_version", "2.2.0")
        changelog = state.get("changelog", [])
        if not changelog:
            local_info = get_local_version_info()
            changelog = local_info.get("changelog", [])

        WhatsNewDialog(parent_window, version, changelog)
