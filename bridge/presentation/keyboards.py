"""لوحات الأزرار (reply_markup) — كائن بلا حالة يُمرَّر في السياق."""

# نصوص أزرار اللوحة الثابتة: تُطابق كأوامر في الموجّه، فتبقى في مكان واحد.
LBL_PROJECTS = "🗂 المشاريع"
LBL_SESSIONS = "💬 الجلسات"
LBL_NEW = "🆕 جلسة"
LBL_MENU = "🧭 الأزرار"
LBL_STATUS = "ℹ️ الحالة"


class Keyboards:
    def kb(self, rows):
        return {"inline_keyboard": rows}

    def menu_kb(self):
        return self.kb([
            [{"text": "🗂 المشاريع", "callback_data": "ph"},
             {"text": "💬 جلسات المشروع", "callback_data": "sessions"}],
            [{"text": "🆕 جلسة جديدة", "callback_data": "new"},
             {"text": "🔌 المحرّك", "callback_data": "src"}],
            [{"text": "📊 بطاقة الجلسة", "callback_data": "card"},
             {"text": "🤖 الوكيل", "callback_data": "ag"}],
            [{"text": "ℹ️ الحالة", "callback_data": "status"},
             {"text": "❓ مساعدة", "callback_data": "help"}],
        ])

    def main_menu(self):
        """لوحة ثابتة أسفل المحادثة تبقى ظاهرة بعد إرسالها."""
        return {
            "keyboard": [
                [{"text": LBL_PROJECTS}, {"text": LBL_SESSIONS}],
                [{"text": LBL_NEW}, {"text": LBL_MENU}],
                [{"text": LBL_STATUS}],
            ],
            "resize_keyboard": True,
            "is_persistent": True,
        }
