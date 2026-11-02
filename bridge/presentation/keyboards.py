"""لوحات الأزرار (reply_markup) — كائن بلا حالة يُمرَّر في السياق."""


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
