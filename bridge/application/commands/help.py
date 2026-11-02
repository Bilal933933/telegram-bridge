"""نص المساعدة والقائمة الرئيسية."""
HELP = (
    "👋 **كيف يعمل**\n\n"
    "1️⃣ اضغط **🗂 المشاريع** واختر مجلدًا\n"
    "2️⃣ اضغط جلسة (أو 🆕 جلسة جديدة)\n"
    "3️⃣ اكتب رسالتك — الوكيل ينفّذها على جهازك ويعيد الرد\n\n"
    "كل رسالة تذهب إلى نفس الجلسة حتى تفتح غيرها.\n"
    "الأوامر: /projects · /sessions · /new · /history · /agent · /model · /stop · /status"
)


def run(ctx, chat_id, arg=""):
    ctx.messenger.send(chat_id, HELP, ctx.keyboards.menu_kb())
