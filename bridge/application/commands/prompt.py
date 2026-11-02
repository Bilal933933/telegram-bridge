"""الرسائل الحرة: تمريرها إلى المحرّك النشط."""


def run(ctx, chat_id, text):
    ctx.runner.submit(chat_id, text)
