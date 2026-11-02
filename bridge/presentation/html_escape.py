"""تهريب النصوص إلى HTML (مكان واحد لكل escaping في طبقة العرض)."""
import html


def esc(text):
    return html.escape(text, quote=False)
