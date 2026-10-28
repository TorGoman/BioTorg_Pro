# -*- coding: utf-8 -*-
"""
محرك معالجة بيانات البصمة - Advision / Realand Attendance Engine
يقوم بقراءة ملفات AGL_001 و GLG_001 وحساب الحضور والغياب والتأخير والانصراف وساعات العمل
"""

import os
import sys
import json
import datetime
from typing import Dict, List, Any, Optional, Union
import pandas as pd

def get_app_dir() -> str:
    """الحصول على المجلد الأساسي للبرنامج سواء كان يعمل ككود أو كملف تنفيذي EXE"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG_FILE = "attendance_config.json"
DEFAULT_ADJUSTMENTS_FILE = "attendance_adjustments.json"

DEFAULT_CONFIG = {
    "shift_start": "11:00",       # موعد بدء العمل الافتراضي (11:00 صباحاً)
    "shift_end": "19:00",         # موعد نهاية العمل الافتراضي (07:00 مساءً)
    "grace_period_mins": 15,     # فترة السماح بالتأخير (بالدقائق)
    "early_departure_grace": 10, # فترة السماح بالانصراف المبكر (بالدقائق)
    "late_calc_mode": "after_grace", # "after_grace": احتساب التأخير فقط لما بعد فترة السماح | "from_start": احتساب التأخير كاملاً من بداية الوردية
    "weekend_days": [4, 5],       # 4 = الجمعة، 5 = السبت (العطلة العامة الافتراضية)
    "employee_weekends": {},      # إجازات مخصصة لكل موظف (مثل فريق المبيعات): {"1": [1], "2": [2]}
    "monthly_permission_hours": 4.0, # عدد ساعات الإذن المسموح بها شهرياً (إذا تجاوزها يخصم يوم)
    "auto_detect_hire_date": True, # عدم احتساب الموظف غائباً قبل تاريخ أول بصمة له
    "hr_settings": {
        "enabled": False,                       # إمكانية تفعيل أو إلغاء تفعيل موديول الرواتب
        "month_days_basis": 30,                 # أساس احتساب أجر اليوم (30 يوماً أو أيام العمل الفعلية)
        "shift_hours": 7.0,                     # عدد ساعات العمل اليومية لاحتساب أجر الساعة
        "absence_penalty_multiplier": 1.0,      # معامل خصم يوم الغياب (1 = خصم يوم، 1.5 = يوم ونصف، 2 = يومين)
        "late_deduction_type": "minutes",       # "minutes" (بالدقائق) أو "tiers" (شرائح تأخير)
        "late_minute_multiplier": 1.0,          # معامل خصم دقيقة التأخير
        "late_tiers": [                         # شرائح التأخير اليومية
            {"max_mins": 15, "day_fraction": 0.0},
            {"max_mins": 30, "day_fraction": 0.25},
            {"max_mins": 60, "day_fraction": 0.50},
            {"max_mins": 9999, "day_fraction": 1.0}
        ],
        "early_leave_deduction": True,          # احتساب خصم الانصراف المبكر
        "overtime_multiplier": 1.5,             # معامل احتساب الساعات الإضافية
        "employees_hr": {}                      # كود الموظف -> {basic_salary, allowances, bonuses, deductions, job_title}
    }
}

class AttendanceEngine:
    def __init__(self, data_file_path: Optional[str] = None):
        self.config = self.load_config()
        self.adjustments = self.load_adjustments()
        self.df_raw: Optional[pd.DataFrame] = None
        self.df_clean: Optional[pd.DataFrame] = None
        self.employees: Dict[int, Dict[str, Any]] = {}
        self.available_dates: List[datetime.date] = []
        self._day_logs_cache: Dict[datetime.date, Any] = {}
        self.current_file_path = data_file_path

        if data_file_path and os.path.exists(data_file_path):
            self.load_file(data_file_path)

    def load_config(self) -> dict:
        config_path = os.path.join(get_app_dir(), DEFAULT_CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    merged = dict(DEFAULT_CONFIG)
                    for k, v in cfg.items():
                        if k == "hr_settings" and isinstance(v, dict):
                            hr_def = dict(DEFAULT_CONFIG.get("hr_settings", {}))
                            hr_def.update(v)
                            # دمج بيانات الموظفين إن وجدت
                            if "employees_hr" in v and isinstance(v["employees_hr"], dict):
                                hr_def["employees_hr"] = dict(v["employees_hr"])
                            merged["hr_settings"] = hr_def
                        else:
                            merged[k] = v
                    return merged
            except Exception:
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def save_config(self, new_config: dict) -> bool:
        self.config.update(new_config)
        config_path = os.path.join(get_app_dir(), DEFAULT_CONFIG_FILE)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print("Error saving config:", e)
            return False

    def load_adjustments(self) -> dict:
        """تحميل قائمة التعديلات اليدوية والتصاريح والظروف الخاصة بالموظفين"""
        adj_path = os.path.join(get_app_dir(), DEFAULT_ADJUSTMENTS_FILE)
        if os.path.exists(adj_path):
            try:
                with open(adj_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print("Error loading adjustments:", e)
                return {}
        return {}

    def save_adjustments(self) -> bool:
        """حفظ التعديلات اليدوية والتصاريح في ملف JSON"""
        adj_path = os.path.join(get_app_dir(), DEFAULT_ADJUSTMENTS_FILE)
        try:
            with open(adj_path, "w", encoding="utf-8") as f:
                json.dump(self.adjustments, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print("Error saving adjustments:", e)
            return False

    def get_daily_adjustment(self, target_date: Any, enno: int) -> dict:
        """جلب التعديل اليدوي أو الظرف المسجل لموظف في يوم محدد"""
        d_str = target_date.strftime("%Y-%m-%d") if isinstance(target_date, (datetime.date, datetime.datetime)) else str(target_date)
        key = f"{d_str}_{enno}"
        return self.adjustments.get(key, {})

    def set_daily_adjustment(self, target_date: Any, enno: int, condition: str = "", status_override: str = "AUTO") -> bool:
        """
        حفظ أو تعديل حالة الموظف وظروفه ليوم محدد
        condition: بيان الظرف مثل (أخذ تصريح، نزل معاينة، إذن انصراف مبكر)
        status_override: 'PRESENT' (حاضر), 'ABSENT' (غائب), 'AUTO' (تلقائي حسب البصمة)
        """
        d_str = target_date.strftime("%Y-%m-%d") if isinstance(target_date, (datetime.date, datetime.datetime)) else str(target_date)
        key = f"{d_str}_{enno}"
        cond_clean = condition.strip() if condition else ""
        stat_clean = status_override.strip().upper() if status_override else "AUTO"

        # إذا كانت الحالة تلقائية وبدون بيان ظرف، نحذف القيد لتنظيف الملف
        if not cond_clean and stat_clean in ("AUTO", ""):
            if key in self.adjustments:
                del self.adjustments[key]
                return self.save_adjustments()
            return True

        self.adjustments[key] = {
            "date": d_str,
            "enno": int(enno),
            "condition": cond_clean,
            "status_override": stat_clean,
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return self.save_adjustments()

    def delete_daily_adjustment(self, target_date: Any, enno: int) -> bool:
        """حذف التعديل اليدوي واستعادة الحالة التلقائية الأصلية"""
        d_str = target_date.strftime("%Y-%m-%d") if isinstance(target_date, (datetime.date, datetime.datetime)) else str(target_date)
        key = f"{d_str}_{enno}"
        if key in self.adjustments:
            del self.adjustments[key]
            return self.save_adjustments()
        return True

    def get_employee_weekend_days(self, enno: int) -> List[int]:
        """
        جلب أيام العطلة الأسبوعية المخصصة للموظف (مثلاً لموظفي المبيعات).
        إذا لم تكن له عطلة خاصة محددة، يتم تطبيق العطلة العامة للمنشأة من الإعدادات.
        الأيام بأرقام بايثون: 0=الإثنين, 1=الثلاثاء, 2=الأربعاء, 3=الخميس, 4=الجمعة, 5=السبت, 6=الأحد.
        """
        emp_weekends = self.config.get("employee_weekends", {})
        enno_str = str(enno)
        if enno_str in emp_weekends and isinstance(emp_weekends[enno_str], list):
            return emp_weekends[enno_str]
        # بديل في حال كان المفتاح رقماً صحيحاً
        if enno in emp_weekends and isinstance(emp_weekends[enno], list):
            return emp_weekends[enno]
        # التراجع إلى العطلة العامة الافتراضية
        return self.config.get("weekend_days", [4, 5])

    def set_employee_weekend_days(self, enno: int, days: List[int]) -> bool:
        """
        تعيين أيام الإجازة الأسبوعية الخاصة بموظف وحفظها في الإعدادات.
        إذا تم تمرير قائمة فارغة أو None، يتم إزالة التخصيص ليعود للعطلة العامة.
        """
        if "employee_weekends" not in self.config:
            self.config["employee_weekends"] = {}
        
        enno_str = str(enno)
        if days is None:
            if enno_str in self.config["employee_weekends"]:
                del self.config["employee_weekends"][enno_str]
        else:
            self.config["employee_weekends"][enno_str] = [int(d) for d in days]
        
        return self.save_config({})

    def load_file(self, file_path: str) -> bool:
        """قراءة وتحليل ملف بصمة Advision / Realand (TXT)"""
        if not os.path.exists(file_path):
            return False

        try:
            # ملفات Realand و Advision تأتي مفصولة بـ TAB (\t)
            try:
                df = pd.read_csv(file_path, sep='\t')
            except Exception:
                df = pd.read_csv(file_path, sep=r'\s+', engine='python')
            
            # تنظيف أسماء الأعمدة
            df.columns = [c.strip() for c in df.columns]

            # معالجة عمود DateTime في حال تم فصله في القراءة
            if 'Date' in df.columns and 'Time' in df.columns and 'DateTime' not in df.columns:
                df['DateTime'] = df['Date'].astype(str) + ' ' + df['Time'].astype(str)

            # تنظيف الأعمدة
            df['EnNo'] = pd.to_numeric(df['EnNo'], errors='coerce')
            df = df.dropna(subset=['EnNo'])
            df['EnNo'] = df['EnNo'].astype(int)

            if 'Name' in df.columns:
                df['Name'] = df['Name'].fillna('').astype(str).str.strip()
            else:
                df['Name'] = df['EnNo'].apply(lambda x: f"Employee {x}")

            df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
            df = df.dropna(subset=['DateTime'])
            df['Date'] = df['DateTime'].dt.date
            df['Time'] = df['DateTime'].dt.time

            # الترتيب الزمني وحذف البصمات المكررة بالخطأ في أقل من 60 ثانية (Ghost / Double Punches)
            df = df.sort_values(by=['DateTime']).reset_index(drop=True)
            time_diff = df.groupby('EnNo')['DateTime'].diff().dt.total_seconds()
            df = df[time_diff.isna() | (time_diff >= 60)].reset_index(drop=True)

            self.df_clean = df
            self.current_file_path = file_path

            # بناء قائمة الموظفين وتواريخ أول وآخر تسجيل والتخزين المؤقت السريع لكل يوم
            self._build_employee_directory()
            self._day_logs_cache = {d: group.groupby('EnNo') for d, group in self.df_clean.groupby('Date')}
            self.available_dates = sorted(self.df_clean['Date'].unique(), reverse=True)
            return True
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            return False

    def _build_employee_directory(self):
        """استخراج سجل كامل بالموظفين وتواريخ نشاطهم"""
        self.employees = {}
        if self.df_clean is None or self.df_clean.empty:
            return

        grouped = self.df_clean.groupby('EnNo')
        for enno, group in grouped:
            # الاسم الأكثر تكراراً للموظف
            names = group['Name'][group['Name'] != '']
            name = names.mode()[0] if not names.empty else f"Employee {enno}"
            first_date = group['Date'].min()
            last_date = group['Date'].max()
            total_logs = len(group)

            self.employees[enno] = {
                "enno": enno,
                "name": name,
                "first_date": first_date,
                "last_date": last_date,
                "total_logs": total_logs,
                "active": True
            }

    def get_kpis_for_date(self, target_date: datetime.date) -> dict:
        """حساب المؤشرات الإحصائية السريعة لليوم المحدد"""
        daily_records = self.get_daily_attendance(target_date)
        total = len(daily_records)
        present = sum(1 for r in daily_records if r["is_present"])
        absent = sum(1 for r in daily_records if not r["is_present"] and "عطلة" not in r["status"])
        late = sum(1 for r in daily_records if r["late_minutes"] > 0)
        missing_checkout = sum(1 for r in daily_records if r["is_present"] and r["checkout_time"] == "--:--:--")
        weekend = sum(1 for r in daily_records if "عطلة أسبوعية" in r["status"])

        return {
            "total_employees": total,
            "present": present,
            "absent": absent,
            "late": late,
            "missing_checkout": missing_checkout,
            "weekend": weekend
        }

    def parse_time_str(self, t_str: str) -> datetime.time:
        """تحويل نص HH:MM إلى datetime.time"""
        parts = t_str.strip().split(':')
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return datetime.time(h, m)

    def get_daily_attendance(self, target_date: datetime.date) -> List[Dict[str, Any]]:
        """حساب الحضور والغياب والتأخير والانصراف لجميع الموظفين في تاريخ محدد مع تطبيق التعديلات والظروف"""
        results = []
        if self.df_clean is None or not self.employees:
            return results

        # استخراج سجلات اليوم المطلوب بسرعة فائقة عبر التخزين المؤقت المسبق
        if hasattr(self, "_day_logs_cache") and target_date in self._day_logs_cache:
            day_logs_by_emp = self._day_logs_cache[target_date]
        else:
            day_logs = self.df_clean[self.df_clean['Date'] == target_date]
            day_logs_by_emp = day_logs.groupby('EnNo')

        # قراءة إعدادات الوردية
        shift_start = self.parse_time_str(self.config.get("shift_start", "11:00"))
        shift_end = self.parse_time_str(self.config.get("shift_end", "19:00"))
        grace_mins = self.config.get("grace_period_mins", 15)
        early_grace_mins = self.config.get("early_departure_grace", 10)
        late_calc_mode = self.config.get("late_calc_mode", "after_grace")
        auto_hire = self.config.get("auto_detect_hire_date", True)
        default_shift_hours = float(self.config.get("hr_settings", {}).get("shift_hours", 7.0))

        # تحويل وقت بدء الوردية إلى دقائق لحساب التأخير
        shift_start_mins = shift_start.hour * 60 + shift_start.minute
        shift_end_mins = shift_end.hour * 60 + shift_end.minute

        for enno, emp_info in sorted(self.employees.items()):
            name = emp_info["name"]

            # هل اليوم عطلة أسبوعية خاصة بهذا الموظف؟
            emp_wk_days = self.get_employee_weekend_days(enno)
            is_weekend = target_date.weekday() in emp_wk_days

            # إذا تم تفعيل الكشف التلقائي عن تاريخ التعيين، ولم يكن الموظف قد التحق بعد
            if auto_hire and target_date < emp_info["first_date"]:
                continue

            # استدعاء التعديل اليدوي أو بيان الظروف المسجل لهذا الموظف
            adj = self.get_daily_adjustment(target_date, enno)
            condition = adj.get("condition", "").strip()
            status_override = adj.get("status_override", "AUTO").upper()

            if enno in day_logs_by_emp.groups:
                # الموظف سجل بصمة في هذا اليوم
                emp_punches = day_logs_by_emp.get_group(enno).sort_values(by="DateTime")
                punch_datetimes = emp_punches['DateTime'].tolist()

                first_punch_dt = punch_datetimes[0]
                last_punch_dt = punch_datetimes[-1]

                checkin_time = first_punch_dt.time()
                checkin_str = checkin_time.strftime("%H:%M:%S")

                # هل توجد بصمة انصراف منفصلة؟
                if len(punch_datetimes) > 1 and last_punch_dt != first_punch_dt:
                    checkout_time = last_punch_dt.time()
                    checkout_str = checkout_time.strftime("%H:%M:%S")
                    duration_sec = (last_punch_dt - first_punch_dt).total_seconds()
                    hours_worked = round(duration_sec / 3600.0, 2)
                    duration_str = f"{int(hours_worked)}س {int((duration_sec % 3600) // 60)}د"
                else:
                    checkout_time = None
                    checkout_str = "--:--:--"
                    hours_worked = 0.0
                    duration_str = "بصمة واحدة"

                # حساب التأخير (بالدقائق):
                # إذا تجاوز فترة السماح، يُحسب التأخير من بعد فترة السماح فقط (أو من البداية حسب الإعدادات)
                actual_checkin_mins = checkin_time.hour * 60 + checkin_time.minute
                diff_checkin = actual_checkin_mins - shift_start_mins
                if diff_checkin > grace_mins:
                    if late_calc_mode == "after_grace":
                        late_minutes = diff_checkin - grace_mins
                    else:
                        late_minutes = diff_checkin
                else:
                    late_minutes = 0

                # حساب الانصراف المبكر (بالدقائق)
                early_leave_minutes = 0
                overtime_minutes = 0
                if checkout_time is not None:
                    actual_checkout_mins = checkout_time.hour * 60 + checkout_time.minute
                    diff_checkout = shift_end_mins - actual_checkout_mins
                    if diff_checkout > early_grace_mins:
                        if late_calc_mode == "after_grace":
                            early_leave_minutes = diff_checkout - early_grace_mins
                        else:
                            early_leave_minutes = diff_checkout
                    elif actual_checkout_mins > shift_end_mins:
                        overtime_minutes = actual_checkout_mins - shift_end_mins

                # تحديد الحالة التلقائية
                notes_list = []
                if checkout_time is None:
                    calc_status = "حاضر (بدون انصراف)"
                    notes_list.append("لم يسجل انصراف")
                elif late_minutes > 0 and early_leave_minutes > 0:
                    calc_status = "متأخر + انصراف مبكر"
                    notes_list.append(f"تأخير {late_minutes}د / مغادرة مبكرة {early_leave_minutes}د")
                elif late_minutes > 0:
                    calc_status = "حاضر (متأخر)"
                    notes_list.append(f"تأخير {late_minutes} دقيقة")
                elif early_leave_minutes > 0:
                    calc_status = "حاضر (انصراف مبكر)"
                    notes_list.append(f"مغادرة مبكرة {early_leave_minutes} دقيقة")
                else:
                    calc_status = "حاضر في الموعد"

                if overtime_minutes > 0:
                    notes_list.append(f"إضافي {overtime_minutes // 60}س {overtime_minutes % 60}د")

                if is_weekend:
                    notes_list.append("عمل في يوم عطلة")

                # تطبيق التعديلات اليدوية إن وجدت
                is_present = True
                if status_override == "ABSENT":
                    is_present = False
                    status = f"غائب ({condition})" if condition else "غائب (يدوي)"
                    late_minutes = 0
                    early_leave_minutes = 0
                    hours_worked = 0.0
                    duration_str = "0س 0د"
                    notes_str = f"غياب يدوي: {condition}" if condition else "غياب يدوي معتمد"
                elif status_override == "PRESENT":
                    is_present = True
                    if condition:
                        status = f"حاضر ({condition})"
                        # إسقاط غرامة الانصراف المبكر أو عدم تسجيل الانصراف في حال كان الموظف لديه تصريح أو نزل معاينة
                        early_leave_minutes = 0
                        clean_notes = [n for n in notes_list if "لم يسجل انصراف" not in n and "مغادرة مبكرة" not in n]
                        notes_str = f"تصريح/معاينة: {condition}" + (f" | {' | '.join(clean_notes)}" if clean_notes else "")
                    else:
                        status = "حاضر (معتمد)"
                        notes_str = " | ".join(notes_list) if notes_list else "حضور معتمد"
                else: # AUTO
                    is_present = True
                    if condition:
                        status = f"{calc_status} ({condition})"
                        notes_str = f"{condition} | " + (" | ".join(notes_list) if notes_list else "منضبط")
                    else:
                        status = calc_status
                        notes_str = " | ".join(notes_list) if notes_list else "منضبط"

                results.append({
                    "enno": enno,
                    "name": name,
                    "date": target_date,
                    "is_present": is_present,
                    "status": status,
                    "checkin_time": checkin_str,
                    "checkout_time": checkout_str,
                    "late_minutes": late_minutes,
                    "early_leave_minutes": early_leave_minutes,
                    "overtime_minutes": overtime_minutes,
                    "hours_worked": hours_worked,
                    "duration_str": duration_str,
                    "punches_count": len(emp_punches),
                    "notes": notes_str,
                    "condition": condition,
                    "status_override": status_override
                })

            else:
                # الموظف لم يسجل بصمة في هذا اليوم
                if status_override == "PRESENT":
                    is_present = True
                    shift_h = default_shift_hours
                    status = f"حاضر ({condition})" if condition else "حاضر (تصريح/معاينة)"
                    notes_str = f"حضور معتمد: {condition}" if condition else "حضور معتمد بتصريح"
                    checkin_str = "--:--:--"
                    checkout_str = "--:--:--"
                    late_minutes = 0
                    early_leave_minutes = 0
                    overtime_minutes = 0
                    hours_worked = shift_h
                    duration_str = f"{int(shift_h)}س 0د (معتمد)"
                elif status_override == "ABSENT":
                    is_present = False
                    status = f"غائب ({condition})" if condition else "غائب"
                    notes_str = f"غياب معتمد: {condition}" if condition else "غياب يدوي"
                    checkin_str = "--:--:--"
                    checkout_str = "--:--:--"
                    late_minutes = 0
                    early_leave_minutes = 0
                    overtime_minutes = 0
                    hours_worked = 0.0
                    duration_str = "0س 0د"
                else: # AUTO
                    is_present = False
                    if is_weekend:
                        status = f"عطلة أسبوعية ({condition})" if condition else "عطلة أسبوعية"
                        notes_str = f"إجازة رسمية: {condition}" if condition else "إجازة رسمية"
                    else:
                        status = f"غائب ({condition})" if condition else "غائب"
                        notes_str = f"غياب: {condition}" if condition else "غياب كامل بدون بصمة"
                    checkin_str = "--:--:--"
                    checkout_str = "--:--:--"
                    late_minutes = 0
                    early_leave_minutes = 0
                    overtime_minutes = 0
                    hours_worked = 0.0
                    duration_str = "0س 0د"

                results.append({
                    "enno": enno,
                    "name": name,
                    "date": target_date,
                    "is_present": is_present,
                    "status": status,
                    "checkin_time": checkin_str,
                    "checkout_time": checkout_str,
                    "late_minutes": late_minutes,
                    "early_leave_minutes": early_leave_minutes,
                    "overtime_minutes": overtime_minutes,
                    "hours_worked": hours_worked,
                    "duration_str": duration_str,
                    "punches_count": 0,
                    "notes": notes_str,
                    "condition": condition,
                    "status_override": status_override
                })

        return results

    def get_period_summary(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
        """حساب التقرير الشهري / التجميعي لفترة محددة لكل موظف"""
        summary_dict = {}

        max_perm_hours = float(self.config.get("monthly_permission_hours", 4.0))
        max_perm_mins = max_perm_hours * 60.0

        for enno, emp in self.employees.items():
            summary_dict[enno] = {
                "enno": enno,
                "name": emp["name"],
                "days_present": 0,
                "days_absent": 0,
                "days_late": 0,
                "total_late_minutes": 0,
                "daily_late_records": [],
                "days_early_leave": 0,
                "total_early_leave_minutes": 0,
                "days_missing_checkout": 0,
                "total_hours_worked": 0.0,
                "total_overtime_minutes": 0,
                "total_working_days": 0,
                "permission_minutes": 0,
                "permission_hours": 0.0,
                "permission_penalty_days": 0,
                "is_permission_exceeded": False
            }

        # مسح جميع الأيام داخل الفترة
        cur_date = start_date
        one_day = datetime.timedelta(days=1)
        weekend_days = self.config.get("weekend_days", [4, 5])
        auto_hire = self.config.get("auto_detect_hire_date", True)

        while cur_date <= end_date:
            daily = self.get_daily_attendance(cur_date)

            for r in daily:
                enno = r["enno"]
                if enno not in summary_dict:
                    continue

                emp_wk = self.get_employee_weekend_days(enno)
                is_wk = cur_date.weekday() in emp_wk

                if not is_wk:
                    summary_dict[enno]["total_working_days"] += 1

                # حساب دقائق الاستئذان (التأخير + الانصراف المبكر)
                day_perm_mins = 0
                if r["late_minutes"] > 0:
                    day_perm_mins += r["late_minutes"]
                if r.get("early_leave_minutes", 0) > 0:
                    day_perm_mins += r["early_leave_minutes"]
                summary_dict[enno]["permission_minutes"] += day_perm_mins

                if r["is_present"]:
                    summary_dict[enno]["days_present"] += 1
                    summary_dict[enno]["total_hours_worked"] += r["hours_worked"]
                    summary_dict[enno]["total_overtime_minutes"] += r["overtime_minutes"]
                    if r["late_minutes"] > 0:
                        summary_dict[enno]["days_late"] += 1
                        summary_dict[enno]["total_late_minutes"] += r["late_minutes"]
                        summary_dict[enno]["daily_late_records"].append(r["late_minutes"])
                    if r.get("early_leave_minutes", 0) > 0:
                        summary_dict[enno]["days_early_leave"] += 1
                        summary_dict[enno]["total_early_leave_minutes"] += r["early_leave_minutes"]
                    if r["checkout_time"] == "--:--:--":
                        summary_dict[enno]["days_missing_checkout"] += 1
                else:
                    if r["status"] == "غائب":
                        summary_dict[enno]["days_absent"] += 1

            cur_date += one_day

        result = list(summary_dict.values())
        for row in result:
            work_days = row["total_working_days"]
            if work_days > 0:
                row["attendance_percentage"] = round((row["days_present"] / work_days) * 100, 1)
            else:
                row["attendance_percentage"] = 0.0
            row["total_hours_worked"] = round(row["total_hours_worked"], 2)
            row["permission_hours"] = round(row["permission_minutes"] / 60.0, 1)

            # تطبيق قاعدة الإذن: إذا تجاوز عدد ساعات الإذن المسموح بها في الشهر يُخصم يوم
            if max_perm_mins > 0 and row["permission_minutes"] > max_perm_mins:
                row["is_permission_exceeded"] = True
                row["permission_penalty_days"] = 1
                row["days_absent"] += 1  # إضافة يوم الخصم للغياب المالي والإداري

        return sorted(result, key=lambda x: x["enno"])

    def export_daily_to_excel(self, target_date: datetime.date, output_path: str) -> bool:
        """تصدير تقرير اليوم إلى ملف Excel بتنسيق وتصميم جذاب مع بيان الظروف والتصاريح"""
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        data = self.get_daily_attendance(target_date)
        if not data:
            return False

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"حضور {target_date.strftime('%Y-%m-%d')}"
        ws.views.sheetView[0].rightToLeft = True

        # خطوط وألوان
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Segoe UI", size=15, bold=True, color="1E293B")
        sub_font = Font(name="Segoe UI", size=10, italic=True, color="64748B")
        normal_font = Font(name="Segoe UI", size=10)
        bold_font = Font(name="Segoe UI", size=10, bold=True)

        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # كحلي أزرق
        
        # ألوان الحالات
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # أخضر فاتح
        orange_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid") # أصفر/برتقالي
        red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # أحمر فاتح
        gray_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid") # رمادي فاتح
        blue_fill = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid") # سماوي

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        center_align = Alignment(horizontal='center', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')

        # عنوان التقرير
        ws.merge_cells("A1:K1")
        ws["A1"] = f"تقرير الحضور والانصراف اليومي - {target_date.strftime('%A %Y/%m/%d')}"
        ws["A1"].font = title_font
        ws["A1"].alignment = center_align

        kpis = self.get_kpis_for_date(target_date)
        ws.merge_cells("A2:K2")
        ws["A2"] = (f"إجمالي الموظفين: {kpis['total_employees']} | "
                    f"حضور: {kpis['present']} | "
                    f"غياب: {kpis['absent']} | "
                    f"تأخير: {kpis['late']} | "
                    f"لم يسجل انصراف: {kpis['missing_checkout']}")
        ws["A2"].font = sub_font
        ws["A2"].alignment = center_align

        # رؤوس الأعمدة
        headers = [
            "م", "كود الموظف", "اسم الموظف", "بيان الظروف / التصريح", "الحالة", 
            "وقت الحضور", "وقت الانصراف", "التأخير (د)", 
            "انصراف مبكر (د)", "ساعات العمل", "ملاحظات"
        ]

        row_num = 4
        for col_num, h in enumerate(headers, 1):
            cell = ws.cell(row=row_num, column=col_num, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        # البيانات
        for idx, r in enumerate(data, 1):
            row_num += 1
            ws.cell(row=row_num, column=1, value=idx).alignment = center_align
            ws.cell(row=row_num, column=2, value=r["enno"]).alignment = center_align
            ws.cell(row=row_num, column=3, value=r["name"]).alignment = left_align
            ws.cell(row=row_num, column=4, value=r.get("condition", "")).alignment = left_align
            
            status_cell = ws.cell(row=row_num, column=5, value=r["status"])
            status_cell.alignment = center_align

            # تلوين الحالة
            if "حاضر" in r["status"]:
                status_cell.fill = green_fill
            elif "متأخر" in r["status"]:
                status_cell.fill = orange_fill
            elif "غائب" in r["status"]:
                status_cell.fill = red_fill
            elif "بدون انصراف" in r["status"]:
                status_cell.fill = blue_fill
            else:
                status_cell.fill = gray_fill

            ws.cell(row=row_num, column=6, value=r["checkin_time"]).alignment = center_align
            ws.cell(row=row_num, column=7, value=r["checkout_time"]).alignment = center_align
            ws.cell(row=row_num, column=8, value=r["late_minutes"] if r["late_minutes"] > 0 else "-").alignment = center_align
            ws.cell(row=row_num, column=9, value=r["early_leave_minutes"] if r["early_leave_minutes"] > 0 else "-").alignment = center_align
            ws.cell(row=row_num, column=10, value=r["duration_str"]).alignment = center_align
            ws.cell(row=row_num, column=11, value=r["notes"]).alignment = left_align

            for col in range(1, 12):
                c = ws.cell(row=row_num, column=col)
                c.font = normal_font
                c.border = thin_border

        # ضبط عرض الأعمدة تلقائياً
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(output_path)
        return True

    def export_period_to_excel(self, start_date: datetime.date, end_date: datetime.date, output_path: str) -> bool:
        """تصدير التقرير الشهري / الدوري إلى Excel"""
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        data = self.get_period_summary(start_date, end_date)
        if not data:
            return False

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "الملخص الدوري"
        ws.views.sheetView[0].rightToLeft = True

        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Segoe UI", size=15, bold=True, color="1E293B")
        sub_font = Font(name="Segoe UI", size=10, italic=True, color="64748B")
        normal_font = Font(name="Segoe UI", size=10)

        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        center_align = Alignment(horizontal='center', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')

        ws.merge_cells("A1:L1")
        ws["A1"] = f"تقرير الحضور والانصراف التجميعي من {start_date.strftime('%Y/%m/%d')} إلى {end_date.strftime('%Y/%m/%d')}"
        ws["A1"].font = title_font
        ws["A1"].alignment = center_align

        headers = [
            "م", "كود الموظف", "اسم الموظف", "أيام العمل", 
            "أيام الحضور", "أيام الغياب", "مرات التأخير", 
            "إجمالي دقائق التأخير", "ساعات الإذن المستهلكة", "خصم تجاوز الإذن (أيام)",
            "إجمالي ساعات العمل", "نسبة الالتزام (%)"
        ]

        row_num = 3
        for col_num, h in enumerate(headers, 1):
            cell = ws.cell(row=row_num, column=col_num, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        for idx, r in enumerate(data, 1):
            row_num += 1
            ws.cell(row=row_num, column=1, value=idx).alignment = center_align
            ws.cell(row=row_num, column=2, value=r["enno"]).alignment = center_align
            ws.cell(row=row_num, column=3, value=r["name"]).alignment = left_align
            ws.cell(row=row_num, column=4, value=r["total_working_days"]).alignment = center_align
            ws.cell(row=row_num, column=5, value=r["days_present"]).alignment = center_align
            ws.cell(row=row_num, column=6, value=r["days_absent"]).alignment = center_align
            ws.cell(row=row_num, column=7, value=r["days_late"]).alignment = center_align
            ws.cell(row=row_num, column=8, value=r["total_late_minutes"]).alignment = center_align
            ws.cell(row=row_num, column=9, value=f"{r.get('permission_hours', 0.0)}س").alignment = center_align
            perm_pen_val = f"{r.get('permission_penalty_days', 0)} يوم" if r.get('permission_penalty_days', 0) > 0 else "-"
            ws.cell(row=row_num, column=10, value=perm_pen_val).alignment = center_align
            ws.cell(row=row_num, column=11, value=r["total_hours_worked"]).alignment = center_align
            ws.cell(row=row_num, column=12, value=f"{r['attendance_percentage']}%").alignment = center_align

            for col in range(1, 13):
                c = ws.cell(row=row_num, column=col)
                c.font = normal_font
                c.border = thin_border

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(output_path)
        return True

    # ==================== موديول إدارة الموارد البشرية والرواتب (HR & Payroll) ====================

    def get_hr_settings(self) -> dict:
        """الحصول على إعدادات وقواعد موديول الرواتب والـ HR"""
        return self.config.get("hr_settings", dict(DEFAULT_CONFIG.get("hr_settings", {})))

    def save_hr_settings(self, new_settings: dict) -> bool:
        """تحديث وحفظ إعدادات موديول الرواتب"""
        current_hr = self.get_hr_settings()
        current_hr.update(new_settings)
        self.config["hr_settings"] = current_hr
        return self.save_config(self.config)

    def get_employee_hr(self, enno: int) -> dict:
        """جلب بيانات الراتب والمسمى الوظيفي والبدلات للموظف"""
        hr_settings = self.get_hr_settings()
        emp_dict = hr_settings.get("employees_hr", {})
        data = emp_dict.get(str(enno), {})
        return {
            "basic_salary": float(data.get("basic_salary", 0.0)),
            "allowances": float(data.get("allowances", 0.0)),
            "bonuses": float(data.get("bonuses", 0.0)),
            "deductions": float(data.get("deductions", 0.0)),
            "job_title": str(data.get("job_title", ""))
        }

    def save_employee_hr(self, enno: int, hr_data: dict) -> bool:
        """تعديل وحفظ بيانات الراتب والبدلات والمسمى الوظيفي للموظف"""
        current_hr = self.get_hr_settings()
        if "employees_hr" not in current_hr or not isinstance(current_hr["employees_hr"], dict):
            current_hr["employees_hr"] = {}

        existing = current_hr["employees_hr"].get(str(enno), {})
        existing.update({
            "basic_salary": float(hr_data.get("basic_salary", 0.0)),
            "allowances": float(hr_data.get("allowances", 0.0)),
            "bonuses": float(hr_data.get("bonuses", 0.0)),
            "deductions": float(hr_data.get("deductions", 0.0)),
            "job_title": str(hr_data.get("job_title", ""))
        })
        current_hr["employees_hr"][str(enno)] = existing
        self.config["hr_settings"] = current_hr
        return self.save_config(self.config)

    def calculate_monthly_payroll(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
        """حساب مسير الرواتب الكامل لجميع الموظفين للفترة المحددة بناءً على بيانات البصمة وقواعد الـ HR"""
        hr_cfg = self.get_hr_settings()
        period_summary = self.get_period_summary(start_date, end_date)
        summary_by_enno = {row["enno"]: row for row in period_summary}

        month_basis = float(hr_cfg.get("month_days_basis", 30))
        shift_hours = float(hr_cfg.get("shift_hours", 7.0))
        absence_multiplier = float(hr_cfg.get("absence_penalty_multiplier", 1.0))
        late_type = hr_cfg.get("late_deduction_type", "minutes")
        late_min_multiplier = float(hr_cfg.get("late_minute_multiplier", 1.0))
        early_leave_ded = bool(hr_cfg.get("early_leave_deduction", True))
        ot_multiplier = float(hr_cfg.get("overtime_multiplier", 1.5))
        late_tiers = hr_cfg.get("late_tiers", [])

        payroll_records = []

        for enno, emp in sorted(self.employees.items()):
            name = emp["name"]
            emp_hr = self.get_employee_hr(enno)
            basic_salary = float(emp_hr.get("basic_salary", 0.0))
            allowances = float(emp_hr.get("allowances", 0.0))
            bonuses = float(emp_hr.get("bonuses", 0.0))
            other_deductions = float(emp_hr.get("deductions", 0.0))
            job_title = emp_hr.get("job_title", "")

            # إحصائيات الحضور للفترة
            att = summary_by_enno.get(enno, {})
            working_days = att.get("total_working_days", 0)
            days_present = att.get("days_present", 0)
            days_absent = att.get("days_absent", 0)
            days_late = att.get("days_late", 0)
            total_late_mins = att.get("total_late_minutes", 0)
            total_early_mins = att.get("total_early_leave_minutes", 0)
            total_ot_mins = att.get("total_overtime_minutes", 0)
            total_hours = att.get("total_hours_worked", 0.0)

            # معدلات الأجر المالي
            day_rate = round(basic_salary / month_basis, 2) if month_basis > 0 else 0.0
            hour_rate = round(day_rate / shift_hours, 2) if shift_hours > 0 else 0.0
            minute_rate = round(hour_rate / 60.0, 4) if shift_hours > 0 else 0.0

            # 1. خصم الغياب
            absence_deduction = round(days_absent * day_rate * absence_multiplier, 2)

            # 2. خصم التأخير
            if late_type == "minutes":
                late_deduction = round(total_late_mins * minute_rate * late_min_multiplier, 2)
            else:
                # نظام الشرائح: يُحسب من السجلات اليومية المحسوبة مسبقاً في مسحة واحدة سريعة جداً
                late_deduction = 0.0
                daily_lates = att.get("daily_late_records", [])
                if daily_lates and late_tiers:
                    sorted_tiers = sorted(late_tiers, key=lambda t: t.get("max_mins", 0))
                    for l_mins in daily_lates:
                        for tier in sorted_tiers:
                            if l_mins <= tier.get("max_mins", 0):
                                late_deduction += tier.get("day_fraction", 0.0) * day_rate
                                break
                late_deduction = round(late_deduction, 2)

            # 3. خصم الانصراف المبكر
            if early_leave_ded:
                early_leave_deduction = round(total_early_mins * minute_rate, 2)
            else:
                early_leave_deduction = 0.0

            # 4. أجر الساعات الإضافية
            overtime_pay = round((total_ot_mins / 60.0) * hour_rate * ot_multiplier, 2)

            # 5. الإجماليات
            total_additions = round(allowances + bonuses + overtime_pay, 2)
            penalty_deductions = round(absence_deduction + late_deduction + early_leave_deduction, 2)
            total_deductions = round(penalty_deductions + other_deductions, 2)
            gross_salary = round(basic_salary + total_additions, 2)
            net_salary = round(max(0.0, gross_salary - total_deductions), 2)

            payroll_records.append({
                "enno": enno,
                "name": name,
                "job_title": job_title,
                "basic_salary": basic_salary,
                "working_days": working_days,
                "days_present": days_present,
                "days_absent": days_absent,
                "days_late": days_late,
                "total_late_minutes": total_late_mins,
                "total_early_minutes": total_early_mins,
                "total_hours": total_hours,
                "total_ot_mins": total_ot_mins,
                "day_rate": day_rate,
                "hour_rate": hour_rate,
                "absence_deduction": absence_deduction,
                "late_deduction": late_deduction,
                "early_leave_deduction": early_leave_deduction,
                "other_deductions": other_deductions,
                "total_deductions": total_deductions,
                "allowances": allowances,
                "bonuses": bonuses,
                "overtime_pay": overtime_pay,
                "total_additions": total_additions,
                "gross_salary": gross_salary,
                "net_salary": net_salary
            })

        return payroll_records

    def export_payroll_to_excel(self, start_date: datetime.date, end_date: datetime.date, output_path: str) -> bool:
        """تصدير كشف مسير الرواتب الشهري المعتمد إلى Excel بتصميم محاسبي فاخر"""
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        data = self.calculate_monthly_payroll(start_date, end_date)
        if not data:
            return False

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"مسير رواتب {start_date.strftime('%Y-%m')}"
        ws.views.sheetView[0].rightToLeft = True

        # أنماط الخطوط
        title_font = Font(name="Segoe UI", size=16, bold=True, color="1E293B")
        sub_font = Font(name="Segoe UI", size=10, italic=True, color="64748B")
        section_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        normal_font = Font(name="Segoe UI", size=10)
        bold_font = Font(name="Segoe UI", size=10, bold=True)
        total_font = Font(name="Segoe UI", size=11, bold=True, color="1E3A8A")

        # تعبئة الألوان للمجموعات
        emp_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")     # كحلي
        att_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")     # رمادي داكن
        add_fill = PatternFill(start_color="15803D", end_color="15803D", fill_type="solid")     # أخضر
        ded_fill = PatternFill(start_color="B91C1C", end_color="B91C1C", fill_type="solid")     # أحمر
        net_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")     # برتقالي ذهبي
        total_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")   # رمادي فاتح

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        double_bottom = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='94A3B8'),
            bottom=Side(style='double', color='1E293B')
        )

        center_align = Alignment(horizontal='center', vertical='center')
        right_align = Alignment(horizontal='right', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')

        # 1. العنوان الرئيسي
        ws.merge_cells("A1:P1")
        ws["A1"] = f"كشف مسير الرواتب والاستحقاقات الشهرية - للفترة من {start_date.strftime('%Y/%m/%d')} إلى {end_date.strftime('%Y/%m/%d')}"
        ws["A1"].font = title_font
        ws["A1"].alignment = center_align

        # إحصائيات مالية سريعة في الترويسة
        tot_basic = sum(r["basic_salary"] for r in data)
        tot_add = sum(r["total_additions"] for r in data)
        tot_ded = sum(r["total_deductions"] for r in data)
        tot_net = sum(r["net_salary"] for r in data)

        ws.merge_cells("A2:P2")
        ws["A2"] = (f"إجمالي الرواتب الأساسية: {tot_basic:,.2f} ج.م | "
                    f"إجمالي البدلات والإضافي: {tot_add:,.2f} ج.م | "
                    f"إجمالي الاستقطاعات والجزاءات: {tot_ded:,.2f} ج.م | "
                    f"صافي المستحق المطلوب صرفه: {tot_net:,.2f} ج.م")
        ws["A2"].font = sub_font
        ws["A2"].alignment = center_align

        # 2. الصف العلوي لتصنيف المجموعات (Merged Headers)
        ws.merge_cells("A4:D4")
        ws["A4"] = "بيانات الموظف الأساسية"
        ws["A4"].font = section_font
        ws["A4"].fill = emp_fill
        ws["A4"].alignment = center_align

        ws.merge_cells("E4:H4")
        ws["E4"] = "إحصائيات الحضور والانضباط"
        ws["E4"].font = section_font
        ws["E4"].fill = att_fill
        ws["E4"].alignment = center_align

        ws.merge_cells("I4:K4")
        ws["I4"] = "الاستحقاقات والإضافات (+)"
        ws["I4"].font = section_font
        ws["I4"].fill = add_fill
        ws["I4"].alignment = center_align

        ws.merge_cells("L4:O4")
        ws["L4"] = "الاستقطاعات والخصومات (-)"
        ws["L4"].font = section_font
        ws["L4"].fill = ded_fill
        ws["L4"].alignment = center_align

        ws.merge_cells("P4:Q4")
        ws["P4"] = "الصافي والتوقيع"
        ws["P4"].font = section_font
        ws["P4"].fill = net_fill
        ws["P4"].alignment = center_align

        # 3. رؤوس الأعمدة التفصيلية
        headers = [
            ("م", emp_fill),
            ("كود", emp_fill),
            ("اسم الموظف", emp_fill),
            ("المسمى الوظيفي", emp_fill),
            ("الراتب الأساسي", emp_fill),
            ("حضور (يوم)", att_fill),
            ("غياب (يوم)", att_fill),
            ("تأخير (د)", att_fill),
            ("بدلات وحوافز", add_fill),
            ("أجر الإضافي", add_fill),
            ("إجمالي المستحق", add_fill),
            ("خصم الغياب", ded_fill),
            ("خصم التأخير", ded_fill),
            ("سلف وخصم إداري", ded_fill),
            ("إجمالي الخصم", ded_fill),
            ("صافي الراتب المستحق", net_fill),
            ("توقيع الموظف", net_fill)
        ]

        row_num = 5
        for col_num, (h_title, h_fill) in enumerate(headers, 1):
            cell = ws.cell(row=row_num, column=col_num, value=h_title)
            cell.font = header_font
            cell.fill = h_fill
            cell.alignment = center_align
            cell.border = thin_border

        # 4. تعبئة بيانات الموظفين
        for idx, r in enumerate(data, 1):
            row_num += 1
            ws.cell(row=row_num, column=1, value=idx).alignment = center_align
            ws.cell(row=row_num, column=2, value=r["enno"]).alignment = center_align
            ws.cell(row=row_num, column=3, value=r["name"]).alignment = left_align
            ws.cell(row=row_num, column=4, value=r["job_title"] or "-").alignment = center_align
            
            c_basic = ws.cell(row=row_num, column=5, value=r["basic_salary"])
            c_basic.number_format = "#,##0.00"
            c_basic.alignment = right_align

            ws.cell(row=row_num, column=6, value=r["days_present"]).alignment = center_align
            ws.cell(row=row_num, column=7, value=r["days_absent"]).alignment = center_align
            ws.cell(row=row_num, column=8, value=r["total_late_minutes"]).alignment = center_align

            c_allow = ws.cell(row=row_num, column=9, value=r["allowances"] + r["bonuses"])
            c_allow.number_format = "#,##0.00"
            c_allow.alignment = right_align

            c_ot = ws.cell(row=row_num, column=10, value=r["overtime_pay"])
            c_ot.number_format = "#,##0.00"
            c_ot.alignment = right_align

            c_gross = ws.cell(row=row_num, column=11, value=r["gross_salary"])
            c_gross.number_format = "#,##0.00"
            c_gross.alignment = right_align
            c_gross.font = bold_font

            c_abs_ded = ws.cell(row=row_num, column=12, value=r["absence_deduction"])
            c_abs_ded.number_format = "#,##0.00"
            c_abs_ded.alignment = right_align

            c_late_ded = ws.cell(row=row_num, column=13, value=r["late_deduction"] + r["early_leave_deduction"])
            c_late_ded.number_format = "#,##0.00"
            c_late_ded.alignment = right_align

            c_other_ded = ws.cell(row=row_num, column=14, value=r["other_deductions"])
            c_other_ded.number_format = "#,##0.00"
            c_other_ded.alignment = right_align

            c_tot_ded = ws.cell(row=row_num, column=15, value=r["total_deductions"])
            c_tot_ded.number_format = "#,##0.00"
            c_tot_ded.alignment = right_align
            c_tot_ded.font = bold_font

            c_net = ws.cell(row=row_num, column=16, value=r["net_salary"])
            c_net.number_format = "#,##0.00"
            c_net.alignment = right_align
            c_net.font = bold_font
            c_net.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid") # تمييز ذهبي

            ws.cell(row=row_num, column=17, value="").alignment = center_align

            for col in range(1, 18):
                cell = ws.cell(row=row_num, column=col)
                if col != 16 and not cell.font.bold:
                    cell.font = normal_font
                cell.border = thin_border

        # 5. صف الإجماليات الختامي
        row_num += 1
        ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=4)
        c_lbl = ws.cell(row=row_num, column=1, value="الإجمـــــــــــــــــالي العــــــــــــــام")
        c_lbl.font = total_font
        c_lbl.alignment = center_align

        # معادلات الإجمالي
        first_row = 6
        last_row = row_num - 1
        
        sum_cols = [5, 9, 10, 11, 12, 13, 14, 15, 16]
        for col_idx in sum_cols:
            col_ltr = get_column_letter(col_idx)
            cell = ws.cell(row=row_num, column=col_idx, value=f"=SUM({col_ltr}{first_row}:{col_ltr}{last_row})")
            cell.font = total_font
            cell.number_format = "#,##0.00"
            cell.alignment = right_align

        for col in range(1, 18):
            c = ws.cell(row=row_num, column=col)
            c.fill = total_fill
            c.border = double_bottom

        # ضبط عرض الأعمدة
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 13)
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 8
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 16
        ws.column_dimensions['P'].width = 18
        ws.column_dimensions['Q'].width = 18

        wb.save(output_path)
        return True

    # ==================== كارت الموظف الفردي والسجل التفصيلي ====================

    def get_employee_ledger(self, enno: int, start_date: datetime.date, end_date: datetime.date) -> Dict[str, Any]:
        """استخراج السجل اليومي التفصيلي لموظف محدد للفترة المحددة مع كافة الإحصائيات"""
        emp_info = self.employees.get(enno, {"name": f"Employee {enno}", "enno": enno})
        name = emp_info.get("name", f"Employee {enno}")
        hr_info = self.get_employee_hr(enno)

        arabic_days = {
            0: "الإثنين",
            1: "الثلاثاء",
            2: "الأربعاء",
            3: "الخميس",
            4: "الجمعة",
            5: "السبت",
            6: "الأحد"
        }

        days_records = []
        cur_d = start_date
        one_d = datetime.timedelta(days=1)

        total_working_days = 0
        days_present = 0
        days_absent = 0
        days_late = 0
        total_late_minutes = 0
        days_early_leave = 0
        total_early_leave_minutes = 0
        total_hours_worked = 0.0
        total_overtime_minutes = 0

        emp_wk_days = self.get_employee_weekend_days(enno)

        while cur_d <= end_date:
            is_wk = cur_d.weekday() in emp_wk_days
            daily_list = self.get_daily_attendance(cur_d)
            emp_rec = next((r for r in daily_list if r["enno"] == enno), None)

            if not is_wk:
                total_working_days += 1

            if emp_rec:
                if emp_rec["is_present"]:
                    days_present += 1
                    total_hours_worked += emp_rec["hours_worked"]
                    total_overtime_minutes += emp_rec.get("overtime_minutes", 0)
                    if emp_rec.get("late_minutes", 0) > 0:
                        days_late += 1
                        total_late_minutes += emp_rec["late_minutes"]
                    if emp_rec.get("early_leave_minutes", 0) > 0:
                        days_early_leave += 1
                        total_early_leave_minutes += emp_rec["early_leave_minutes"]
                elif emp_rec["status"] == "غائب":
                    days_absent += 1

                days_records.append({
                    "date": cur_d,
                    "date_str": cur_d.strftime("%Y-%m-%d"),
                    "day_name": arabic_days.get(cur_d.weekday(), ""),
                    "is_weekend": is_wk,
                    "is_present": emp_rec["is_present"],
                    "status": emp_rec["status"],
                    "condition": emp_rec.get("condition", ""),
                    "status_override": emp_rec.get("status_override", "AUTO"),
                    "checkin_time": emp_rec["checkin_time"],
                    "checkout_time": emp_rec["checkout_time"],
                    "late_minutes": emp_rec.get("late_minutes", 0),
                    "early_leave_minutes": emp_rec.get("early_leave_minutes", 0),
                    "overtime_minutes": emp_rec.get("overtime_minutes", 0),
                    "hours_worked": emp_rec.get("hours_worked", 0.0),
                    "duration_str": emp_rec.get("duration_str", "-"),
                    "notes": emp_rec.get("notes", "")
                })

            cur_d += one_d

        attendance_pct = round((days_present / total_working_days * 100), 1) if total_working_days > 0 else 0.0

        max_perm_hours = float(self.config.get("monthly_permission_hours", 4.0))
        max_perm_mins = max_perm_hours * 60.0
        total_permission_minutes = total_late_minutes + total_early_leave_minutes
        permission_penalty_days = 0
        if max_perm_mins > 0 and total_permission_minutes > max_perm_mins:
            permission_penalty_days = 1
            days_absent += 1

        return {
            "enno": enno,
            "name": name,
            "hr_info": hr_info,
            "start_date": start_date,
            "end_date": end_date,
            "summary": {
                "total_working_days": total_working_days,
                "days_present": days_present,
                "days_absent": days_absent,
                "days_late": days_late,
                "total_late_minutes": total_late_minutes,
                "days_early_leave": days_early_leave,
                "total_early_leave_minutes": total_early_leave_minutes,
                "permission_minutes": total_permission_minutes,
                "permission_hours": round(total_permission_minutes / 60.0, 1),
                "max_permission_hours": max_perm_hours,
                "permission_penalty_days": permission_penalty_days,
                "is_permission_exceeded": (permission_penalty_days > 0),
                "total_hours_worked": round(total_hours_worked, 2),
                "total_overtime_minutes": total_overtime_minutes,
                "attendance_percentage": attendance_pct
            },
            "days": days_records
        }

    def export_employee_ledger_to_excel(self, enno: int, start_date: datetime.date, end_date: datetime.date, output_path: str) -> bool:
        """تصدير بطاقة الموظف الشاملة (كارت الموظف) إلى Excel بتصميم فخم"""
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        ledger = self.get_employee_ledger(enno, start_date, end_date)
        if not ledger or not ledger.get("days"):
            return False

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"كارت موظف {enno}"
        ws.views.sheetView[0].rightToLeft = True

        title_font = Font(name="Segoe UI", size=16, bold=True, color="1E293B")
        sub_font = Font(name="Segoe UI", size=11, bold=True, color="475569")
        kpi_num_font = Font(name="Segoe UI", size=14, bold=True, color="1E3A8A")
        kpi_lbl_font = Font(name="Segoe UI", size=9, bold=True, color="64748B")
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        normal_font = Font(name="Segoe UI", size=10)
        bold_font = Font(name="Segoe UI", size=10, bold=True)
        total_font = Font(name="Segoe UI", size=11, bold=True, color="1E3A8A")

        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        card_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        total_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        orange_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        gray_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        double_bottom = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='94A3B8'),
            bottom=Side(style='double', color='1E293B')
        )

        center_align = Alignment(horizontal='center', vertical='center')
        left_align = Alignment(horizontal='left', vertical='center')

        # 1. العنوان الرئيسي
        ws.merge_cells("A1:J1")
        ws["A1"] = f"بطاقة كشف الحضور والانصراف الفردي (كارت الموظف)"
        ws["A1"].font = title_font
        ws["A1"].alignment = center_align

        ws.merge_cells("A2:J2")
        emp_name = ledger["name"]
        job_t = ledger["hr_info"].get("job_title") or "موظف"
        ws["A2"] = f"الموظف: {emp_name} | كود: {enno} | الوظيفة: {job_t} | الفترة من {start_date.strftime('%Y/%m/%d')} إلى {end_date.strftime('%Y/%m/%d')}"
        ws["A2"].font = sub_font
        ws["A2"].alignment = center_align

        # 2. بطاقات المؤشرات الإحصائية
        s = ledger["summary"]
        kpis = [
            ("أيام العمل", str(s["total_working_days"]), "A4:B4", "A5:B5"),
            ("أيام الحضور", str(s["days_present"]), "C4:D4", "C5:D5"),
            ("أيام الغياب", str(s["days_absent"]), "E4:F4", "E5:F5"),
            ("مرات التأخير", f"{s['days_late']} ({s['total_late_minutes']}د)", "G4:H4", "G5:H5"),
            ("ساعات العمل", f"{s['total_hours_worked']} س", "I4:J4", "I5:J5")
        ]

        for title, val, rng_lbl, rng_val in kpis:
            ws.merge_cells(rng_lbl)
            ws.merge_cells(rng_val)
            c_lbl = ws[rng_lbl.split(':')[0]]
            c_lbl.value = title
            c_lbl.font = kpi_lbl_font
            c_lbl.alignment = center_align
            c_lbl.fill = card_fill

            c_val = ws[rng_val.split(':')[0]]
            c_val.value = val
            c_val.font = kpi_num_font
            c_val.alignment = center_align
            c_val.fill = card_fill

        # 3. جدول الأيام
        headers = [
            "م", "اليوم", "التاريخ", "الحالة", 
            "وقت الحضور", "وقت الانصراف", "التأخير (د)", 
            "انصراف مبكر (د)", "ساعات العمل", "ملاحظات"
        ]

        row_num = 7
        for col_num, h in enumerate(headers, 1):
            cell = ws.cell(row=row_num, column=col_num, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        for idx, r in enumerate(ledger["days"], 1):
            row_num += 1
            ws.cell(row=row_num, column=1, value=idx).alignment = center_align
            ws.cell(row=row_num, column=2, value=r["day_name"]).alignment = center_align
            ws.cell(row=row_num, column=3, value=r["date_str"]).alignment = center_align

            c_status = ws.cell(row=row_num, column=4, value=r["status"])
            c_status.alignment = center_align
            if r["status"] == "حاضر في الموعد":
                c_status.fill = green_fill
            elif "متأخر" in r["status"]:
                c_status.fill = orange_fill
            elif r["status"] == "غائب":
                c_status.fill = red_fill
            else:
                c_status.fill = gray_fill

            ws.cell(row=row_num, column=5, value=r["checkin_time"]).alignment = center_align
            ws.cell(row=row_num, column=6, value=r["checkout_time"]).alignment = center_align
            ws.cell(row=row_num, column=7, value=r["late_minutes"] if r["late_minutes"] > 0 else "-").alignment = center_align
            ws.cell(row=row_num, column=8, value=r["early_leave_minutes"] if r["early_leave_minutes"] > 0 else "-").alignment = center_align
            ws.cell(row=row_num, column=9, value=r["duration_str"]).alignment = center_align
            ws.cell(row=row_num, column=10, value=r["notes"]).alignment = left_align

            for col in range(1, 11):
                cell = ws.cell(row=row_num, column=col)
                if not cell.fill or cell.fill == card_fill:
                    cell.font = normal_font
                cell.border = thin_border

        # 4. صف الإجمالي الختامي
        row_num += 1
        ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=6)
        c_tot = ws.cell(row=row_num, column=1, value=f"إجمالي الفترة ({emp_name}): {s['days_present']} حضور | {s['days_absent']} غياب | {s['total_hours_worked']} ساعة عمل")
        c_tot.font = total_font
        c_tot.alignment = center_align

        ws.cell(row=row_num, column=7, value=s["total_late_minutes"]).alignment = center_align
        ws.cell(row=row_num, column=8, value=s["total_early_leave_minutes"]).alignment = center_align
        ws.cell(row=row_num, column=9, value=f"{s['total_hours_worked']} س").alignment = center_align
        ws.cell(row=row_num, column=10, value=f"نسبة الالتزام: {s['attendance_percentage']}%").alignment = center_align

        for col in range(1, 11):
            c = ws.cell(row=row_num, column=col)
            c.font = bold_font
            c.fill = total_fill
            c.border = double_bottom

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(output_path)
        return True

