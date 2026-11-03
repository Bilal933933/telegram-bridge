"""مؤشّر «يكتب الآن» في خيط خلفي، ويُوقف بـ Event."""
import threading


def start_typing(tg, chat_id, thread_id=None, interval=4.5):
    """يبدأ إرسال إجراء typing دوريًا ويعيد Event لإيقافه."""
    stop = threading.Event()

    def loop():
        while not stop.wait(interval):
            tg.action(chat_id, "typing", thread_id=thread_id)

    threading.Thread(target=loop, daemon=True).start()
    return stop
