# -*- coding: utf-8 -*-
"""
BioTorg Pro - نظام الحضور والانصراف ومسير الرواتب الذكي
CustomTkinter Desktop Application
"""

import os
import sys
import datetime
import threading
from typing import Optional, List, Dict, Any
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from attendance_engine import AttendanceEngine, get_app_dir
import updater

# ضبط المظهر الافتراضي
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AttendanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # إعدادات النافذة الرئيسية مع دعم العمل على أي شاشة ومقاس
        self.title("BioTorg Pro - نظام الحضور والانصراف ومسير الرواتب الذكي")
        self.geometry("1240x800")
        self.minsize(750, 480)

        # تعيين أيقونة البرنامج الرسمية (BioTorg Pro Shield Icon)
        for ico_cand in [
            os.path.join(get_app_dir(), "app_icon.ico"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico"),
            os.path.join(get_app_dir(), "assets", "icon.ico")
        ]:
            if os.path.exists(ico_cand):
                try:
                    self.iconbitmap(ico_cand)
                    break
                except Exception:
                    pass

        # محرك التحجيم التلقائي الذكي (Responsive Auto-Scaling Engine)
        self._base_width = 1240.0
        self._base_height = 800.0
        self._current_scale = 1.0
        self._resize_job = None
        self._last_win_size = (0, 0)
        self._daily_base_cols = {}
        self._monthly_base_cols = {}
        self._hr_base_cols = {}
        self._raw_base_cols = {}

        # تهيئة محرك البيانات
        default_file = self.detect_default_file()
        self.engine = AttendanceEngine(default_file)

        # متغيرات الحالة
        self.selected_date: datetime.date = datetime.date.today()
        if self.engine.available_dates:
            self.selected_date = self.engine.available_dates[0]

        self.current_filter = "ALL"  # ALL, PRESENT, LATE, ABSENT, NO_CHECKOUT
        self.search_text = tk.StringVar()
        self.search_text.trace_add("write", lambda *args: self.apply_daily_filter())
        self.current_payroll_data = []
        self._selected_daily_enno: Optional[int] = None
        self._loaded_tabs = set()

        # بناء الواجهة
        self.setup_ui()

        # ربط حدث تحجيم النافذة للتكيف الديناميكي على أي مقاس
        self.bind("<Configure>", self._on_window_configure)

        # تحميل البيانات في الجداول
        if default_file:
            self.refresh_all_views()

    def detect_default_file(self) -> str:
        """البحث عن ملفات البصمة الافتراضية في المجلد الحالي"""
        base_dir = get_app_dir()
        agl = os.path.join(base_dir, "AGL_001.TXT")
        glg = os.path.join(base_dir, "GLG_001.TXT")
        if os.path.exists(agl):
            return agl
        if os.path.exists(glg):
            return glg
        return ""

    def setup_ui(self):
        # 1. شريط العنوان العلوي (Header) بنمط عنبري دافئ راقٍ
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("#FFFFFF", "#120E08"))
        self.header_frame.pack(side="top", fill="x")

        # العنوان الرئيسي
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="right", padx=15, pady=8)

        app_title = ctk.CTkLabel(
            title_box,
            text="BioTorg Pro",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#F59E0B"
        )
        app_title.pack(anchor="e")

        app_subtitle = ctk.CTkLabel(
            title_box,
            text="نظام الحضور والانصراف ومسير الرواتب الذكي",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("#64748B", "#D1A562")
        )
        app_subtitle.pack(anchor="e")

        app_dev = ctk.CTkLabel(
            title_box,
            text="حقوق التطوير والملكية: Ahmed TorGoman  |  Telegram: @torgoman0 ✈️",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#F59E0B"
        )
        app_dev.pack(anchor="e")

        # أدوات الملف والمظهر في الجانب الأيسر
        tools_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        tools_box.pack(side="left", padx=10, pady=8)

        # زر تبديل الثيم
        self.theme_btn = ctk.CTkButton(
            tools_box,
            text="☀️ / 🌙",
            width=45,
            command=self.toggle_theme,
            fg_color=("#E2E8F0", "#241808"),
            hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FBBF24"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E")
        )
        self.theme_btn.pack(side="left", padx=3)

        # أيقونة وزر المطور وحقوق الملكية
        self.btn_developer = ctk.CTkButton(
            tools_box,
            text="👑 Ahmed TorGoman",
            width=135,
            command=self.show_about_developer,
            fg_color=("#FEF3C7", "#241808"),
            hover_color=("#FDE68A", "#3D2A0E"),
            text_color=("#92400E", "#FBBF24"),
            border_width=1.5,
            border_color=("#F59E0B", "#D97706"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        )
        self.btn_developer.pack(side="left", padx=3)

        # زر دعم البرنامج والمطور (InstaPay QR)
        self.btn_support = ctk.CTkButton(
            tools_box,
            text="دعم البرنامج 💖",
            width=110,
            command=self.show_support_dialog,
            fg_color=("#FEF2F2", "#261317"),
            hover_color=("#FEE2E2", "#3D1A21"),
            text_color=("#DC2626", "#F87171"),
            border_width=1.5,
            border_color=("#EF4444", "#DC2626"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        )
        self.btn_support.pack(side="left", padx=3)

        # زر فحص وتنزيل التحديثات من GitHub
        self.btn_check_update = ctk.CTkButton(
            tools_box,
            text="التحديثات 🔄",
            width=95,
            command=self.manual_check_updates,
            fg_color=("#E2E8F0", "#241808"),
            hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FBBF24"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")
        )
        self.btn_check_update.pack(side="left", padx=3)

        # أزرار التبديل السريع للملفات
        self.btn_agl = ctk.CTkButton(
            tools_box,
            text="(AGL) الكامل السجل 📄",
            command=lambda: self.switch_to_known_file("AGL_001.TXT"),
            fg_color="#D97706",
            hover_color="#B45309",
            width=135
        )
        self.btn_agl.pack(side="left", padx=3)

        self.btn_glg = ctk.CTkButton(
            tools_box,
            text="(GLG) الحركات سجلات ⚡",
            command=lambda: self.switch_to_known_file("GLG_001.TXT"),
            fg_color=("#E2E8F0", "#241808"),
            hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FEF3C7"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E"),
            width=135
        )
        self.btn_glg.pack(side="left", padx=3)

        self.btn_open_file = ctk.CTkButton(
            tools_box,
            text="ملف استعراض 📂",
            command=self.choose_custom_file,
            fg_color="#10B981",
            hover_color="#059669",
            width=110
        )
        self.btn_open_file.pack(side="left", padx=3)

        self.btn_usb_sync = ctk.CTkButton(
            tools_box,
            text="USB من سحب 🔌",
            command=self.sync_from_usb,
            fg_color="#F59E0B",
            hover_color="#D97706",
            width=125
        )
        self.btn_usb_sync.pack(side="left", padx=3)

        # 4. شريط الحالة السفلي (Status Bar) - نثبته أولاً في أسفل النافذة حتى لا يختفي أبداً عند تصغير النافذة
        self.status_bar = ctk.CTkFrame(self, height=26, corner_radius=0, fg_color=("#F1F5F9", "#0C0A06"))
        self.status_bar.pack(side="bottom", fill="x")

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="جاهز",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("#64748B", "#D1A562")
        )
        self.status_label.pack(side="right", padx=15)

        self.dev_label = ctk.CTkLabel(
            self.status_bar,
            text="© برمجة وتطوير: Ahmed TorGoman  |  Telegram: @torgoman0 ✈️",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#F59E0B"
        )
        self.dev_label.pack(side="left", padx=20)

        self.file_info_label = ctk.CTkLabel(
            self.status_bar,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#10B981"
        )
        self.file_info_label.pack(side="left", padx=10)

        # 2. بطاقات الإحصائيات (KPI Cards) بنمط عنبري ملكي
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.pack(side="top", fill="x", padx=15, pady=(8, 3))

        self.kpi_cards = {}
        cards_info = [
            ("total", "إجمالي الموظفين", "0", "#818CF8"),       # Royal Indigo ملكي
            ("present", "الحاضرون اليوم", "0", "#10B981"),      # أخضر زمردي
            ("late", "المتأخرون", "0", "#F59E0B"),             # عنبري ذهبي متألق
            ("absent", "الغياب اليوم", "0", "#EF4444"),         # قرمزي مرجاني
            ("missing", "لم يسجل انصراف", "0", "#06B6D4")      # سماوي ناصع
        ]

        # ترتيب الأعمدة بالتساوي
        for i in range(5):
            self.kpi_frame.columnconfigure(i, weight=1)

        for col_idx, (key, label_text, default_val, color) in enumerate(cards_info):
            # تصميم بطاقة عنبرية أنيقة
            card = ctk.CTkFrame(
                self.kpi_frame,
                corner_radius=8,
                fg_color=("#F8FAFC", "#171005"),
                border_width=1.5,
                border_color=("#CBD5E1", "#3D2A0E")
            )
            card.grid(row=0, column=col_idx, padx=4, pady=2, sticky="nsew")

            val_label = ctk.CTkLabel(
                card,
                text=default_val,
                font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                text_color=color
            )
            val_label.pack(pady=(4, 0))

            lbl = ctk.CTkLabel(
                card,
                text=label_text,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=("#475569", "#FEF3C7")
            )
            lbl.pack(pady=(0, 4))

            self.kpi_cards[key] = val_label

        # 3. التبويبات الرئيسية (Tabview) بألوان عنبرية متناسقة - تتمدد لتملأ المساحة المتبقية
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=8,
            command=self.on_tab_changed,
            segmented_button_selected_color="#D97706",
            segmented_button_selected_hover_color="#B45309",
            segmented_button_unselected_color=("#E2E8F0", "#241808"),
            segmented_button_unselected_hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB")
        )
        self.tabview.pack(side="top", fill="both", expand=True, padx=12, pady=(2, 4))

        self.tab_daily = self.tabview.add("اليومي التقرير 📅")
        self.tab_monthly = self.tabview.add("والشهري الدوري الملخص 📊")
        self.tab_hr = self.tabview.add("HR والـ الرواتب 💼")
        self.tab_raw = self.tabview.add("الخام الحركات سجل 🔍")
        self.tab_settings = self.tabview.add("والورديات العمل إعدادات ⚙️")

        # إعداد محتويات كل تبويب
        self.setup_daily_tab()
        self.setup_monthly_tab()
        self.setup_hr_tab()
        self.setup_raw_tab()
        self.setup_settings_tab()

    def setup_daily_tab(self):
        """إعداد تبويب التقرير اليومي"""
        controls_frame = ctk.CTkFrame(self.tab_daily, fg_color="transparent")
        controls_frame.pack(fill="x", padx=10, pady=(5, 10))

        # الجانب الأيمن: اختيار التاريخ والتحكم
        right_box = ctk.CTkFrame(controls_frame, fg_color="transparent")
        right_box.pack(side="right", fill="x")

        lbl_date = ctk.CTkLabel(right_box, text="تاريخ اليوم:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_date.pack(side="right", padx=(5, 0))

        self.date_combobox = ctk.CTkComboBox(
            right_box,
            values=["--"],
            command=self.on_date_changed,
            width=140
        )
        self.date_combobox.pack(side="right", padx=5)

        self.btn_prev_day = ctk.CTkButton(
            right_box,
            text="◀ السابق",
            width=65,
            command=self.go_prev_day,
            fg_color=("#E2E8F0", "#241808"),
            hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FBBF24"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E")
        )
        self.btn_prev_day.pack(side="right", padx=2)

        self.btn_next_day = ctk.CTkButton(
            right_box,
            text="التالي ▶",
            width=65,
            command=self.go_next_day,
            fg_color=("#E2E8F0", "#241808"),
            hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FBBF24"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E")
        )
        self.btn_next_day.pack(side="right", padx=2)

        self.btn_latest_day = ctk.CTkButton(
            right_box,
            text="يوم أحدث 📌",
            width=80,
            command=self.go_latest_day,
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="#FFFFFF"
        )
        self.btn_latest_day.pack(side="right", padx=5)

        # الجانب الأيسر: زر التصدير والبحث
        left_box = ctk.CTkFrame(controls_frame, fg_color="transparent")
        left_box.pack(side="left")

        self.btn_export_daily = ctk.CTkButton(
            left_box,
            text="Excel إلى تصدير 📊",
            command=self.export_daily_excel,
            fg_color="#15803D",
            hover_color="#166534",
            width=140
        )
        self.btn_export_daily.pack(side="left", padx=5)

        self.btn_daily_ledger = ctk.CTkButton(
            left_box,
            text="الموظف كارت 👤",
            command=self.open_ledger_from_daily,
            fg_color="#F59E0B",
            hover_color="#D97706",
            text_color="#FFFFFF",
            width=125
        )
        self.btn_daily_ledger.pack(side="left", padx=5)

        search_entry = ctk.CTkEntry(
            left_box,
            textvariable=self.search_text,
            placeholder_text="🔍 بحث باسم الموظف أو الكود...",
            fg_color=("#FFFFFF", "#171005"),
            border_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            placeholder_text_color=("#94A3B8", "#78664D"),
            width=220
        )
        search_entry.pack(side="left", padx=5)

        # شريط أزرار الفلترة السريعة بنمط عنبري متألق
        filters_frame = ctk.CTkFrame(self.tab_daily, fg_color="transparent")
        filters_frame.pack(fill="x", padx=10, pady=(0, 10))

        lbl_filters = ctk.CTkLabel(filters_frame, text="تصفية العرض:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_filters.pack(side="right", padx=5)

        self.filter_buttons = {}
        filters_def = [
            ("ALL", "الكل عرض", "#D97706"),
            ("PRESENT", "فقط الحاضرون ✅", "#10B981"),
            ("LATE", "فقط المتأخرون ⏰", "#F59E0B"),
            ("ABSENT", "فقط الغياب ❌", "#EF4444"),
            ("NO_CHECKOUT", "انصراف بدون ⚠️", "#06B6D4")
        ]

        for f_key, f_label, color in filters_def:
            btn = ctk.CTkButton(
                filters_frame,
                text=f_label,
                width=115,
                height=28,
                fg_color=color if f_key == "ALL" else ("#E2E8F0", "#241808"),
                hover_color="#B45309" if f_key == "ALL" else ("#CBD5E1", "#3D2A0E"),
                text_color="#FFFFFF" if f_key == "ALL" else ("#0F172A", "#FEF3C7"),
                border_width=1,
                border_color=("#CBD5E1", "#3D2A0E"),
                command=lambda k=f_key: self.set_daily_filter(k)
            )
            btn.pack(side="right", padx=3)
            self.filter_buttons[f_key] = btn

        # 1. لوحة تعديل حالة وظروف الموظف المباشرة - تُثبَّت أولاً في أسفل التبويب حتى لا تُحجب أبداً عند تصغير النافذة
        self.setup_daily_edit_panel()

        # 2. جدول التقرير اليومي - يملأ المساحة المركزية بمرونة كاملة
        table_container = ctk.CTkFrame(self.tab_daily, corner_radius=8, fg_color=("#F8FAFC", "#171005"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"))
        table_container.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 4))

        cols = ("idx", "enno", "name", "condition", "status", "checkin", "checkout", "late", "early", "work_hours", "notes")
        self.daily_tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")

        headers_map = {
            "idx": ("م", 35, "center"),
            "enno": ("كود", 45, "center"),
            "name": ("اسم الموظف", 140, "w"),
            "condition": ("📝 بيان الظروف / التصريح (قابل للتعديل)", 185, "w"),
            "status": ("الحالة", 130, "center"),
            "checkin": ("وقت الحضور", 90, "center"),
            "checkout": ("وقت الانصراف", 90, "center"),
            "late": ("التأخير (د)", 75, "center"),
            "early": ("انصراف مبكر", 75, "center"),
            "work_hours": ("ساعات العمل", 85, "center"),
            "notes": ("ملاحظات النظام", 160, "w")
        }
        self._daily_base_cols = headers_map

        for c_id, (c_name, c_width, c_align) in headers_map.items():
            self.daily_tree.heading(c_id, text=c_name)
            self.daily_tree.column(c_id, width=c_width, anchor=c_align)

        # ربط أحداث النقر والتحديد
        self.daily_tree.bind("<<TreeviewSelect>>", self.on_daily_tree_selected)
        self.daily_tree.bind("<Double-1>", self.on_daily_tree_double_click)

        # أشرطة التمرير
        v_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.daily_tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.daily_tree.xview)
        self.daily_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.daily_tree.pack(fill="both", expand=True)

        self.apply_tree_styles(self.daily_tree)

    def setup_daily_edit_panel(self):
        """لوحة سريعة ومباشرة لتعديل ظرف أو تصريح الموظف وتحديد حضوره أو غيابه"""
        self.edit_panel = ctk.CTkFrame(
            self.tab_daily,
            corner_radius=10,
            fg_color=("#F8FAFC", "#171005"),
            border_width=1.5,
            border_color=("#CBD5E1", "#3D2A0E")
        )
        self.edit_panel.pack(side="bottom", fill="x", padx=10, pady=(2, 6))

        # السطر الأول: بيانات الموظف المختار وأزرار الحضور والغياب
        row1 = ctk.CTkFrame(self.edit_panel, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(8, 4))

        self.lbl_daily_sel_emp = ctk.CTkLabel(
            row1,
            text="👈 اضغط على أي موظف في الجدول أعلاه لتعديل حالته أو كتابة ظرفه (تصريح / معاينة)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#F59E0B"
        )
        self.lbl_daily_sel_emp.pack(side="right", padx=5)

        # أزرار تحديد الحالة بنمط عنبري
        self.seg_daily_status = ctk.CTkSegmentedButton(
            row1,
            values=["⚙️ تلقائي (بصمة)", "🟢 حاضر (معتمد)", "🔴 غائب"],
            command=self.on_daily_status_seg_changed,
            selected_color="#D97706",
            selected_hover_color="#B45309",
            unselected_color=("#E2E8F0", "#241808"),
            unselected_hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=280
        )
        self.seg_daily_status.set("⚙️ تلقائي (بصمة)")
        self.seg_daily_status.pack(side="left", padx=5)

        lbl_status_prompt = ctk.CTkLabel(
            row1,
            text="تعديل الحالة:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#1E293B", "#FEF3C7")
        )
        lbl_status_prompt.pack(side="left", padx=(10, 2))

        # السطر الثاني: إدخال بيان الظروف والأزرار السريعة وزر الحفظ
        row2 = ctk.CTkFrame(self.edit_panel, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(4, 8))

        lbl_cond = ctk.CTkLabel(
            row2,
            text="📝 بيان الظروف / التصريح:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#1E293B", "#FEF3C7")
        )
        lbl_cond.pack(side="right", padx=(5, 5))

        self.entry_daily_condition = ctk.CTkEntry(
            row2,
            placeholder_text="اكتب هنا مثلاً: أخذ تصريح انصراف مبكر / نزل معاينة موقع / مأمورية خارجية...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=("#FFFFFF", "#1F160A"),
            border_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            placeholder_text_color=("#94A3B8", "#78664D"),
            height=34
        )
        self.entry_daily_condition.pack(side="right", padx=5, fill="x", expand=True)
        self.entry_daily_condition.bind("<Return>", lambda e: self.save_selected_daily_adjustment())

        # أزرار سريعة للاختيار والتطبيق المباشر
        quick_frame = ctk.CTkFrame(row2, fg_color="transparent")
        quick_frame.pack(side="right", padx=5)

        quick_reasons = [
            ("🚗 نزل معاينة", "نزل معاينة موقع", "🟢 حاضر (معتمد)"),
            ("📝 أخذ تصريح", "أخذ تصريح معتمد", "🟢 حاضر (معتمد)"),
            ("💼 مأمورية", "مأمورية عمل خارجية", "🟢 حاضر (معتمد)"),
            ("⏱️ إذن مبكر", "إذن انصراف مبكر", "🟢 حاضر (معتمد)"),
            ("🏖️ إجازة عارضة", "إجازة عارضة", "🔴 غائب"),
            ("🏥 عذر مرضي", "عذر مرضي معتمد", "🔴 غائب")
        ]

        for q_label, q_text, q_status in quick_reasons:
            btn_q = ctk.CTkButton(
                quick_frame,
                text=q_label,
                width=74,
                height=30,
                fg_color=("#E2E8F0", "#241808"),
                hover_color=("#CBD5E1", "#3D2A0E"),
                text_color=("#0F172A", "#FEF3C7"),
                border_width=1,
                border_color=("#CBD5E1", "#3D2A0E"),
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                command=lambda t=q_text, s=q_status: self.set_quick_reason(t, s)
            )
            btn_q.pack(side="right", padx=2)

        # زر الحفظ المباشر
        self.btn_save_daily_adj = ctk.CTkButton(
            row2,
            text="التعديل حفظ 💾",
            command=self.save_selected_daily_adjustment,
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            width=115,
            height=34
        )
        self.btn_save_daily_adj.pack(side="left", padx=5)

        self.btn_clear_daily_adj = ctk.CTkButton(
            row2,
            text="الأصل استعادة 🔄",
            command=self.clear_selected_daily_adjustment,
            fg_color=("#94A3B8", "#241808"),
            hover_color=("#64748B", "#3D2A0E"),
            text_color=("#0F172A", "#FEF3C7"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=95,
            height=32
        )
        self.btn_clear_daily_adj.pack(side="left", padx=5)

    def setup_monthly_tab(self):
        """إعداد تبويب التقرير الدوري والشهري"""
        controls_frame = ctk.CTkFrame(self.tab_monthly, fg_color="transparent")
        controls_frame.pack(fill="x", padx=10, pady=10)

        right_box = ctk.CTkFrame(controls_frame, fg_color="transparent")
        right_box.pack(side="right")

        lbl_from = ctk.CTkLabel(right_box, text="من تاريخ:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_from.pack(side="right", padx=(5, 0))

        self.combo_from_date = ctk.CTkComboBox(right_box, values=["--"], width=130)
        self.combo_from_date.pack(side="right", padx=5)

        lbl_to = ctk.CTkLabel(right_box, text="إلى تاريخ:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_to.pack(side="right", padx=(10, 0))

        self.combo_to_date = ctk.CTkComboBox(right_box, values=["--"], width=130)
        self.combo_to_date.pack(side="right", padx=5)

        btn_calc_period = ctk.CTkButton(
            right_box,
            text="الدوري الملخص تحديث 🔄",
            command=self.update_period_view,
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="#FFFFFF",
            width=150
        )
        btn_calc_period.pack(side="right", padx=10)

        # زر التصدير
        left_box = ctk.CTkFrame(controls_frame, fg_color="transparent")
        left_box.pack(side="left")

        btn_export_period = ctk.CTkButton(
            left_box,
            text="Excel إلى الملخص تصدير 📊",
            command=self.export_period_excel,
            fg_color="#15803D",
            hover_color="#166534",
            width=180
        )
        btn_export_period.pack(side="left", padx=5)

        self.btn_monthly_ledger = ctk.CTkButton(
            left_box,
            text="الموظف كارت 👤",
            command=self.open_ledger_from_monthly,
            fg_color="#F59E0B",
            hover_color="#D97706",
            text_color="#FFFFFF",
            width=130
        )
        self.btn_monthly_ledger.pack(side="left", padx=5)

        # جدول الملخص الدوري
        table_container = ctk.CTkFrame(self.tab_monthly, corner_radius=8, fg_color=("#F8FAFC", "#171005"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"))
        table_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("idx", "enno", "name", "work_days", "present_days", "absent_days", "late_days", "late_mins", "perm_hours", "perm_penalty", "missing_checkout", "total_hours", "attendance_pct")
        self.monthly_tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")

        headers_map = {
            "idx": ("م", 35, "center"),
            "enno": ("كود", 45, "center"),
            "name": ("اسم الموظف", 145, "w"),
            "work_days": ("أيام العمل", 75, "center"),
            "present_days": ("الحضور", 70, "center"),
            "absent_days": ("الغياب", 70, "center"),
            "late_days": ("مرات التأخير", 75, "center"),
            "late_mins": ("التأخير (د)", 75, "center"),
            "perm_hours": ("ساعات الإذن", 85, "center"),
            "perm_penalty": ("خصم الإذن", 85, "center"),
            "missing_checkout": ("بدون انصراف", 85, "center"),
            "total_hours": ("ساعات العمل", 95, "center"),
            "attendance_pct": ("الالتزام (%)", 85, "center")
        }
        self._monthly_base_cols = headers_map

        for c_id, (c_name, c_width, c_align) in headers_map.items():
            self.monthly_tree.heading(c_id, text=c_name)
            self.monthly_tree.column(c_id, width=c_width, anchor=c_align)

        # ربط النقر المزدوج لفتح كارت الموظف
        self.monthly_tree.bind("<Double-1>", lambda event: self.open_ledger_from_monthly())

        v_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.monthly_tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.monthly_tree.xview)
        self.monthly_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.monthly_tree.pack(fill="both", expand=True)

        self.apply_tree_styles(self.monthly_tree)

    # ==================== تبويب إدارة الرواتب وشؤون الموظفين (HR & Payroll) ====================

    def setup_hr_tab(self):
        """إعداد تبويب إدارة الرواتب وشؤون الموظفين (HR & Payroll)"""
        # 1. شريط التحكم العلوي
        header_frame = ctk.CTkFrame(self.tab_hr, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        # مفتاح تفعيل/إلغاء تفعيل الموديول
        hr_cfg = self.engine.get_hr_settings()
        self.var_hr_enabled = ctk.BooleanVar(value=hr_cfg.get("enabled", False))

        toggle_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        toggle_box.pack(side="right")

        self.switch_hr = ctk.CTkSwitch(
            toggle_box,
            text="تفعيل موديول إدارة الرواتب والـ HR",
            variable=self.var_hr_enabled,
            command=self.on_hr_toggle_changed,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            progress_color="#F59E0B"
        )
        self.switch_hr.pack(side="right", padx=10)

        # عناصر تحكم التاريخ واحتساب الرواتب
        self.hr_actions_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.hr_actions_box.pack(side="left")

        self.btn_export_hr = ctk.CTkButton(
            self.hr_actions_box,
            text="(Excel) الرواتب مسير تصدير 📥",
            command=self.export_payroll_excel,
            fg_color="#15803D",
            hover_color="#166534",
            width=180
        )
        self.btn_export_hr.pack(side="left", padx=5)

        self.btn_calc_hr = ctk.CTkButton(
            self.hr_actions_box,
            text="الرواتب مسير احتساب ⚡",
            command=self.update_hr_view,
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="#FFFFFF",
            width=150
        )
        self.btn_calc_hr.pack(side="left", padx=5)

        self.combo_hr_to = ctk.CTkComboBox(self.hr_actions_box, values=["--"], width=130)
        self.combo_hr_to.pack(side="left", padx=4)

        lbl_to = ctk.CTkLabel(self.hr_actions_box, text="إلى:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_to.pack(side="left", padx=2)

        self.combo_hr_from = ctk.CTkComboBox(self.hr_actions_box, values=["--"], width=130)
        self.combo_hr_from.pack(side="left", padx=4)

        lbl_from = ctk.CTkLabel(self.hr_actions_box, text="من:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_from.pack(side="left", padx=2)

        # حاوية المحتوى الرئيسي للتبويب
        self.hr_main_container = ctk.CTkFrame(self.tab_hr, fg_color="transparent")
        self.hr_main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # شاشة الموديول غير المفعّل (Disabled Banner)
        self.hr_disabled_frame = ctk.CTkFrame(self.hr_main_container, corner_radius=12, fg_color=("#F8FAFC", "#171005"), border_width=1.5, border_color=("#CBD5E1", "#3D2A0E"))

        lbl_dis_icon = ctk.CTkLabel(self.hr_disabled_frame, text="🔒", font=ctk.CTkFont(size=46))
        lbl_dis_icon.pack(pady=(35, 10))

        lbl_dis_title = ctk.CTkLabel(
            self.hr_disabled_frame,
            text="موديول إدارة الرواتب وشؤون الموظفين (HR & Payroll) غير مفعّل",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#F59E0B"
        )
        lbl_dis_title.pack(pady=5)

        lbl_dis_desc = ctk.CTkLabel(
            self.hr_disabled_frame,
            text="هذه الميزة اختيارية ومستقلة. عند تفعيلها يمكنك:\n"
                 "• تحديد الراتب الأساسي والبدلات الشهرية والمكافآت والسلف والمسمى الوظيفي لكل موظف.\n"
                 "• تحديد نسبة خصم أيام الغياب (يوم بيوم، 1.5 يوم، أو يومين جزاء).\n"
                 "• تحديد طريقة حساب خصم التأخير والانصراف المبكر (بالدقائق أو بنظام الشرائح).\n"
                 "• احتساب صافي المستحق لكل موظف وتصدير مسير رواتب شهري متكامل في Excel.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=("#64748B", "#D1A562"),
            justify="right"
        )
        lbl_dis_desc.pack(pady=15, padx=30)

        btn_enable_now = ctk.CTkButton(
            self.hr_disabled_frame,
            text="الآن HR والـ الرواتب موديول تفعيل 🚀",
            command=self.activate_hr_module,
            fg_color="#D97706",
            hover_color="#B45309",
            height=42,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        btn_enable_now.pack(pady=(10, 35))

        # شاشة الموديول المفعّل (Enabled View)
        self.hr_enabled_frame = ctk.CTkFrame(self.hr_main_container, fg_color="transparent")

        # أ) بطاقات المؤشرات المالية KPI
        self.hr_kpi_frame = ctk.CTkFrame(self.hr_enabled_frame, fg_color="transparent")
        self.hr_kpi_frame.pack(fill="x", pady=(0, 10))

        for i in range(4):
            self.hr_kpi_frame.columnconfigure(i, weight=1)

        kpis_data = [
            ("basic", "إجمالي الرواتب الأساسية", "0.00 ج.م", "#818CF8"),
            ("additions", "إجمالي البدلات والإضافي (+)", "0.00 ج.م", "#10B981"),
            ("deductions", "إجمالي الخصومات والجزاءات (-)", "0.00 ج.م", "#EF4444"),
            ("net", "صافي المستحق المطلوب صرفه", "0.00 ج.م", "#F59E0B")
        ]

        self.hr_kpi_labels = {}
        for col_i, (k_id, k_title, k_def, k_col) in enumerate(kpis_data):
            c_card = ctk.CTkFrame(
                self.hr_kpi_frame,
                corner_radius=10,
                fg_color=("#F8FAFC", "#171005"),
                border_width=1.5,
                border_color=("#CBD5E1", "#3D2A0E")
            )
            c_card.grid(row=0, column=col_i, padx=5, pady=2, sticky="nsew")

            val_l = ctk.CTkLabel(c_card, text=k_def, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=k_col)
            val_l.pack(pady=(6, 0))

            tit_l = ctk.CTkLabel(c_card, text=k_title, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#475569", "#FEF3C7"))
            tit_l.pack(pady=(0, 6))

            self.hr_kpi_labels[k_id] = val_l

        # ب) شريط أدوات الجدول والإدارة
        toolbar = ctk.CTkFrame(self.hr_enabled_frame, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))

        btn_edit_emp = ctk.CTkButton(
            toolbar,
            text="المحدد الموظف راتب تعديل ✏️",
            command=self.open_edit_selected_emp_dialog,
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            width=200
        )
        btn_edit_emp.pack(side="right", padx=5)

        btn_policies = ctk.CTkButton(
            toolbar,
            text="والبدلات الخصم سياسات ⚙️",
            command=self.open_hr_policies_dialog,
            fg_color=("#E2E8F0", "#241808"),
            hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FEF3C7"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E"),
            width=170
        )
        btn_policies.pack(side="right", padx=5)

        lbl_hint = ctk.CTkLabel(
            toolbar,
            text="💡 انقر نقراً مزدوجاً على أي موظف لتعديل راتبه وبدلاته فوراً",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748B", "#D1A562")
        )
        lbl_hint.pack(side="right", padx=10)

        # حقل البحث
        self.hr_search_var = tk.StringVar()
        self.hr_search_var.trace_add("write", lambda *args: self.filter_hr_table())
        entry_search_hr = ctk.CTkEntry(
            toolbar,
            textvariable=self.hr_search_var,
            placeholder_text="🔍 بحث بالاسم أو الكود أو الوظيفة...",
            fg_color=("#FFFFFF", "#171005"),
            border_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            placeholder_text_color=("#94A3B8", "#78664D"),
            width=220
        )
        entry_search_hr.pack(side="left", padx=5)

        # ج) جدول مسير الرواتب
        table_container = ctk.CTkFrame(self.hr_enabled_frame, corner_radius=8, fg_color=("#F8FAFC", "#171005"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"))
        table_container.pack(fill="both", expand=True)

        cols = ("idx", "enno", "name", "job_title", "basic", "present", "absent", "abs_ded", "late_mins", "late_ded", "other_ded", "additions", "net")
        self.hr_tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")

        headers_map = {
            "idx": ("م", 35, "center"),
            "enno": ("كود", 45, "center"),
            "name": ("اسم الموظف", 140, "w"),
            "job_title": ("المسمى الوظيفي", 110, "center"),
            "basic": ("الراتب الأساسي", 95, "center"),
            "present": ("حضور", 55, "center"),
            "absent": ("غياب", 55, "center"),
            "abs_ded": ("خصم الغياب", 85, "center"),
            "late_mins": ("تأخير (د)", 65, "center"),
            "late_ded": ("خصم التأخير", 85, "center"),
            "other_ded": ("سلف/خصم", 80, "center"),
            "additions": ("بدلات وإضافي", 90, "center"),
            "net": ("صافي الراتب المستحق", 120, "center")
        }
        self._hr_base_cols = headers_map

        for c_id, (c_name, c_width, c_align) in headers_map.items():
            self.hr_tree.heading(c_id, text=c_name)
            self.hr_tree.column(c_id, width=c_width, anchor=c_align)

        # ربط النقر المزدوج لفتح شاشة التعديل
        self.hr_tree.bind("<Double-1>", lambda event: self.open_edit_selected_emp_dialog())

        v_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.hr_tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.hr_tree.xview)
        self.hr_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.hr_tree.pack(fill="both", expand=True)

        self.apply_tree_styles(self.hr_tree)
        self.refresh_hr_state_display()

    def activate_hr_module(self):
        """تفعيل موديول الرواتب بالزر"""
        self.var_hr_enabled.set(True)
        self.on_hr_toggle_changed()

    def on_hr_toggle_changed(self):
        """التبديل بين تفعيل وتعطيل موديول الـ HR"""
        is_enabled = self.var_hr_enabled.get()
        self.engine.save_hr_settings({"enabled": is_enabled})
        self.refresh_hr_state_display()
        if is_enabled:
            self.update_hr_view()

    def refresh_hr_state_display(self):
        """تحديث شكل الواجهة طبقاً لحالة التفعيل"""
        is_enabled = self.var_hr_enabled.get()
        if is_enabled:
            self.hr_disabled_frame.pack_forget()
            self.hr_enabled_frame.pack(fill="both", expand=True)
            self.btn_calc_hr.configure(state="normal")
            self.btn_export_hr.configure(state="normal")
        else:
            self.hr_enabled_frame.pack_forget()
            self.hr_disabled_frame.pack(fill="both", expand=True, pady=30, padx=40)
            self.btn_calc_hr.configure(state="disabled")
            self.btn_export_hr.configure(state="disabled")

    def update_hr_view(self):
        """احتساب مسير الرواتب وعرض البيانات في الجدول وبطاقات الـ KPI بخيط عمل خلفي سريع دون أي تجميد"""
        if not getattr(self, "var_hr_enabled", None) or not self.var_hr_enabled.get():
            return

        try:
            start_d = datetime.datetime.strptime(self.combo_hr_from.get(), "%Y-%m-%d").date()
            end_d = datetime.datetime.strptime(self.combo_hr_to.get(), "%Y-%m-%d").date()
        except Exception:
            return

        if start_d > end_d:
            messagebox.showwarning("تنبيه", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")
            return

        if hasattr(self, "btn_calc_hr"):
            self.btn_calc_hr.configure(state="disabled", text="جاري الاحتساب... ⏳")

        def _worker():
            try:
                data = self.engine.calculate_monthly_payroll(start_d, end_d)
            except Exception as e:
                print("Error calculating payroll:", e)
                data = []
            self.after(0, lambda: self._apply_payroll_results(data))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_payroll_results(self, data):
        """تطبيق نتائج مسير الرواتب وتحديث الجداول والبطاقات في الواجهة"""
        if hasattr(self, "btn_calc_hr"):
            self.btn_calc_hr.configure(state="normal", text="الرواتب مسير احتساب ⚡")

        self.current_payroll_data = data

        # تحديث بطاقات الـ KPI
        tot_basic = sum(r["basic_salary"] for r in self.current_payroll_data)
        tot_add = sum(r["total_additions"] for r in self.current_payroll_data)
        tot_ded = sum(r["total_deductions"] for r in self.current_payroll_data)
        tot_net = sum(r["net_salary"] for r in self.current_payroll_data)

        if hasattr(self, "hr_kpi_labels") and "basic" in self.hr_kpi_labels:
            self.hr_kpi_labels["basic"].configure(text=f"{tot_basic:,.2f} ج.م")
            self.hr_kpi_labels["additions"].configure(text=f"{tot_add:,.2f} ج.م")
            self.hr_kpi_labels["deductions"].configure(text=f"{tot_ded:,.2f} ج.م")
            self.hr_kpi_labels["net"].configure(text=f"{tot_net:,.2f} ج.م")

        self.filter_hr_table()

    def filter_hr_table(self):
        """تطبيق البحث النصي على جدول مسير الرواتب"""
        if not hasattr(self, "hr_tree") or not hasattr(self, "current_payroll_data"):
            return

        for item in self.hr_tree.get_children():
            self.hr_tree.delete(item)

        q = self.hr_search_var.get().strip().lower()

        filtered = []
        for r in self.current_payroll_data:
            if q:
                match_id = q in str(r["enno"])
                match_name = q in r["name"].lower()
                match_title = q in (r["job_title"] or "").lower()
                if not (match_id or match_name or match_title):
                    continue
            filtered.append(r)

        for idx, r in enumerate(filtered, 1):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.hr_tree.insert(
                "",
                "end",
                values=(
                    idx,
                    r["enno"],
                    r["name"],
                    r["job_title"] or "-",
                    f"{r['basic_salary']:,.2f}",
                    r["days_present"],
                    r["days_absent"],
                    f"{r['absence_deduction']:,.2f}",
                    r["total_late_minutes"],
                    f"{(r['late_deduction'] + r['early_leave_deduction']):,.2f}",
                    f"{r['other_deductions']:,.2f}",
                    f"{r['total_additions']:,.2f}",
                    f"{r['net_salary']:,.2f}"
                ),
                tags=(tag,)
            )

    def open_edit_selected_emp_dialog(self):
        """نافذة تعديل راتب وبدلات ومسمى الموظف"""
        selected = self.hr_tree.selection()
        if not selected:
            children = self.hr_tree.get_children()
            if not children:
                messagebox.showwarning("تنبيه", "لا توجد بيانات موظفين لعرضها.")
                return
            selected = [children[0]]
            self.hr_tree.selection_set(selected[0])

        vals = self.hr_tree.item(selected[0], "values")
        enno = int(vals[1])
        emp_name = vals[2]
        emp_hr = self.engine.get_employee_hr(enno)

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"تعديل راتب وبيانات: {emp_name} (كود {enno})")
        dialog.geometry("500x520")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        head_box = ctk.CTkFrame(dialog, corner_radius=0, fg_color=("#FFFFFF", "#120E08"))
        head_box.pack(fill="x")
        ctk.CTkLabel(head_box, text=f"بيانات الموظف المالية - {emp_name}", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#F59E0B").pack(pady=(12, 2))
        ctk.CTkLabel(head_box, text=f"كود البصمة: {enno}", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=("#64748B", "#D1A562")).pack(pady=(0, 10))

        content_box = ctk.CTkFrame(dialog, fg_color="transparent")
        content_box.pack(fill="both", expand=True, padx=25, pady=15)

        # 1. المسمى الوظيفي
        row_title = ctk.CTkFrame(content_box, fg_color="transparent")
        row_title.pack(fill="x", pady=6)
        ctk.CTkLabel(row_title, text="المسمى الوظيفي:", width=140, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="right", padx=5)
        entry_title = ctk.CTkEntry(row_title, width=220, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_title.insert(0, emp_hr.get("job_title", ""))
        entry_title.pack(side="right", padx=5)

        # 2. الراتب الأساسي
        row_salary = ctk.CTkFrame(content_box, fg_color="transparent")
        row_salary.pack(fill="x", pady=6)
        ctk.CTkLabel(row_salary, text="الراتب الأساسي (ج.م):", width=140, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="right", padx=5)
        entry_salary = ctk.CTkEntry(row_salary, width=220, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_salary.insert(0, str(emp_hr.get("basic_salary", 0.0)))
        entry_salary.pack(side="right", padx=5)

        # 3. البدلات الشهرية الثابتة
        row_allow = ctk.CTkFrame(content_box, fg_color="transparent")
        row_allow.pack(fill="x", pady=6)
        ctk.CTkLabel(row_allow, text="بدلات شهرية ثابتة (ج.م):", width=140, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right", padx=5)
        entry_allow = ctk.CTkEntry(row_allow, width=220, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_allow.insert(0, str(emp_hr.get("allowances", 0.0)))
        entry_allow.pack(side="right", padx=5)

        # 4. المكافآت والحوافز
        row_bonus = ctk.CTkFrame(content_box, fg_color="transparent")
        row_bonus.pack(fill="x", pady=6)
        ctk.CTkLabel(row_bonus, text="مكافآت وحوافز (ج.م):", width=140, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right", padx=5)
        entry_bonus = ctk.CTkEntry(row_bonus, width=220, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_bonus.insert(0, str(emp_hr.get("bonuses", 0.0)))
        entry_bonus.pack(side="right", padx=5)

        # 5. السلف والخصومات الإدارية
        row_ded = ctk.CTkFrame(content_box, fg_color="transparent")
        row_ded.pack(fill="x", pady=6)
        ctk.CTkLabel(row_ded, text="سلف / خصومات أخرى (ج.م):", width=140, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right", padx=5)
        entry_ded = ctk.CTkEntry(row_ded, width=220, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_ded.insert(0, str(emp_hr.get("deductions", 0.0)))
        entry_ded.pack(side="right", padx=5)

        # شريط معاينة المعدلات
        rate_box = ctk.CTkFrame(content_box, corner_radius=8, fg_color=("#F1F5F9", "#1F160A"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"))
        rate_box.pack(fill="x", pady=12)
        lbl_rates = ctk.CTkLabel(rate_box, text="حساب الأجر اليومي والساعي...", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#F59E0B")
        lbl_rates.pack(pady=8)

        def update_rates(*args):
            try:
                s = float(entry_salary.get().strip() or "0")
                d_rate = s / 30.0
                h_rate = d_rate / 7.0
                lbl_rates.configure(text=f"أجر اليوم التقريبي: {d_rate:.2f} ج.م  |  أجر الساعة: {h_rate:.2f} ج.م")
            except Exception:
                lbl_rates.configure(text="يرجى إدخال أرقام صحيحة للراتب")

        entry_salary.bind("<KeyRelease>", update_rates)
        update_rates()

        # أزرار الحفظ والإلغاء
        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=25, pady=(5, 20))

        def on_save():
            try:
                sal = float(entry_salary.get().strip())
                alw = float(entry_allow.get().strip())
                bon = float(entry_bonus.get().strip())
                ded = float(entry_ded.get().strip())
                title = entry_title.get().strip()

                if sal < 0 or alw < 0 or bon < 0 or ded < 0:
                    messagebox.showerror("خطأ", "لا يمكن إدخال قيم سالبة.")
                    return

                new_data = {
                    "job_title": title,
                    "basic_salary": sal,
                    "allowances": alw,
                    "bonuses": bon,
                    "deductions": ded
                }
                self.engine.save_employee_hr(enno, new_data)
                dialog.destroy()
                self.update_hr_view()
                messagebox.showinfo("تم الحفظ", f"تم تحديث بيانات وراتب الموظف {emp_name} بنجاح.")
            except ValueError:
                messagebox.showerror("خطأ", "يرجى التأكد من كتابة الأرقام بشكل صحيح.")

        btn_save = ctk.CTkButton(btn_box, text="حفظ التعديلات 💾", command=on_save, fg_color="#D97706", hover_color="#B45309", width=160, height=36, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        btn_save.pack(side="right", padx=5)

        btn_cancel = ctk.CTkButton(btn_box, text="إلغاء", command=dialog.destroy, fg_color=("#94A3B8", "#241808"), hover_color=("#64748B", "#3D2A0E"), text_color=("#0F172A", "#FEF3C7"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"), width=90, height=36)
        btn_cancel.pack(side="left", padx=5)

    def open_hr_policies_dialog(self):
        """نافذة إعدادات سياسات الرواتب ونسب الخصم للغياب والتأخير"""
        hr_cfg = self.engine.get_hr_settings()

        dialog = ctk.CTkToplevel(self)
        dialog.title("قواعد وسياسات احتساب الرواتب والخصومات")
        dialog.geometry("540x530")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        head_box = ctk.CTkFrame(dialog, corner_radius=0, fg_color=("#FFFFFF", "#120E08"))
        head_box.pack(fill="x")
        ctk.CTkLabel(head_box, text="سياسات الـ HR والخصومات المعتمدة", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#F59E0B").pack(pady=(12, 2))
        ctk.CTkLabel(head_box, text="تحديد نسب خصم الغياب والتأخير ومعدلات أجر الساعات", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=("#64748B", "#D1A562")).pack(pady=(0, 10))

        content_box = ctk.CTkFrame(dialog, fg_color="transparent")
        content_box.pack(fill="both", expand=True, padx=25, pady=15)

        # 1. معامل خصم يوم الغياب
        r1 = ctk.CTkFrame(content_box, fg_color="transparent")
        r1.pack(fill="x", pady=6)
        ctk.CTkLabel(r1, text="معامل خصم يوم الغياب:", width=180, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="right", padx=5)
        entry_abs_mult = ctk.CTkEntry(r1, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_abs_mult.insert(0, str(hr_cfg.get("absence_penalty_multiplier", 1.0)))
        entry_abs_mult.pack(side="right", padx=5)
        ctk.CTkLabel(r1, text="1 = خصم يوم، 1.5 = يوم ونصف، 2 = يومين", font=ctk.CTkFont(size=10), text_color="#94A3B8").pack(side="right")

        # 2. طريقة احتساب خصم التأخير
        r2 = ctk.CTkFrame(content_box, fg_color="transparent")
        r2.pack(fill="x", pady=6)
        ctk.CTkLabel(r2, text="طريقة احتساب خصم التأخير:", width=180, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="right", padx=5)
        combo_late_type = ctk.CTkComboBox(r2, values=["حساب بالدقائق (دقيقة بدقيقة)", "نظام شرائح التأخير اليومية"], width=190)
        if hr_cfg.get("late_deduction_type") == "tiers":
            combo_late_type.set("نظام شرائح التأخير اليومية")
        else:
            combo_late_type.set("حساب بالدقائق (دقيقة بدقيقة)")
        combo_late_type.pack(side="right", padx=5)

        # 3. معامل دقيقة التأخير
        r3 = ctk.CTkFrame(content_box, fg_color="transparent")
        r3.pack(fill="x", pady=6)
        ctk.CTkLabel(r3, text="مضاعف دقيقة التأخير:", width=180, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right", padx=5)
        entry_late_mult = ctk.CTkEntry(r3, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_late_mult.insert(0, str(hr_cfg.get("late_minute_multiplier", 1.0)))
        entry_late_mult.pack(side="right", padx=5)
        ctk.CTkLabel(r3, text="1 = عادي، 1.5 = دقيقة ونصف، 2 = ضعف", font=ctk.CTkFont(size=10), text_color="#94A3B8").pack(side="right")

        # 4. أساس أيام الشهر لاحتساب أجر اليوم
        r4 = ctk.CTkFrame(content_box, fg_color="transparent")
        r4.pack(fill="x", pady=6)
        ctk.CTkLabel(r4, text="أساس أيام الشهر للأجر:", width=180, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right", padx=5)
        entry_month_days = ctk.CTkEntry(r4, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_month_days.insert(0, str(hr_cfg.get("month_days_basis", 30)))
        entry_month_days.pack(side="right", padx=5)
        ctk.CTkLabel(r4, text="عادة 30 يوماً أو 26 يوماً", font=ctk.CTkFont(size=10), text_color="#94A3B8").pack(side="right")

        # 5. ساعات العمل اليومية
        r5 = ctk.CTkFrame(content_box, fg_color="transparent")
        r5.pack(fill="x", pady=6)
        ctk.CTkLabel(r5, text="ساعات العمل اليومية الرسمية:", width=180, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right", padx=5)
        entry_shift_h = ctk.CTkEntry(r5, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_shift_h.insert(0, str(hr_cfg.get("shift_hours", 7.0)))
        entry_shift_h.pack(side="right", padx=5)
        ctk.CTkLabel(r5, text="لاحتساب أجر الساعة (مثلاً 7 أو 8)", font=ctk.CTkFont(size=10), text_color="#94A3B8").pack(side="right")

        # 6. معامل الساعات الإضافية
        r6 = ctk.CTkFrame(content_box, fg_color="transparent")
        r6.pack(fill="x", pady=6)
        ctk.CTkLabel(r6, text="معامل الساعات الإضافية:", width=180, anchor="e", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right", padx=5)
        entry_ot_mult = ctk.CTkEntry(r6, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        entry_ot_mult.insert(0, str(hr_cfg.get("overtime_multiplier", 1.5)))
        entry_ot_mult.pack(side="right", padx=5)
        ctk.CTkLabel(r6, text="مثلاً 1.5 = ساعة ونصف لكل ساعة عمل", font=ctk.CTkFont(size=10), text_color="#94A3B8").pack(side="right")

        # 7. احتساب خصم الانصراف المبكر
        r7 = ctk.CTkFrame(content_box, fg_color="transparent")
        r7.pack(fill="x", pady=8)
        var_early_ded = ctk.BooleanVar(value=hr_cfg.get("early_leave_deduction", True))
        chk_early = ctk.CTkCheckBox(r7, text="احتساب خصم الانصراف المبكر قبل نهاية الوردية", variable=var_early_ded, font=ctk.CTkFont(family="Segoe UI", size=12))
        chk_early.pack(side="right", padx=5)

        # أزرار الحفظ
        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=25, pady=(5, 20))

        def on_save_policies():
            try:
                abs_m = float(entry_abs_mult.get().strip())
                late_m = float(entry_late_mult.get().strip())
                m_days = float(entry_month_days.get().strip())
                s_hours = float(entry_shift_h.get().strip())
                ot_m = float(entry_ot_mult.get().strip())
                l_type = "tiers" if "شرائح" in combo_late_type.get() else "minutes"

                new_settings = {
                    "absence_penalty_multiplier": abs_m,
                    "late_deduction_type": l_type,
                    "late_minute_multiplier": late_m,
                    "month_days_basis": m_days,
                    "shift_hours": s_hours,
                    "overtime_multiplier": ot_m,
                    "early_leave_deduction": var_early_ded.get()
                }
                self.engine.save_hr_settings(new_settings)
                dialog.destroy()
                self.update_hr_view()
                messagebox.showinfo("تم الحفظ", "تم تحديث سياسات الرواتب وإعادة حساب المسير بنجاح.")
            except ValueError:
                messagebox.showerror("خطأ", "يرجى التأكد من كتابة الأرقام بشكل صحيح.")

        btn_save = ctk.CTkButton(btn_box, text="حفظ السياسات وإعادة الحساب 💾", command=on_save_policies, fg_color="#D97706", hover_color="#B45309", width=200, height=36, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        btn_save.pack(side="right", padx=5)

        btn_cancel = ctk.CTkButton(btn_box, text="إلغاء", command=dialog.destroy, fg_color=("#94A3B8", "#241808"), hover_color=("#64748B", "#3D2A0E"), text_color=("#0F172A", "#FEF3C7"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"), width=90, height=36)
        btn_cancel.pack(side="left", padx=5)

    def export_payroll_excel(self):
        """تصدير مسير الرواتب إلى Excel"""
        try:
            start_d = datetime.datetime.strptime(self.combo_hr_from.get(), "%Y-%m-%d").date()
            end_d = datetime.datetime.strptime(self.combo_hr_to.get(), "%Y-%m-%d").date()
        except Exception:
            messagebox.showwarning("تنبيه", "يرجى تحديد فترة صحيحة لاحتساب الرواتب أولاً.")
            return

        def_name = f"مسير_رواتب_{start_d.strftime('%Y_%m')}_إلى_{end_d.strftime('%Y_%m')}.xlsx"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=def_name,
            title="حفظ مسير الرواتب بصيغة Excel"
        )
        if save_path:
            success = self.engine.export_payroll_to_excel(start_d, end_d, save_path)
            if success:
                messagebox.showinfo("نجاح التصدير", f"تم تصدير كشف مسير الرواتب بنجاح إلى:\n{save_path}")
            else:
                messagebox.showerror("خطأ", "حدث خطأ أثناء تصدير ملف Excel.")

    def setup_raw_tab(self):
        """إعداد تبويب الحركات الخام المسجلة على الماكينة"""
        controls_frame = ctk.CTkFrame(self.tab_raw, fg_color="transparent")
        controls_frame.pack(fill="x", padx=10, pady=10)

        right_box = ctk.CTkFrame(controls_frame, fg_color="transparent")
        right_box.pack(side="right")

        self.raw_search_var = tk.StringVar()
        self.raw_search_var.trace_add("write", lambda *args: self.filter_raw_table())

        lbl_s = ctk.CTkLabel(right_box, text="بحث في الحركات:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        lbl_s.pack(side="right", padx=5)

        raw_search_entry = ctk.CTkEntry(
            right_box,
            textvariable=self.raw_search_var,
            placeholder_text="ابحث باسم الموظف أو الكود أو التاريخ...",
            fg_color=("#FFFFFF", "#171005"),
            border_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            placeholder_text_color=("#94A3B8", "#78664D"),
            width=260
        )
        raw_search_entry.pack(side="right", padx=5)

        self.raw_count_lbl = ctk.CTkLabel(controls_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#F59E0B")
        self.raw_count_lbl.pack(side="left", padx=10)

        # جدول الحركات الخام
        table_container = ctk.CTkFrame(self.tab_raw, corner_radius=8, fg_color=("#F8FAFC", "#171005"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"))
        table_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("no", "tmno", "enno", "name", "mode", "inout", "datetime")
        self.raw_tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")

        headers_map = {
            "no": ("رقم الحركة", 80, "center"),
            "tmno": ("رقم الجهاز", 80, "center"),
            "enno": ("كود الموظف", 80, "center"),
            "name": ("اسم الموظف", 180, "w"),
            "mode": ("طريقة التحقق", 110, "center"),
            "inout": ("حالة البصمة", 110, "center"),
            "datetime": ("التاريخ والوقت المسجل بالماكينة", 220, "center")
        }
        self._raw_base_cols = headers_map

        for c_id, (c_name, c_width, c_align) in headers_map.items():
            self.raw_tree.heading(c_id, text=c_name)
            self.raw_tree.column(c_id, width=c_width, anchor=c_align)

        v_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.raw_tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.raw_tree.xview)
        self.raw_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.raw_tree.pack(fill="both", expand=True)

        self.apply_tree_styles(self.raw_tree)

    def setup_settings_tab(self):
        """إعداد تبويب قواعد العمل ومواعيد الورديات بنمط عنبري راقٍ"""
        settings_box = ctk.CTkScrollableFrame(self.tab_settings, corner_radius=10, fg_color=("#FFFFFF", "#171005"), border_width=1.5, border_color=("#CBD5E1", "#3D2A0E"))
        settings_box.pack(fill="both", expand=True, padx=20, pady=12)

        title = ctk.CTkLabel(
            settings_box,
            text="قواعد احتساب الحضور والانصراف والتأخير",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#F59E0B"
        )
        title.pack(anchor="e", padx=30, pady=(20, 15))

        cfg = self.engine.config

        # 1. موعد بدء العمل
        row1 = ctk.CTkFrame(settings_box, fg_color="transparent")
        row1.pack(fill="x", padx=30, pady=8)
        lbl1 = ctk.CTkLabel(row1, text="موعد بدء العمل الرسمي (صباحاً):", font=ctk.CTkFont(family="Segoe UI", size=13), width=230, anchor="e")
        lbl1.pack(side="right", padx=10)
        self.entry_shift_start = ctk.CTkEntry(row1, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        self.entry_shift_start.insert(0, cfg.get("shift_start", "11:00"))
        self.entry_shift_start.pack(side="right", padx=10)
        ctk.CTkLabel(row1, text="صيغة الوقت 24 ساعة (مثال: 10:00 أو 11:00)", text_color=("#64748B", "#D1A562")).pack(side="right")

        # 2. موعد نهاية العمل
        row2 = ctk.CTkFrame(settings_box, fg_color="transparent")
        row2.pack(fill="x", padx=30, pady=8)
        lbl2 = ctk.CTkLabel(row2, text="موعد نهاية العمل الرسمي (مساءً):", font=ctk.CTkFont(family="Segoe UI", size=13), width=230, anchor="e")
        lbl2.pack(side="right", padx=10)
        self.entry_shift_end = ctk.CTkEntry(row2, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        self.entry_shift_end.insert(0, cfg.get("shift_end", "19:00"))
        self.entry_shift_end.pack(side="right", padx=10)
        ctk.CTkLabel(row2, text="صيغة الوقت 24 ساعة (مثال: 18:00 أو 19:00)", text_color=("#64748B", "#D1A562")).pack(side="right")

        # 3. فترة السماح بالتأخير
        row3 = ctk.CTkFrame(settings_box, fg_color="transparent")
        row3.pack(fill="x", padx=30, pady=6)
        lbl3 = ctk.CTkLabel(row3, text="فترة السماح بالتأخير (دقائق):", font=ctk.CTkFont(family="Segoe UI", size=13), width=230, anchor="e")
        lbl3.pack(side="right", padx=10)
        self.entry_grace_mins = ctk.CTkEntry(row3, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        self.entry_grace_mins.insert(0, str(cfg.get("grace_period_mins", 15)))
        self.entry_grace_mins.pack(side="right", padx=10)
        ctk.CTkLabel(row3, text="الدقائق المسموح بها بعد بداية الوردية دون احتساب تأخير", text_color=("#64748B", "#D1A562")).pack(side="right")

        # 3.1 طريقة احتساب دقائق التأخير
        row3_sub = ctk.CTkFrame(settings_box, fg_color="transparent")
        row3_sub.pack(fill="x", padx=30, pady=4)
        lbl3_sub = ctk.CTkLabel(row3_sub, text="طريقة احتساب دقائق التأخير:", font=ctk.CTkFont(family="Segoe UI", size=13), width=230, anchor="e")
        lbl3_sub.pack(side="right", padx=10)
        self.var_late_calc_mode = ctk.StringVar(value=cfg.get("late_calc_mode", "after_grace"))
        r_after = ctk.CTkRadioButton(
            row3_sub,
            text="احتساب التأخير لما بعد فترة السماح فقط (مثال: حضور 11:35 بسماح 30د = 5 دقائق تأخير)",
            variable=self.var_late_calc_mode,
            value="after_grace",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        r_after.pack(side="right", padx=10)
        r_start = ctk.CTkRadioButton(
            row3_sub,
            text="احتساب التأخير كاملاً من بداية الوردية",
            variable=self.var_late_calc_mode,
            value="from_start",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        r_start.pack(side="right", padx=10)

        # 4. فترة السماح بالانصراف المبكر
        row4 = ctk.CTkFrame(settings_box, fg_color="transparent")
        row4.pack(fill="x", padx=30, pady=6)
        lbl4 = ctk.CTkLabel(row4, text="سماح الانصراف المبكر (دقائق):", font=ctk.CTkFont(family="Segoe UI", size=13), width=230, anchor="e")
        lbl4.pack(side="right", padx=10)
        self.entry_early_grace = ctk.CTkEntry(row4, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        self.entry_early_grace.insert(0, str(cfg.get("early_departure_grace", 10)))
        self.entry_early_grace.pack(side="right", padx=10)

        # 4.1 رصيد ساعات الاستئذان العامة المسموح بها شهرياً
        row_perm = ctk.CTkFrame(settings_box, fg_color="transparent")
        row_perm.pack(fill="x", padx=30, pady=6)
        lbl_perm = ctk.CTkLabel(row_perm, text="رصيد ساعات الإذن الشهرية المسموح بها (ساعات):", font=ctk.CTkFont(family="Segoe UI", size=13), width=230, anchor="e")
        lbl_perm.pack(side="right", padx=10)
        self.entry_perm_hours = ctk.CTkEntry(row_perm, width=120, fg_color=("#FFFFFF", "#1F160A"), border_color=("#CBD5E1", "#3D2A0E"), text_color=("#0F172A", "#FFFBEB"))
        self.entry_perm_hours.insert(0, str(cfg.get("monthly_permission_hours", 4.0)))
        self.entry_perm_hours.pack(side="right", padx=10)
        ctk.CTkLabel(row_perm, text="تطبق على جميع الموظفين (تأخير الصباح + انصراف مبكر) - إذا تجاوزها الموظف يُخصم يوم", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#F59E0B").pack(side="right")

        # 5. العطلة الأسبوعية العامة
        row5 = ctk.CTkFrame(settings_box, fg_color="transparent")
        row5.pack(fill="x", padx=30, pady=6)
        lbl5 = ctk.CTkLabel(row5, text="العطلة الأسبوعية العامة (الافتراضية):", font=ctk.CTkFont(family="Segoe UI", size=13), width=230, anchor="e")
        lbl5.pack(side="right", padx=10)
        self.combo_weekend = ctk.CTkComboBox(
            row5,
            values=["الجمعة فقط", "الجمعة والسبت", "بدون عطلة"],
            width=150
        )
        current_wk = cfg.get("weekend_days", [4])
        if current_wk == [4, 5]:
            self.combo_weekend.set("الجمعة والسبت")
        elif not current_wk:
            self.combo_weekend.set("بدون عطلة")
        else:
            self.combo_weekend.set("الجمعة فقط")
        self.combo_weekend.pack(side="right", padx=10)
        ctk.CTkLabel(row5, text="تطبق تلقائياً على كل الموظفين ما لم يُحدد لهم أيام إجازة خاصة أدناه", text_color=("#64748B", "#D1A562")).pack(side="right")

        # 6. عدم احتساب الغياب قبل تاريخ أول بصمة للموظف
        row6 = ctk.CTkFrame(settings_box, fg_color="transparent")
        row6.pack(fill="x", padx=30, pady=6)
        self.var_auto_hire = ctk.BooleanVar(value=cfg.get("auto_detect_hire_date", True))
        self.chk_auto_hire = ctk.CTkCheckBox(
            row6,
            text="عدم احتساب الموظف غائباً في الأيام السابقة لتاريخ أول بصمة له (تاريخ التحاقه بالعمل)",
            variable=self.var_auto_hire,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.chk_auto_hire.pack(side="right", padx=10)

        # 7. قسم خاص: إجازات موظفي المبيعات والورديات الخاصة
        emp_wk_card = ctk.CTkFrame(
            settings_box,
            fg_color=("#F8FAFC", "#1F160A"),
            corner_radius=10,
            border_width=1.5,
            border_color=("#CBD5E1", "#3D2A0E")
        )
        emp_wk_card.pack(fill="x", padx=30, pady=12)

        wk_title_row = ctk.CTkFrame(emp_wk_card, fg_color="transparent")
        wk_title_row.pack(fill="x", padx=15, pady=(10, 4))
        ctk.CTkLabel(
            wk_title_row,
            text="🏖️ إجازات موظفي المبيعات والورديات الخاصة (أيام الراحة الأسبوعية لكل موظف)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#F59E0B"
        ).pack(side="right")
        ctk.CTkLabel(
            wk_title_row,
            text="اختر الموظف وحدد أيام إجازته في الأسبوع (سيتم استثناؤه تلقائياً من الغياب في هذه الأيام)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748B", "#FEF3C7")
        ).pack(side="left")

        wk_ctrl_row = ctk.CTkFrame(emp_wk_card, fg_color="transparent")
        wk_ctrl_row.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(wk_ctrl_row, text="اختر الموظف:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="right", padx=5)

        emp_choices = [f"{e['enno']} - {e['name']}" for e in sorted(self.engine.employees.values(), key=lambda x: x['enno'])] if self.engine.employees else ["-- لا توجد بيانات موظفين --"]
        self.combo_emp_weekend = ctk.CTkComboBox(wk_ctrl_row, values=emp_choices, width=220)
        self.combo_emp_weekend.pack(side="right", padx=10)

        # مصفوفة أيام الأسبوع
        # 0=الإثنين, 1=الثلاثاء, 2=الأربعاء, 3=الخميس, 4=الجمعة, 5=السبت, 6=الأحد
        weekdays_meta = [
            (5, "السبت"),
            (6, "الأحد"),
            (0, "الإثنين"),
            (1, "الثلاثاء"),
            (2, "الأربعاء"),
            (3, "الخميس"),
            (4, "الجمعة")
        ]
        self.emp_wk_vars = {}
        days_box = ctk.CTkFrame(emp_wk_card, fg_color="transparent")
        days_box.pack(fill="x", padx=15, pady=(2, 10))

        ctk.CTkLabel(days_box, text="أيام الإجازة الأسبوعية:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="right", padx=(5, 10))

        for day_num, day_title in weekdays_meta:
            var = ctk.BooleanVar(value=False)
            self.emp_wk_vars[day_num] = var
            chk = ctk.CTkCheckBox(days_box, text=day_title, variable=var, width=70, font=ctk.CTkFont(family="Segoe UI", size=11))
            chk.pack(side="right", padx=4)

        def on_emp_weekend_selected(choice):
            try:
                enno_sel = int(choice.split(" - ")[0])
                assigned_days = self.engine.get_employee_weekend_days(enno_sel)
                for d_num, v in self.emp_wk_vars.items():
                    v.set(d_num in assigned_days)
            except Exception:
                pass

        self.combo_emp_weekend.configure(command=on_emp_weekend_selected)

        # زر حفظ إجازة الموظف
        def save_selected_emp_weekend():
            try:
                val = self.combo_emp_weekend.get()
                if " - " not in val:
                    messagebox.showwarning("تنبيه", "يرجى اختيار موظف أولاً.")
                    return
                enno_sel = int(val.split(" - ")[0])
                sel_days = [d_num for d_num, v in self.emp_wk_vars.items() if v.get()]
                self.engine.set_employee_weekend_days(enno_sel, sel_days)
                self.update_daily_view()
                self.update_period_view()
                messagebox.showinfo("تم الحفظ", f"تم حفظ أيام الإجازة الأسبوعية للموظف [{val}] وتحديث التقارير بنجاح!")
            except Exception as e:
                messagebox.showerror("خطأ", f"حدث خطأ أثناء حفظ أيام الإجازة:\n{e}")

        # زر إعادة الموظف للعطلة العامة
        def reset_selected_emp_weekend():
            try:
                val = self.combo_emp_weekend.get()
                if " - " not in val:
                    return
                enno_sel = int(val.split(" - ")[0])
                self.engine.set_employee_weekend_days(enno_sel, None)
                # استعادة الأيام الافتراضية
                gen_days = self.engine.config.get("weekend_days", [4, 5])
                for d_num, v in self.emp_wk_vars.items():
                    v.set(d_num in gen_days)
                self.update_daily_view()
                self.update_period_view()
                messagebox.showinfo("تم الاسترجاع", f"تمت استعادة العطلة الأسبوعية العامة للموظف [{val}] بنجاح.")
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        btn_save_emp_wk = ctk.CTkButton(
            days_box,
            text="الموظف هذا إجازة حفظ 💾",
            command=save_selected_emp_weekend,
            fg_color="#D97706",
            hover_color="#B45309",
            width=160,
            height=30,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        btn_save_emp_wk.pack(side="left", padx=5)

        btn_reset_emp_wk = ctk.CTkButton(
            days_box,
            text="العامة العطلة استعادة 🔄",
            command=reset_selected_emp_weekend,
            fg_color=("#94A3B8", "#241808"),
            hover_color=("#64748B", "#3D2A0E"),
            text_color=("#0F172A", "#FEF3C7"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E"),
            width=140,
            height=30,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        btn_reset_emp_wk.pack(side="left", padx=5)

        # تهيئة الاختيار الأولي لموظف الإجازات
        if emp_choices and " - " in emp_choices[0]:
            on_emp_weekend_selected(emp_choices[0])

        # زر الحفظ العام
        btn_save = ctk.CTkButton(
            settings_box,
            text="فوراً الحساب وإعادة العامة الإعدادات حفظ 💾",
            command=self.save_settings_action,
            fg_color="#D97706",
            hover_color="#B45309",
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        btn_save.pack(anchor="e", padx=30, pady=(15, 20))

    def apply_tree_styles(self, tree: ttk.Treeview):
        """تخصيص تصميم وألوان جدول البيانات ليتناسق مع الواجهة الداكنة بنمط نهاري عنبري (Amber Theme - LG_M.A) بدقة وتباين فائق"""
        if not hasattr(self, "_registered_trees"):
            self._registered_trees = []
        if tree not in self._registered_trees:
            self._registered_trees.append(tree)

        style = ttk.Style()
        style.theme_use("clam")

        is_dark = (ctk.get_appearance_mode().lower() == "dark")
        scale = getattr(self, "_current_scale", 1.0)
        body_font_size = max(8, int(round(10.0 * scale)))
        heading_font_size = max(9, int(round(11.0 * scale)))
        row_height = max(18, int(round(30.0 * scale)))
        heading_pad = max(3, int(round(7.0 * scale)))

        if is_dark:
            # نمط نهاري عنبري الداكن (Amber Dark Mode - LG_M.A Style)
            # رأس الجدول: خلفية عنبرية داكنة راقية + نص ذهبي عنبري مشرق وواضح
            style.configure(
                "Treeview.Heading",
                font=("Segoe UI", heading_font_size, "bold"),
                background="#1F160A",
                foreground="#FBBF24",
                relief="flat",
                padding=heading_pad
            )
            style.map(
                "Treeview.Heading",
                background=[('active', '#2D1F0E')],
                foreground=[('active', '#FFFBEB')]
            )

            # جسم الجدول والصفوف
            style.configure(
                "Treeview",
                font=("Segoe UI", body_font_size),
                rowheight=row_height,
                background="#120E08",
                foreground="#FFFBEB",
                fieldbackground="#120E08",
                bordercolor="#3D2A0E",
                borderwidth=1
            )
            style.map(
                "Treeview",
                background=[('selected', '#D97706')],
                foreground=[('selected', '#FFFFFF')]
            )

            # وسوم الحالات مع تباين عالي ومريح للعين
            # حاضر: زيتي داكن أنيق + نص زمردي متألق
            tree.tag_configure("present", background="#0D2818", foreground="#6EE7B7")
            # متأخر: خلفية عنبري دافئ داكن + نص أصفر ذهبي عنبري ساطع
            tree.tag_configure("late", background="#451A03", foreground="#FDE047")
            # غياب: قرمزي غامق + نص مرجاني وردي ناصع
            tree.tag_configure("absent", background="#450A0A", foreground="#FCA5A5")
            # بدون انصراف: كحلي محيطي عميق + نص سماوي مشرق
            tree.tag_configure("missing", background="#082F49", foreground="#7DD3FC")
            # عطلة أسبوعية: بني عنبري داكن + نص ذهبي دافئ
            tree.tag_configure("weekend", background="#241808", foreground="#D4AF37")
            # صفوف عادية متبادلة Zebra Stripping
            tree.tag_configure("evenrow", background="#171005", foreground="#FEF3C7")
            tree.tag_configure("oddrow", background="#120E08", foreground="#FFFBEB")
        else:
            # نمط نهاري فاتح عنبري (Amber Light Mode)
            style.configure(
                "Treeview.Heading",
                font=("Segoe UI", heading_font_size, "bold"),
                background="#F8FAFC",
                foreground="#EA580C",
                relief="flat",
                padding=heading_pad
            )
            style.map(
                "Treeview.Heading",
                background=[('active', '#FFF7ED')],
                foreground=[('active', '#C2410C')]
            )
            style.configure(
                "Treeview",
                font=("Segoe UI", body_font_size),
                rowheight=row_height,
                background="#FFFFFF",
                foreground="#0F172A",
                fieldbackground="#FFFFFF",
                bordercolor="#E2E8F0",
                borderwidth=1
            )
            style.map(
                "Treeview",
                background=[('selected', '#F59E0B')],
                foreground=[('selected', '#FFFFFF')]
            )
            tree.tag_configure("present", background="#ECFDF5", foreground="#065F46")
            tree.tag_configure("late", background="#FFFBEB", foreground="#B45309")
            tree.tag_configure("absent", background="#FEF2F2", foreground="#991B1B")
            tree.tag_configure("missing", background="#F0F9FF", foreground="#0369A1")
            tree.tag_configure("weekend", background="#F1F5F9", foreground="#475569")
            tree.tag_configure("evenrow", background="#FFFFFF", foreground="#0F172A")
            tree.tag_configure("oddrow", background="#F8FAFC", foreground="#0F172A")

    # ==================== محرك التكيف التلقائي مع جميع مقاسات الشاشات (Responsive Scaling) ====================

    def _get_real_window_size(self):
        """الحصول على المقاس الحقيقي الفعلي لنافذة البرنامج بالبكسل"""
        try:
            parts = self.geometry().split("+")[0].split("x")
            return int(parts[0]), int(parts[1])
        except Exception:
            return 1240, 800

    def _on_window_configure(self, event):
        """التقاط حدث تغيير أبعاد النافذة مع منع التكرار (Debouncing)"""
        if event.widget != self:
            return

        w, h = self._get_real_window_size()
        if (w, h) == self._last_win_size:
            return
        self._last_win_size = (w, h)

        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(80, self._apply_responsive_scaling)

    def _apply_responsive_scaling(self):
        """حساب وتطبيق مقياس التصغير والتكبير التلقائي للخطوط والأزرار والبطاقات والجداول"""
        self._resize_job = None
        w, h = self._get_real_window_size()
        if w < 250 or h < 250:
            return

        # الحساب بالنسبة للحجم المرجعي القياسي 1240x800
        scale_w = w / self._base_width
        scale_h = h / self._base_height
        raw_scale = min(scale_w, scale_h)

        # حصر النطاق بين 0.65x و 1.25x مع خطوات منتظمة 0.05
        clamped_scale = max(0.65, min(1.25, raw_scale))
        target_scale = round(clamped_scale * 20.0) / 20.0

        if abs(target_scale - self._current_scale) >= 0.035:
            self._current_scale = target_scale
            ctk.set_widget_scaling(target_scale)
            self._update_responsive_treeviews(target_scale)

    def _update_responsive_treeviews(self, scale: float):
        """تحديث خطوط وصفوف وأعمدة جميع الجداول لتتناسب تلقائياً مع حجم النافذة"""
        body_font_size = max(8, int(round(10.0 * scale)))
        heading_font_size = max(9, int(round(11.0 * scale)))
        row_height = max(18, int(round(30.0 * scale)))
        heading_pad = max(3, int(round(7.0 * scale)))

        try:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure(
                "Treeview",
                font=("Segoe UI", body_font_size),
                rowheight=row_height
            )
            style.configure(
                "Treeview.Heading",
                font=("Segoe UI", heading_font_size, "bold"),
                padding=heading_pad
            )

            # تحجيم أعمدة كل جدول مسجل
            tree_maps = [
                (getattr(self, "daily_tree", None), getattr(self, "_daily_base_cols", None)),
                (getattr(self, "monthly_tree", None), getattr(self, "_monthly_base_cols", None)),
                (getattr(self, "hr_tree", None), getattr(self, "_hr_base_cols", None)),
                (getattr(self, "raw_tree", None), getattr(self, "_raw_base_cols", None)),
            ]
            for tree, col_map in tree_maps:
                if tree is not None and col_map:
                    for col_id, (c_name, base_w, c_align) in col_map.items():
                        new_w = max(25, int(round(base_w * scale)))
                        min_w = max(20, int(round(base_w * scale * 0.6)))
                        tree.column(col_id, width=new_w, minwidth=min_w)
        except Exception:
            pass

    # ==================== أحداث العمليات والبيانات ====================

    def show_about_developer(self):
        """نافذة منبثقة راقية تعرض حقوق الملكية ومعلومات مطور وبرمجيات النظام"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("حقوق الملكية وتطوير النظام - Ahmed TorGoman")
        dialog.geometry("480x360")
        dialog.minsize(420, 320)
        dialog.transient(self)
        dialog.grab_set()

        # إطار الرأس العنبري
        hdr = ctk.CTkFrame(dialog, corner_radius=0, fg_color=("#FFFFFF", "#120E08"))
        hdr.pack(fill="x", pady=0)

        ctk.CTkLabel(
            hdr,
            text="👑 بطاقة حقوق الملكية وتطوير النظام",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#F59E0B"
        ).pack(pady=(15, 3))

        ctk.CTkLabel(
            hdr,
            text="BioTorg Pro - Smart Attendance & HR Payroll System",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("#64748B", "#D1A562")
        ).pack(pady=(0, 10))

        # بطاقة التفاصيل
        body = ctk.CTkFrame(dialog, fg_color=("#F8FAFC", "#171005"), corner_radius=10, border_width=1.5, border_color=("#CBD5E1", "#3D2A0E"))
        body.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(
            body,
            text="تمت البرمجة والتطوير بواسطة:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#475569", "#FEF3C7")
        ).pack(pady=(15, 2))

        ctk.CTkLabel(
            body,
            text="Ahmed TorGoman",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#F59E0B"
        ).pack(pady=2)

        import webbrowser

        lbl_tg = ctk.CTkLabel(
            body,
            text="✈️ تلجرام: @torgoman0",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#38BDF8",
            cursor="hand2"
        )
        lbl_tg.pack(pady=6)
        lbl_tg.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://t.me/torgoman0"))

        ctk.CTkLabel(
            body,
            text="جميع الحقوق محفوظة ومسجلة للمطور © Ahmed TorGoman",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748B", "#D1A562")
        ).pack(pady=(6, 8))

        ctk.CTkButton(
            body,
            text="💖 دعم المطور عبر InstaPay",
            command=lambda: [dialog.destroy(), self.show_support_dialog()],
            fg_color=("#FEF2F2", "#261317"),
            hover_color=("#FEE2E2", "#3D1A21"),
            text_color=("#DC2626", "#F87171"),
            border_width=1,
            border_color=("#EF4444", "#DC2626"),
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            height=28,
            width=180
        ).pack(pady=(0, 10))

        # زر الإغلاق
        ctk.CTkButton(
            dialog,
            text="إغلاق ✕",
            command=dialog.destroy,
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=120,
            height=32
        ).pack(pady=(0, 15))

    def show_support_dialog(self):
        """نافذة راقية لعرض رمز الاستجابة السريعة (QR Code) لمحفظة إنستاباي لدعم المطور والبرنامج"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("💖 دعم وتطوير برنامج BioTorg Pro - InstaPay")
        dialog.geometry("500x670")
        dialog.minsize(460, 620)
        dialog.transient(self)
        dialog.grab_set()

        # إطار الرأس
        hdr = ctk.CTkFrame(dialog, corner_radius=0, fg_color=("#FFFFFF", "#120E08"))
        hdr.pack(fill="x", pady=0)

        ctk.CTkLabel(
            hdr,
            text="💖 ادعم استمرار تطوير BioTorg Pro",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#F59E0B"
        ).pack(pady=(14, 3))

        ctk.CTkLabel(
            hdr,
            text="مساهمتك الكريمة تضمن استمرار التحديثات المجانية والتطوير المستمر",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("#64748B", "#D1A562")
        ).pack(pady=(0, 10))

        # جسم النافذة الرئيسي
        body = ctk.CTkFrame(
            dialog,
            fg_color=("#F8FAFC", "#171005"),
            corner_radius=12,
            border_width=1.5,
            border_color=("#CBD5E1", "#3D2A0E")
        )
        body.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            body,
            text="إذا كان البرنامج قد وفّر عليك الوقت والمجهود ونال إعجابك،\nيسعدنا ويشرفنا دعمك عبر محفظة إنستاباي (InstaPay):",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#334155", "#FEF3C7"),
            justify="center"
        ).pack(pady=(10, 4))

        # تحميل وعرض صورة الـ QR Code
        qr_pil = None
        try:
            app_dir = get_app_dir()
            p1 = os.path.join(app_dir, "assets", "instapay_qr.png")
            p2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "instapay_qr.png")
            for p in [p1, p2]:
                if os.path.exists(p):
                    qr_pil = Image.open(p)
                    break
        except Exception:
            pass

        if qr_pil is None:
            try:
                import base64
                import io
                import assets_data
                data = base64.b64decode(assets_data.INSTAPAY_QR_BASE64)
                qr_pil = Image.open(io.BytesIO(data))
            except Exception:
                pass

        if qr_pil is not None:
            # إطار أبيض أنيق حول الـ QR لسهولة مسحه بالكاميرا حتى في الوضع الليلي
            qr_frame = ctk.CTkFrame(body, fg_color="#FFFFFF", corner_radius=10, border_width=2, border_color="#D97706")
            qr_frame.pack(pady=4)

            # تحجيم متناسق للصورة
            ctk_img = ctk.CTkImage(light_image=qr_pil, dark_image=qr_pil, size=(245, 262))
            lbl_img = ctk.CTkLabel(qr_frame, image=ctk_img, text="")
            lbl_img.image = ctk_img
            lbl_img.pack(padx=6, pady=6)
        else:
            ctk.CTkLabel(
                body,
                text="📱 رمز QR متاح عبر InstaPay",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#F59E0B"
            ).pack(pady=20)

        # صندوق المعرف
        id_frame = ctk.CTkFrame(body, fg_color=("#F1F5F9", "#241808"), corner_radius=8, border_width=1, border_color=("#CBD5E1", "#3D2A0E"))
        id_frame.pack(fill="x", padx=25, pady=6)

        instapay_account = "torgoman0@instapay"

        ctk.CTkLabel(
            id_frame,
            text="معرّف التحويل المباشر (IPA):",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("#64748B", "#D1A562")
        ).pack(pady=(4, 0))

        lbl_id = ctk.CTkLabel(
            id_frame,
            text=instapay_account,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#10B981"
        )
        lbl_id.pack(pady=(0, 4))

        # زر نسخ المعرف
        def copy_id():
            self.clipboard_clear()
            self.clipboard_append(instapay_account)
            btn_copy.configure(text="تم النسخ بنجاح! ✅", fg_color="#10B981", hover_color="#059669")
            self.after(2000, lambda: btn_copy.configure(
                text="نسخ معرف إنستاباي 📋",
                fg_color="#D97706",
                hover_color="#B45309"
            ))

        btn_copy = ctk.CTkButton(
            body,
            text="نسخ معرف إنستاباي 📋",
            command=copy_id,
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=32,
            width=210
        )
        btn_copy.pack(pady=4)

        # زر الإغلاق في الأسفل
        ctk.CTkButton(
            dialog,
            text="شكراً جزيلاً لدعمكم ✕",
            command=dialog.destroy,
            fg_color=("#E2E8F0", "#241808"),
            hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FBBF24"),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=160,
            height=32
        ).pack(pady=(0, 10))

    def toggle_theme(self):
        curr = ctk.get_appearance_mode()
        new_mode = "Light" if curr == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        if hasattr(self, "_registered_trees"):
            for t in self._registered_trees:
                try:
                    self.apply_tree_styles(t)
                except Exception:
                    pass

    def switch_to_known_file(self, filename: str):
        base_dir = get_app_dir()
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            self.load_fingerprint_file(path)
        else:
            messagebox.showwarning("تنبيه", f"الملف {filename} غير موجود في المسار الحالي.")

    def choose_custom_file(self):
        file_path = filedialog.askopenfilename(
            title="اختر ملف البصمة",
            filetypes=[("Text & Dat Files", "*.TXT *.DAT *.txt *.dat"), ("All Files", "*.*")]
        )
        if file_path:
            # إذا اختار ملف DAT، نتحقق إن كان هناك TXT مصاحب
            if file_path.upper().endswith(".DAT"):
                txt_equivalent = file_path[:-4] + ".TXT"
                if os.path.exists(txt_equivalent):
                    file_path = txt_equivalent

            self.load_fingerprint_file(file_path)

    def detect_usb_fingerprint_file(self) -> Optional[str]:
        """فحص الفلاشات المتصلة بالكمبيوتر والبحث عن ملفات البصمة"""
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                if (bitmask >> (ord(letter) - ord('A'))) & 1:
                    drive_path = f"{letter}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    if drive_type == 2:  # DRIVE_REMOVABLE
                        agl = os.path.join(drive_path, "AGL_001.TXT")
                        glg = os.path.join(drive_path, "GLG_001.TXT")
                        if os.path.exists(agl):
                            return agl
                        if os.path.exists(glg):
                            return glg
        except Exception as e:
            print("Error scanning USB:", e)
        return None

    def sync_from_usb(self):
        """قراءة أحدث ملفات البصمة تلقائياً من الفلاشة المتصلة"""
        usb_file = self.detect_usb_fingerprint_file()
        if not usb_file:
            messagebox.showinfo(
                "فحص الفلاشة (USB)",
                "لم يتم العثور على فلاشة USB متصلة تحتوي على ملفات البصمة (AGL_001.TXT).\n\n"
                "يرجى التأكد من توصيل الفلاشة بالكمبيوتر والمحاولة مجدداً."
            )
            return

        drive_letter = os.path.splitdrive(usb_file)[0]
        fname = os.path.basename(usb_file)
        ans = messagebox.askyesno(
            "تم اكتشاف الفلاشة 🔌",
            f"تم العثور على ملف البصمة على الفلاشة ({drive_letter}\\):\n{fname}\n\n"
            f"هل تريد سحب وقراءة الحركات فوراً؟"
        )
        if ans:
            self.load_fingerprint_file(usb_file)
            messagebox.showinfo("تم السحب بنجاح", f"تم سحب وقراءة البيانات بنجاح من الفلاشة ({drive_letter})!")

    def load_fingerprint_file(self, file_path: str):
        success = self.engine.load_file(file_path)
        if not success:
            messagebox.showerror("خطأ", f"تعذر قراءة ملف البصمة:\n{file_path}")
            return

        # تحديث الأزرار بنمط عنبري
        fname = os.path.basename(file_path).upper()
        if "AGL" in fname:
            self.btn_agl.configure(fg_color="#D97706", text_color="#FFFFFF")
            self.btn_glg.configure(fg_color=("#E2E8F0", "#241808"), text_color=("#0F172A", "#FEF3C7"))
        elif "GLG" in fname:
            self.btn_glg.configure(fg_color="#D97706", text_color="#FFFFFF")
            self.btn_agl.configure(fg_color=("#E2E8F0", "#241808"), text_color=("#0F172A", "#FEF3C7"))
        else:
            self.btn_agl.configure(fg_color=("#E2E8F0", "#241808"), text_color=("#0F172A", "#FEF3C7"))
            self.btn_glg.configure(fg_color=("#E2E8F0", "#241808"), text_color=("#0F172A", "#FEF3C7"))

        self.refresh_all_views()
        self.status_label.configure(text=f"تم تحميل الملف بنجاح ({len(self.engine.df_clean)} حركة)")

    def refresh_all_views(self):
        """تحديث الواجهة مع تفعيل الفتح السريع الفوري للتقرير اليومي"""
        if not self.engine.available_dates:
            return

        date_strings = [d.strftime("%Y-%m-%d") for d in self.engine.available_dates]
        self.date_combobox.configure(values=date_strings)
        self.combo_from_date.configure(values=list(reversed(date_strings)))
        self.combo_to_date.configure(values=date_strings)

        # تحديد أحدث تاريخ افتراضياً
        self.selected_date = self.engine.available_dates[0]
        self.date_combobox.set(self.selected_date.strftime("%Y-%m-%d"))

        # نطاق مبدئي للملخص الدوري: أول وآخر شهر
        if len(self.engine.available_dates) > 0:
            self.combo_from_date.set(date_strings[-1])
            self.combo_to_date.set(date_strings[0])

        fname = os.path.basename(self.engine.current_file_path or "")
        total_p = len(self.engine.df_clean) if self.engine.df_clean is not None else 0
        total_emp = len(self.engine.employees)
        self.file_info_label.configure(
            text=f"الملف النشط: {fname} | إجمالي الحركات: {total_p} | الموظفون: {total_emp}"
        )

        # 1. تحديث التقرير اليومي فقط عند البداية لتسريع الفتح الفوري
        self._loaded_tabs = {"daily"}
        self.update_daily_view()

        # إعداد تواريخ تبويب الرواتب إن وجدت (البدء تلقائياً من أول الشهر الأخير لتفادي البطء)
        if hasattr(self, "combo_hr_from") and hasattr(self, "combo_hr_to"):
            self.combo_hr_from.configure(values=list(reversed(date_strings)))
            self.combo_hr_to.configure(values=date_strings)
            if len(self.engine.available_dates) > 0:
                latest_d = self.engine.available_dates[0]
                month_start_d = latest_d.replace(day=1)
                valid_from = [d for d in self.engine.available_dates if d >= month_start_d]
                default_from_d = valid_from[-1] if valid_from else latest_d
                self.combo_hr_from.set(default_from_d.strftime("%Y-%m-%d"))
                self.combo_hr_to.set(latest_d.strftime("%Y-%m-%d"))

        # تحديث قائمة موظفي إجازات المبيعات في تبويب الإعدادات
        if hasattr(self, "combo_emp_weekend") and self.engine.employees:
            emp_choices = [f"{e['enno']} - {e['name']}" for e in sorted(self.engine.employees.values(), key=lambda x: x['enno'])]
            self.combo_emp_weekend.configure(values=emp_choices)
            if not self.combo_emp_weekend.get() or "--" in self.combo_emp_weekend.get():
                self.combo_emp_weekend.set(emp_choices[0])

        # 2. تحميل باقي التبويبات بالخلفية بدون تعطيل واجهة المستخدم
        self.after(400, self._idle_background_preload)

        # 3. فحص التحديثات الذكي وعرض مميزات الإصدار الجديد إن وجدت
        self.after(1200, self.init_auto_updater)

    def init_auto_updater(self):
        """التحقق التلقائي الهادئ من تحديثات GitHub وعرض مميزات التحديث الجديد"""
        try:
            # 1. إظهار نافذة 'ما الجديد' إذا تم تثبيت تحديث مؤخراً
            updater.check_and_show_whats_new(self)

            # 2. فحص خلفي صامت لتوفر تحديث جديد
            def _on_check(has_update, remote_info):
                if has_update and remote_info:
                    current_info = updater.get_local_version_info()
                    cur_v = current_info.get("version", "2.2.0")
                    self.after(0, lambda: updater.UpdateDialog(self, cur_v, remote_info))

            updater.check_for_updates_background(_on_check)
        except Exception as e:
            print("Auto-updater check error:", e)

    def manual_check_updates(self):
        """فحص يدوي للتحديثات عند النقر على الزر في الشريط العلوي"""
        self.btn_check_update.configure(state="disabled", text="جاري الفحص... ⏳")
        def _on_manual_check(has_update, remote_info):
            def _ui_action():
                self.btn_check_update.configure(state="normal", text="التحديثات 🔄")
                current_info = updater.get_local_version_info()
                cur_v = current_info.get("version", "2.2.0")
                if has_update and remote_info:
                    updater.UpdateDialog(self, cur_v, remote_info)
                else:
                    messagebox.showinfo(
                        "التحديثات",
                        f"أنت تستخدم بالفعل أحدث إصدار من البرنامج (v{cur_v}) ولا توجد تحديثات جديدة حالياً."
                    )
            self.after(0, _ui_action)

        updater.check_for_updates_background(_on_manual_check)

    def on_tab_changed(self):
        """التحميل الكسول (Lazy Load) للتبويبات عند النقر عليها فقط"""
        cur_tab = self.tabview.get()
        if ("الملخص" in cur_tab or "الدوري" in cur_tab) and "monthly" not in self._loaded_tabs:
            self._loaded_tabs.add("monthly")
            self.update_period_view()
        elif "الخام" in cur_tab and "raw" not in self._loaded_tabs:
            self._loaded_tabs.add("raw")
            self.populate_raw_table()
        elif "الرواتب" in cur_tab and "hr" not in self._loaded_tabs:
            self._loaded_tabs.add("hr")
            if hasattr(self, "var_hr_enabled") and self.var_hr_enabled.get():
                self.update_hr_view()

    def _idle_background_preload(self):
        """تحميل هادئ وتدريجي في الخلفية بعد ظهور النافذة للمستخدم"""
        try:
            if "raw" not in self._loaded_tabs:
                self._loaded_tabs.add("raw")
                self.populate_raw_table()
            if "monthly" not in self._loaded_tabs:
                self._loaded_tabs.add("monthly")
                self.update_period_view()
        except Exception:
            pass

    def on_date_changed(self, choice: str):
        try:
            self.selected_date = datetime.datetime.strptime(choice, "%Y-%m-%d").date()
            self._selected_daily_enno = None
            self.update_daily_view()
        except Exception:
            pass

    def go_prev_day(self):
        if not self.engine.available_dates:
            return
        try:
            cur_idx = self.engine.available_dates.index(self.selected_date)
            if cur_idx + 1 < len(self.engine.available_dates):
                self.selected_date = self.engine.available_dates[cur_idx + 1]
                self.date_combobox.set(self.selected_date.strftime("%Y-%m-%d"))
                self._selected_daily_enno = None
                self.update_daily_view()
        except ValueError:
            pass

    def go_next_day(self):
        if not self.engine.available_dates:
            return
        try:
            cur_idx = self.engine.available_dates.index(self.selected_date)
            if cur_idx - 1 >= 0:
                self.selected_date = self.engine.available_dates[cur_idx - 1]
                self.date_combobox.set(self.selected_date.strftime("%Y-%m-%d"))
                self._selected_daily_enno = None
                self.update_daily_view()
        except ValueError:
            pass

    def go_latest_day(self):
        if self.engine.available_dates:
            self.selected_date = self.engine.available_dates[0]
            self.date_combobox.set(self.selected_date.strftime("%Y-%m-%d"))
            self._selected_daily_enno = None
            self.update_daily_view()

    def set_daily_filter(self, filter_key: str):
        self.current_filter = filter_key
        active_colors = {
            "ALL": "#D97706",
            "PRESENT": "#10B981",
            "LATE": "#F59E0B",
            "ABSENT": "#EF4444",
            "NO_CHECKOUT": "#06B6D4"
        }
        for k, btn in self.filter_buttons.items():
            if k == filter_key:
                btn.configure(fg_color=active_colors.get(k, "#D97706"), text_color="#FFFFFF")
            else:
                btn.configure(fg_color=("#E2E8F0", "#241808"), text_color=("#0F172A", "#FEF3C7"))
        self.apply_daily_filter()

    def update_daily_view(self):
        """إعادة حساب وعرض بيانات اليوم المحدد وتحديث مؤشرات الـ KPIs بدقة وسرعة فائقة"""
        daily_data = self.engine.get_daily_attendance(self.selected_date)
        
        # حساب المؤشرات الإحصائية مباشرة بدون إعادة حساب
        total = len(daily_data)
        present = sum(1 for r in daily_data if r["is_present"])
        absent = sum(1 for r in daily_data if not r["is_present"] and "عطلة" not in r["status"])
        late = sum(1 for r in daily_data if r["late_minutes"] > 0)
        missing_checkout = sum(1 for r in daily_data if r["is_present"] and r["checkout_time"] == "--:--:--")

        self.kpi_cards["total"].configure(text=str(total))
        self.kpi_cards["present"].configure(text=str(present))
        self.kpi_cards["late"].configure(text=str(late))
        self.kpi_cards["absent"].configure(text=str(absent))
        self.kpi_cards["missing"].configure(text=str(missing_checkout))

        self.apply_daily_filter(daily_data)

    def apply_daily_filter(self, daily_data=None):
        """تطبيق الفلترة السريعة والبحث النصي على جدول اليوم مع الحفاظ على التحديد"""
        for item in self.daily_tree.get_children():
            self.daily_tree.delete(item)

        if daily_data is None:
            daily_data = self.engine.get_daily_attendance(self.selected_date)

        search_q = self.search_text.get().strip().lower()

        filtered = []
        for r in daily_data:
            # 1. فلتر الحالة
            if self.current_filter == "PRESENT" and not r["is_present"]:
                continue
            elif self.current_filter == "LATE" and r["late_minutes"] <= 0:
                continue
            elif self.current_filter == "ABSENT" and (r["is_present"] or "عطلة" in r["status"]):
                continue
            elif self.current_filter == "NO_CHECKOUT" and (not r["is_present"] or r["checkout_time"] != "--:--:--"):
                continue

            # 2. فلتر البحث النصي (الاسم أو الكود أو بيان الظروف)
            if search_q:
                match_id = search_q in str(r["enno"])
                match_name = search_q in r["name"].lower()
                match_cond = search_q in r.get("condition", "").lower()
                if not (match_id or match_name or match_cond):
                    continue

            filtered.append(r)

        selected_item_id = None

        # ملء الجدول
        for idx, r in enumerate(filtered, 1):
            if r.get("status_override") == "PRESENT" or (r.get("condition") and r["is_present"]):
                tag = "present"
            elif r.get("status_override") == "ABSENT":
                tag = "absent"
            elif r["status"] == "حاضر في الموعد":
                tag = "present"
            elif "متأخر" in r["status"]:
                tag = "late"
            elif "غائب" in r["status"]:
                tag = "absent"
            elif "بدون انصراف" in r["status"]:
                tag = "missing"
            elif "عطلة" in r["status"]:
                tag = "weekend"
            else:
                tag = "oddrow" if idx % 2 == 1 else "evenrow"

            late_disp = f"{r['late_minutes']} د" if r["late_minutes"] > 0 else "-"
            early_disp = f"{r['early_leave_minutes']} د" if r["early_leave_minutes"] > 0 else "-"
            cond_disp = r.get("condition", "")

            item_id = self.daily_tree.insert(
                "",
                "end",
                values=(
                    idx,
                    r["enno"],
                    r["name"],
                    cond_disp,
                    r["status"],
                    r["checkin_time"],
                    r["checkout_time"],
                    late_disp,
                    early_disp,
                    r["duration_str"],
                    r["notes"]
                ),
                tags=(tag,)
            )

            if self._selected_daily_enno == r["enno"]:
                selected_item_id = item_id

        # إعادة تحديد الموظف إذا كان محدداً مسبقاً
        if selected_item_id:
            self.daily_tree.selection_set(selected_item_id)
            self.daily_tree.see(selected_item_id)

        self.status_label.configure(
            text=f"عرض {len(filtered)} من أصل {len(daily_data)} موظف في يوم {self.selected_date.strftime('%Y-%m-%d')}"
        )

    # ==================== إدارة تعديل ظروف وتصاريح الموظفين ====================

    def on_daily_tree_selected(self, event=None):
        """عند تحديد موظف من جدول التقرير اليومي يتم تعبئة لوحة التعديل السريع فوراً"""
        sel = self.daily_tree.selection()
        if not sel:
            return

        vals = self.daily_tree.item(sel[0], "values")
        if not vals or len(vals) < 4:
            return

        try:
            enno = int(vals[1])
            name = vals[2]
            cond = vals[3]
        except (ValueError, IndexError):
            return

        self._selected_daily_enno = enno
        adj = self.engine.get_daily_adjustment(self.selected_date, enno)
        condition_val = adj.get("condition", cond)
        override_val = adj.get("status_override", "AUTO").upper()

        self.lbl_daily_sel_emp.configure(
            text=f"👤 الموظف المحدد: [{enno}] {name}  |  تاريخ: {self.selected_date.strftime('%Y-%m-%d')}"
        )

        self.entry_daily_condition.delete(0, "end")
        if condition_val:
            self.entry_daily_condition.insert(0, condition_val)

        if override_val == "PRESENT":
            self.seg_daily_status.set("🟢 حاضر (معتمد)")
        elif override_val == "ABSENT":
            self.seg_daily_status.set("🔴 غائب")
        else:
            self.seg_daily_status.set("⚙️ تلقائي (بصمة)")

    def on_daily_status_seg_changed(self, value=None):
        """استجابة سريعة عند تغيير زر الحالة"""
        pass

    def set_quick_reason(self, reason_text: str, target_status: str):
        """اختيار سبب سريع وتطبيقه وحفظه للموظف بضغطة زر واحدة"""
        if self._selected_daily_enno is None:
            messagebox.showinfo("تنبيه", "يرجى أولاً الضغط على اسم الموظف من الجدول لتحديد حالته.")
            return

        self.entry_daily_condition.delete(0, "end")
        self.entry_daily_condition.insert(0, reason_text)
        self.seg_daily_status.set(target_status)
        self.save_selected_daily_adjustment()

    def save_selected_daily_adjustment(self):
        """حفظ بيان الظروف أو التصريح وحالة الحضور/الغياب للموظف المحدد"""
        if self._selected_daily_enno is None:
            messagebox.showwarning("تنبيه", "يرجى تحديد موظف من الجدول لحفظ التعديل.")
            return

        enno = self._selected_daily_enno
        condition = self.entry_daily_condition.get().strip()
        seg_val = self.seg_daily_status.get()

        if "حاضر" in seg_val:
            status_override = "PRESENT"
        elif "غائب" in seg_val:
            status_override = "ABSENT"
        else:
            status_override = "AUTO"

        # حفظ التعديل في محرك البيانات
        self.engine.set_daily_adjustment(self.selected_date, enno, condition, status_override)

        # تحديث العرض
        self.update_daily_view()

        emp_info = self.engine.employees.get(enno, {})
        emp_name = emp_info.get("name", str(enno))
        self.status_label.configure(
            text=f"✅ تم حفظ حالة الموظف '{emp_name}' بنجاح ({condition if condition else seg_val})"
        )

    def clear_selected_daily_adjustment(self):
        """إلغاء التعديل اليدوي واستعادة الحساب التلقائي حسب البصمة الأصلية"""
        if self._selected_daily_enno is None:
            return

        enno = self._selected_daily_enno
        self.engine.delete_daily_adjustment(self.selected_date, enno)
        self.entry_daily_condition.delete(0, "end")
        self.seg_daily_status.set("⚙️ تلقائي (بصمة)")
        self.update_daily_view()

        emp_info = self.engine.employees.get(enno, {})
        emp_name = emp_info.get("name", str(enno))
        self.status_label.configure(
            text=f"🔄 تمت استعادة الحالة الأصلية لبصمة الموظف '{emp_name}'"
        )

    def on_daily_tree_double_click(self, event=None):
        """عند النقر المزدوج على موظف فتح نافذة التعديل السريع أو كارت الموظف"""
        sel = self.daily_tree.selection()
        if not sel:
            return
        vals = self.daily_tree.item(sel[0], "values")
        if vals and len(vals) > 1:
            try:
                enno = int(vals[1])
                self.open_quick_edit_modal(enno)
            except (ValueError, IndexError):
                pass

    def open_quick_edit_modal(self, enno: int):
        """نافذة منبثقة سريعة ومريحة لتعديل حالة الموظف وظروفه مع إمكانية فتح الكارت الكامل"""
        emp_info = self.engine.employees.get(enno, {"name": f"Employee {enno}", "enno": enno})
        name = emp_info.get("name", f"Employee {enno}")
        adj = self.engine.get_daily_adjustment(self.selected_date, enno)

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"تعديل حالة وظروف الموظف: {name}")
        dialog.geometry("540x420")
        dialog.minsize(480, 380)
        dialog.transient(self)
        dialog.grab_set()

        # إطار الرأس
        hdr = ctk.CTkFrame(dialog, corner_radius=0, fg_color=("#FFFFFF", "#120E08"))
        hdr.pack(fill="x", pady=0)

        ctk.CTkLabel(
            hdr,
            text=f"👤 كارت التعديل اليومي للموظف",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#F59E0B"
        ).pack(anchor="e", padx=20, pady=(10, 2))

        ctk.CTkLabel(
            hdr,
            text=f"الموظف: [{enno}] {name}  |  تاريخ اليوم: {self.selected_date.strftime('%Y-%m-%d')}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748B", "#D1A562")
        ).pack(anchor="e", padx=20, pady=(0, 10))

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)

        # 1. تحديد الحضور / الغياب
        ctk.CTkLabel(content, text="حالة التواجد لليوم:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(anchor="e", pady=(0, 5))

        curr_ov = adj.get("status_override", "AUTO").upper()
        seg_modal_status = ctk.CTkSegmentedButton(
            content,
            values=["⚙️ تلقائي (بصمة)", "🟢 حاضر (معتمد)", "🔴 غائب"],
            selected_color="#D97706",
            selected_hover_color="#B45309",
            unselected_color=("#E2E8F0", "#241808"),
            unselected_hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            height=34,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        if curr_ov == "PRESENT":
            seg_modal_status.set("🟢 حاضر (معتمد)")
        elif curr_ov == "ABSENT":
            seg_modal_status.set("🔴 غائب")
        else:
            seg_modal_status.set("⚙️ تلقائي (بصمة)")
        seg_modal_status.pack(fill="x", pady=(0, 15))

        # 2. بيان الظروف أو التصريح
        ctk.CTkLabel(content, text="📝 بيان الظروف / سبب الانصراف المبكر أو الغياب:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(anchor="e", pady=(0, 5))

        entry_modal_cond = ctk.CTkEntry(
            content,
            placeholder_text="اكتب هنا... مثلاً: أخذ تصريح انصراف / نزل معاينة موقع...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=("#FFFFFF", "#1F160A"),
            border_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            placeholder_text_color=("#94A3B8", "#78664D"),
            height=36
        )
        entry_modal_cond.insert(0, adj.get("condition", ""))
        entry_modal_cond.pack(fill="x", pady=(0, 10))

        # أزرار سريعة
        q_box = ctk.CTkFrame(content, fg_color="transparent")
        q_box.pack(fill="x", pady=(0, 15))

        modal_reasons = [
            ("🚗 معاينة", "نزل معاينة موقع", "🟢 حاضر (معتمد)"),
            ("📝 تصريح", "أخذ تصريح معتمد", "🟢 حاضر (معتمد)"),
            ("💼 مأمورية", "مأمورية عمل خارجية", "🟢 حاضر (معتمد)"),
            ("⏱️ إذن مبكر", "إذن انصراف مبكر", "🟢 حاضر (معتمد)"),
            ("🏖️ عارضة", "إجازة عارضة", "🔴 غائب")
        ]

        def put_q_modal(t, s):
            entry_modal_cond.delete(0, "end")
            entry_modal_cond.insert(0, t)
            seg_modal_status.set(s)

        for q_l, q_t, q_s in modal_reasons:
            ctk.CTkButton(
                q_box,
                text=q_l,
                width=65,
                height=26,
                fg_color=("#E2E8F0", "#241808"),
                hover_color=("#CBD5E1", "#3D2A0E"),
                text_color=("#0F172A", "#FEF3C7"),
                border_width=1,
                border_color=("#CBD5E1", "#3D2A0E"),
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                command=lambda t=q_t, s=q_s: put_q_modal(t, s)
            ).pack(side="right", padx=2)

        # 3. أزرار الحفظ والإجراءات
        btn_bar = ctk.CTkFrame(content, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(10, 0))

        def do_save_modal():
            cond = entry_modal_cond.get().strip()
            sv = seg_modal_status.get()
            ov = "PRESENT" if "حاضر" in sv else ("ABSENT" if "غائب" in sv else "AUTO")
            self.engine.set_daily_adjustment(self.selected_date, enno, cond, ov)
            self._selected_daily_enno = enno
            self.update_daily_view()
            dialog.destroy()

        def do_clear_modal():
            self.engine.delete_daily_adjustment(self.selected_date, enno)
            self._selected_daily_enno = enno
            self.update_daily_view()
            dialog.destroy()

        def do_open_ledger():
            dialog.destroy()
            self.open_employee_ledger_dialog(enno)

        btn_save_m = ctk.CTkButton(
            btn_bar,
            text="وتطبيق حفظ 💾",
            command=do_save_modal,
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            width=120,
            height=34
        )
        btn_save_m.pack(side="right", padx=4)

        btn_clear_m = ctk.CTkButton(
            btn_bar,
            text="الأصل استعادة 🔄",
            command=do_clear_modal,
            fg_color=("#94A3B8", "#241808"),
            hover_color=("#64748B", "#3D2A0E"),
            text_color=("#0F172A", "#FEF3C7"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E"),
            width=100,
            height=34
        )
        btn_clear_m.pack(side="right", padx=4)

        btn_full_card = ctk.CTkButton(
            btn_bar,
            text="الكامل الموظف كارت 👤",
            command=do_open_ledger,
            fg_color="#F59E0B",
            hover_color="#D97706",
            text_color="#FFFFFF",
            width=140,
            height=34
        )
        btn_full_card.pack(side="left", padx=4)

    def update_period_view(self):
        """تحديث جدول الملخص الدوري والشهري"""
        try:
            start_d = datetime.datetime.strptime(self.combo_from_date.get(), "%Y-%m-%d").date()
            end_d = datetime.datetime.strptime(self.combo_to_date.get(), "%Y-%m-%d").date()
        except Exception:
            return

        if start_d > end_d:
            messagebox.showwarning("تنبيه", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")
            return

        for item in self.monthly_tree.get_children():
            self.monthly_tree.delete(item)

        period_data = self.engine.get_period_summary(start_d, end_d)
        for idx, r in enumerate(period_data, 1):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            perm_h_s = f"{r.get('permission_hours', 0.0)} س"
            if r.get("is_permission_exceeded"):
                perm_pen_s = "خصم 1 يوم"
            else:
                perm_pen_s = "-"

            self.monthly_tree.insert(
                "",
                "end",
                values=(
                    idx,
                    r["enno"],
                    r["name"],
                    r["total_working_days"],
                    r["days_present"],
                    r["days_absent"],
                    r["days_late"],
                    r["total_late_minutes"],
                    perm_h_s,
                    perm_pen_s,
                    r["days_missing_checkout"],
                    f"{r['total_hours_worked']} س",
                    f"{r['attendance_percentage']}%"
                ),
                tags=(tag,)
            )

    # ==================== بطاقة كشف حساب الموظف الشهري (كارت الموظف) ====================

    def open_ledger_from_daily(self):
        """فتح كارت الموظف المحدد في جدول اليوم"""
        sel = self.daily_tree.selection()
        enno = None
        if sel:
            enno = int(self.daily_tree.item(sel[0], "values")[1])
        self.open_employee_ledger_dialog(enno)

    def open_ledger_from_monthly(self):
        """فتح كارت الموظف المحدد في جدول الملخص الدوري"""
        sel = self.monthly_tree.selection()
        enno = None
        if sel:
            enno = int(self.monthly_tree.item(sel[0], "values")[1])
        self.open_employee_ledger_dialog(enno)

    def open_employee_ledger_dialog(self, default_enno=None):
        """نافذة كارت الموظف الفردي والسجل اليومي المفصل"""
        if not self.engine.employees:
            messagebox.showwarning("تنبيه", "لا توجد بيانات موظفين لعرضها.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("بطاقة كشف الحضور والانصراف الفردي (كارت الموظف)")
        dialog.geometry("980x700")
        dialog.minsize(860, 580)
        dialog.transient(self)
        dialog.grab_set()

        # شريط التحكم العلوي
        ctrl_frame = ctk.CTkFrame(dialog, corner_radius=0, fg_color=("#FFFFFF", "#120E08"))
        ctrl_frame.pack(fill="x", padx=0, pady=0)

        # الجانب الأيمن: اختيار الموظف والتواريخ
        r_box = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        r_box.pack(side="right", padx=10, pady=8)

        emp_choices = [f"{e['enno']} - {e['name']}" for e in sorted(self.engine.employees.values(), key=lambda x: x['enno'])]
        
        lbl_emp = ctk.CTkLabel(r_box, text="اختر الموظف:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#F59E0B")
        lbl_emp.pack(side="right", padx=4)

        combo_emp = ctk.CTkComboBox(r_box, values=emp_choices, width=180)
        if default_enno:
            matched = next((c for c in emp_choices if c.startswith(f"{default_enno} -")), None)
            if matched:
                combo_emp.set(matched)
            else:
                combo_emp.set(emp_choices[0])
        else:
            combo_emp.set(emp_choices[0])
        combo_emp.pack(side="right", padx=4)

        # التواريخ
        date_strings = [d.strftime("%Y-%m-%d") for d in self.engine.available_dates] if self.engine.available_dates else []

        lbl_to = ctk.CTkLabel(r_box, text="إلى:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        lbl_to.pack(side="right", padx=(8, 2))

        combo_l_to = ctk.CTkComboBox(r_box, values=date_strings, width=110)
        if date_strings:
            combo_l_to.set(date_strings[0])
        combo_l_to.pack(side="right", padx=3)

        lbl_from = ctk.CTkLabel(r_box, text="من:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        lbl_from.pack(side="right", padx=(8, 2))

        combo_l_from = ctk.CTkComboBox(r_box, values=list(reversed(date_strings)), width=110)
        if date_strings:
            combo_l_from.set(date_strings[-1])
        combo_l_from.pack(side="right", padx=3)

        # الجانب الأيسر: أزرار التحديث والتصدير
        l_box = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        l_box.pack(side="left", padx=10, pady=8)

        btn_export_card = ctk.CTkButton(
            l_box,
            text="Excel إلى الكارت تصدير 📥",
            fg_color="#15803D",
            hover_color="#166534",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=160,
            height=30
        )
        btn_export_card.pack(side="left", padx=4)

        btn_refresh_card = ctk.CTkButton(
            l_box,
            text="عرض الكارت 🔄",
            fg_color="#D97706",
            hover_color="#B45309",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=110,
            height=30
        )
        btn_refresh_card.pack(side="left", padx=4)

        # الحاوية الرئيسية
        main_box = ctk.CTkFrame(dialog, fg_color="transparent")
        main_box.pack(fill="both", expand=True, padx=12, pady=8)

        # بطاقات المؤشرات الإحصائية للموظف (5 كروت) بنمط عنبري هادئ وأنيق
        kpi_row = ctk.CTkFrame(main_box, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(0, 8))

        for i in range(5):
            kpi_row.columnconfigure(i, weight=1)

        kpi_defs = [
            ("days", "أيام الحضور والعمل", "0 / 0", "#10B981"),
            ("absent", "أيام الغياب", "0", "#EF4444"),
            ("late", "دقائق التأخير", "0 د (0 مرات)", "#F59E0B"),
            ("permission", "رصيد الأذونات الشهرية", "0.0 / 0.0 س", "#818CF8"),
            ("hours", "إجمالي ساعات العمل", "0.0 س", "#D97706")
        ]

        card_labels = {}
        for ci, (k_key, k_txt, k_val, k_clr) in enumerate(kpi_defs):
            cd = ctk.CTkFrame(
                kpi_row,
                corner_radius=8,
                fg_color=("#F8FAFC", "#171005"),
                border_width=1.5,
                border_color=("#CBD5E1", "#3D2A0E")
            )
            cd.grid(row=0, column=ci, padx=3, pady=2, sticky="nsew")

            v_lbl = ctk.CTkLabel(cd, text=k_val, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=k_clr)
            v_lbl.pack(pady=(4, 1))

            t_lbl = ctk.CTkLabel(cd, text=k_txt, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=("#475569", "#FEF3C7"))
            t_lbl.pack(pady=(1, 4))

            card_labels[k_key] = v_lbl

        # جدول الأيام المفصل
        table_box = ctk.CTkFrame(main_box, corner_radius=8, fg_color=("#F8FAFC", "#171005"), border_width=1, border_color=("#CBD5E1", "#3D2A0E"))
        table_box.pack(fill="both", expand=True)

        cols = ("idx", "day_name", "date", "condition", "status", "checkin", "checkout", "late", "early", "hours", "notes")
        ledger_tree = ttk.Treeview(table_box, columns=cols, show="headings", selectmode="browse")

        hdrs = {
            "idx": ("م", 35, "center"),
            "day_name": ("اليوم", 75, "center"),
            "date": ("التاريخ", 95, "center"),
            "condition": ("📝 بيان الظروف / التصريح", 160, "w"),
            "status": ("الحالة", 120, "center"),
            "checkin": ("وقت الحضور", 90, "center"),
            "checkout": ("وقت الانصراف", 90, "center"),
            "late": ("التأخير (د)", 75, "center"),
            "early": ("مغادرة مبكرة", 75, "center"),
            "hours": ("ساعات العمل", 85, "center"),
            "notes": ("ملاحظات", 160, "w")
        }

        for c_id, (c_name, c_width, c_align) in hdrs.items():
            ledger_tree.heading(c_id, text=c_name)
            ledger_tree.column(c_id, width=c_width, anchor=c_align)

        vs = ttk.Scrollbar(table_box, orient="vertical", command=ledger_tree.yview)
        hs = ttk.Scrollbar(table_box, orient="horizontal", command=ledger_tree.xview)
        ledger_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")
        ledger_tree.pack(fill="both", expand=True)

        self.apply_tree_styles(ledger_tree)

        # شريط تعديل اليوم المحدد في كارت الموظف
        led_edit_box = ctk.CTkFrame(
            main_box,
            corner_radius=8,
            fg_color=("#F8FAFC", "#171005"),
            border_width=1.5,
            border_color=("#CBD5E1", "#3D2A0E")
        )
        led_edit_box.pack(fill="x", pady=(8, 0))

        led_r1 = ctk.CTkFrame(led_edit_box, fg_color="transparent")
        led_r1.pack(fill="x", padx=12, pady=(6, 2))

        lbl_led_sel = ctk.CTkLabel(
            led_r1,
            text="👈 اضغط على أي يوم من الجدول لتعديل حالته أو إثبات الظرف (تصريح / معاينة):",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#F59E0B"
        )
        lbl_led_sel.pack(side="right", padx=5)

        seg_led_st = ctk.CTkSegmentedButton(
            led_r1,
            values=["⚙️ تلقائي", "🟢 حاضر (معتمد)", "🔴 غائب"],
            selected_color="#D97706",
            selected_hover_color="#B45309",
            unselected_color=("#E2E8F0", "#241808"),
            unselected_hover_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            width=240,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        seg_led_st.set("⚙️ تلقائي")
        seg_led_st.pack(side="left", padx=5)

        lbl_led_prompt = ctk.CTkLabel(
            led_r1,
            text="تحديد الحالة:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#1E293B", "#FEF3C7")
        )
        lbl_led_prompt.pack(side="left", padx=(5, 2))

        led_r2 = ctk.CTkFrame(led_edit_box, fg_color="transparent")
        led_r2.pack(fill="x", padx=12, pady=(2, 6))

        entry_led_c = ctk.CTkEntry(
            led_r2,
            placeholder_text="اكتب بيان الظروف أو التصريح لهذا اليوم (مثلاً: أخذ تصريح انصراف مبكر / نزل معاينة موقع)...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#FFFFFF", "#1F160A"),
            border_color=("#CBD5E1", "#3D2A0E"),
            text_color=("#0F172A", "#FFFBEB"),
            placeholder_text_color=("#94A3B8", "#78664D"),
            height=32
        )
        entry_led_c.pack(side="right", fill="x", expand=True, padx=5)

        selected_ledger_date = [None]

        def on_ledger_select(event=None):
            sel_item = ledger_tree.selection()
            if not sel_item:
                return
            v = ledger_tree.item(sel_item[0], "values")
            if len(v) >= 4:
                d_str = v[2]
                selected_ledger_date[0] = d_str
                try:
                    c_enno = int(combo_emp.get().split(" - ")[0])
                except Exception:
                    return
                adj_d = self.engine.get_daily_adjustment(d_str, c_enno)
                lbl_led_sel.configure(text=f"📅 اليوم المحدد: {v[1]} ({d_str})")
                entry_led_c.delete(0, "end")
                if adj_d.get("condition"):
                    entry_led_c.insert(0, adj_d["condition"])
                ov_st = adj_d.get("status_override", "AUTO").upper()
                if ov_st == "PRESENT":
                    seg_led_st.set("🟢 حاضر (معتمد)")
                elif ov_st == "ABSENT":
                    seg_led_st.set("🔴 غائب")
                else:
                    seg_led_st.set("⚙️ تلقائي")

        ledger_tree.bind("<<TreeviewSelect>>", on_ledger_select)

        def save_ledger_day():
            d_str = selected_ledger_date[0]
            if not d_str:
                messagebox.showwarning("تنبيه", "يرجى اختيار يوم من الجدول أولاً.")
                return
            try:
                c_enno = int(combo_emp.get().split(" - ")[0])
            except Exception:
                return
            cond = entry_led_c.get().strip()
            sv = seg_led_st.get()
            ov = "PRESENT" if "حاضر" in sv else ("ABSENT" if "غائب" in sv else "AUTO")
            self.engine.set_daily_adjustment(d_str, c_enno, cond, ov)
            load_current_ledger()
            self.update_daily_view()

        def clear_ledger_day():
            d_str = selected_ledger_date[0]
            if not d_str:
                return
            try:
                c_enno = int(combo_emp.get().split(" - ")[0])
            except Exception:
                return
            self.engine.delete_daily_adjustment(d_str, c_enno)
            entry_led_c.delete(0, "end")
            seg_led_st.set("⚙️ تلقائي")
            load_current_ledger()
            self.update_daily_view()

        btn_l_save = ctk.CTkButton(
            led_r2,
            text="اليوم حفظ 💾",
            command=save_ledger_day,
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=100,
            height=30
        )
        btn_l_save.pack(side="left", padx=3)

        btn_l_clear = ctk.CTkButton(
            led_r2,
            text="الأصل استعادة 🔄",
            command=clear_ledger_day,
            fg_color=("#94A3B8", "#241808"),
            hover_color=("#64748B", "#3D2A0E"),
            text_color=("#0F172A", "#FEF3C7"),
            border_width=1,
            border_color=("#CBD5E1", "#3D2A0E"),
            width=90,
            height=30
        )
        btn_l_clear.pack(side="left", padx=3)

        def load_current_ledger():
            try:
                raw_c = combo_emp.get()
                curr_enno = int(raw_c.split(" - ")[0])
                d_from = datetime.datetime.strptime(combo_l_from.get(), "%Y-%m-%d").date()
                d_to = datetime.datetime.strptime(combo_l_to.get(), "%Y-%m-%d").date()
            except Exception:
                return

            if d_from > d_to:
                messagebox.showwarning("تنبيه", "تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")
                return

            ledger = self.engine.get_employee_ledger(curr_enno, d_from, d_to)
            s = ledger["summary"]

            # تحديث الكروت بتنسيق مقروء وأنيق ومختصر يناسب العرض بدقة
            card_labels["days"].configure(text=f"{s['days_present']} / {s['total_working_days']} يوم ({s['attendance_percentage']}%)")
            
            abs_txt = f"{s['days_absent']} يوم غياب"
            if s.get("permission_penalty_days", 0) > 0:
                abs_txt = f"{s['days_absent']} يوم (يشمل خصم إذن)"
            card_labels["absent"].configure(text=abs_txt)

            card_labels["late"].configure(text=f"{s['total_late_minutes']} دقيقة ({s['days_late']} مرات)")
            
            # كارت رصيد الأذونات
            perm_h = s.get("permission_hours", 0.0)
            max_p = s.get("max_permission_hours", 4.0)
            if s.get("is_permission_exceeded"):
                perm_txt = f"{perm_h}س / {max_p}س (⚠️ تجاوز الحد)"
                card_labels["permission"].configure(text=perm_txt, text_color="#EF4444")
            else:
                rem_h = round(max(0.0, max_p - perm_h), 1)
                perm_txt = f"{perm_h}س / {max_p}س (متبقي {rem_h}س)"
                card_labels["permission"].configure(text=perm_txt, text_color="#818CF8")

            card_labels["hours"].configure(text=f"{s['total_hours_worked']} ساعة عمل")

            # مسح وتعبئة الجدول
            for item in ledger_tree.get_children():
                ledger_tree.delete(item)

            for idx, r in enumerate(ledger["days"], 1):
                if r["status"] == "حاضر في الموعد" or (r.get("condition") and r["is_present"]):
                    tag = "present"
                elif "متأخر" in r["status"]:
                    tag = "late"
                elif r["status"] == "غائب":
                    tag = "absent"
                elif r["is_weekend"]:
                    tag = "weekend"
                else:
                    tag = "evenrow" if idx % 2 == 0 else "oddrow"

                late_s = f"{r['late_minutes']} د" if r['late_minutes'] > 0 else "-"
                early_s = f"{r['early_leave_minutes']} د" if r['early_leave_minutes'] > 0 else "-"
                cond_s = r.get("condition", "")

                ledger_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        r["day_name"],
                        r["date_str"],
                        cond_s,
                        r["status"],
                        r["checkin_time"],
                        r["checkout_time"],
                        late_s,
                        early_s,
                        r["duration_str"],
                        r["notes"]
                    ),
                    tags=(tag,)
                )

        def export_current_ledger():
            try:
                raw_c = combo_emp.get()
                curr_enno = int(raw_c.split(" - ")[0])
                emp_n = raw_c.split(" - ")[1]
                d_from = datetime.datetime.strptime(combo_l_from.get(), "%Y-%m-%d").date()
                d_to = datetime.datetime.strptime(combo_l_to.get(), "%Y-%m-%d").date()
            except Exception:
                return

            def_name = f"كارت_حضور_{emp_n}_{curr_enno}_{d_from.strftime('%Y_%m')}.xlsx"
            save_p = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx")],
                initialfile=def_name,
                title="حفظ كارت الموظف بصيغة Excel"
            )
            if save_p:
                ok = self.engine.export_employee_ledger_to_excel(curr_enno, d_from, d_to, save_p)
                if ok:
                    messagebox.showinfo("نجاح التصدير", f"تم تصدير كارت الموظف بنجاح إلى:\n{save_p}")
                else:
                    messagebox.showerror("خطأ", "تعذر تصدير ملف Excel.")

        combo_emp.configure(command=lambda e: load_current_ledger())
        btn_refresh_card.configure(command=load_current_ledger)
        btn_export_card.configure(command=export_current_ledger)

        # تحميل مبدئي
        load_current_ledger()

    def populate_raw_table(self):
        """ملء جدول الحركات الخام"""
        self.filter_raw_table()

    def filter_raw_table(self):
        if self.engine.df_clean is None:
            return

        for item in self.raw_tree.get_children():
            self.raw_tree.delete(item)

        df = self.engine.df_clean
        query = self.raw_search_var.get().strip().lower()

        # نمط التحقق
        mode_names = {1: "بصمة إصبع (Finger)", 2: "بطاقة (Card)", 3: "كلمة مرور (Password)"}
        inout_names = {0: "عام / غير محدد", 5: "دخول (Check-In)", 6: "خروج (Check-Out)"}

        # فرز وعرض آخر 500 حركة للسرعة إذا لم يكن هناك بحث محدد
        if query:
            match_mask = (
                df['Name'].str.lower().str.contains(query, na=False) |
                df['EnNo'].astype(str).str.contains(query, na=False) |
                df['DateTime'].astype(str).str.contains(query, na=False)
            )
            filtered_df = df[match_mask]
        else:
            filtered_df = df.tail(500)

        for idx, row in filtered_df.iterrows():
            m_code = int(row.get('Mode', 1))
            io_code = int(row.get('INOUT', 0))
            m_text = mode_names.get(m_code, str(m_code))
            io_text = inout_names.get(io_code, str(io_code))
            dt_str = str(row['DateTime'])

            self.raw_tree.insert(
                "",
                "end",
                values=(
                    row.get('No', idx + 1),
                    row.get('TMNo', 1),
                    row['EnNo'],
                    row['Name'],
                    m_text,
                    io_text,
                    dt_str
                )
            )

        self.raw_count_lbl.configure(text=f"إجمالي الحركات المعروضة: {len(filtered_df)}")

    def save_settings_action(self):
        """حفظ إعدادات الورديات ومواعيد العمل"""
        try:
            start_s = self.entry_shift_start.get().strip()
            end_s = self.entry_shift_end.get().strip()
            grace_m = int(self.entry_grace_mins.get().strip())
            early_m = int(self.entry_early_grace.get().strip())
            wk_choice = self.combo_weekend.get()
            auto_hire = self.var_auto_hire.get()

            # التحقق من صيغة الوقت
            datetime.datetime.strptime(start_s, "%H:%M")
            datetime.datetime.strptime(end_s, "%H:%M")

            if wk_choice == "الجمعة والسبت":
                wk_days = [4, 5]
            elif wk_choice == "الجمعة فقط":
                wk_days = [4]
            else:
                wk_days = []

            late_calc = getattr(self, "var_late_calc_mode", None)
            late_mode_val = late_calc.get() if late_calc else "after_grace"

            perm_hours_val = 4.0
            if hasattr(self, "entry_perm_hours"):
                try:
                    perm_hours_val = float(self.entry_perm_hours.get().strip())
                except ValueError:
                    perm_hours_val = 4.0

            new_cfg = {
                "shift_start": start_s,
                "shift_end": end_s,
                "grace_period_mins": grace_m,
                "early_departure_grace": early_m,
                "late_calc_mode": late_mode_val,
                "monthly_permission_hours": perm_hours_val,
                "weekend_days": wk_days,
                "auto_detect_hire_date": auto_hire
            }

            self.engine.save_config(new_cfg)
            self.update_daily_view()
            self.update_period_view()
            messagebox.showinfo("تم الحفظ", "تم حفظ إعدادات العمل وإعادة حساب التقارير بنجاح!")
        except Exception as e:
            messagebox.showerror("خطأ في البيانات", f"يرجى التأكد من صحة أوقات العمل والأرقام المدخلة:\n{e}")

    def export_daily_excel(self):
        """تصدير التقرير اليومي إلى Excel"""
        def_name = f"تقرير_حضور_بصمة_{self.selected_date.strftime('%Y_%m_%d')}.xlsx"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=def_name,
            title="حفظ تقرير اليوم بصيغة Excel"
        )
        if save_path:
            success = self.engine.export_daily_to_excel(self.selected_date, save_path)
            if success:
                messagebox.showinfo("نجاح التصدير", f"تم حفظ تقرير اليوم في:\n{save_path}")
            else:
                messagebox.showerror("خطأ", "حدث خطأ أثناء تصدير ملف Excel.")

    def export_period_excel(self):
        """تصدير التقرير الدوري إلى Excel"""
        try:
            start_d = datetime.datetime.strptime(self.combo_from_date.get(), "%Y-%m-%d").date()
            end_d = datetime.datetime.strptime(self.combo_to_date.get(), "%Y-%m-%d").date()
        except Exception:
            return

        def_name = f"تقرير_حضور_دوري_{start_d.strftime('%Y_%m_%d')}_إلى_{end_d.strftime('%Y_%m_%d')}.xlsx"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=def_name,
            title="حفظ التقرير الدوري بصيغة Excel"
        )
        if save_path:
            success = self.engine.export_period_to_excel(start_d, end_d, save_path)
            if success:
                messagebox.showinfo("نجاح التصدير", f"تم حفظ التقرير الدوري في:\n{save_path}")
            else:
                messagebox.showerror("خطأ", "حدث خطأ أثناء تصدير ملف Excel.")


if __name__ == "__main__":
    app = AttendanceApp()
    app.mainloop()
