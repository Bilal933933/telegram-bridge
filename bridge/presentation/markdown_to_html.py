"""تحويل Markdown إلى HTML المفهوم في تيليجرام."""
import re

from bridge.presentation.html_escape import esc
from bridge.presentation.table_renderer import render_table, table_ranges


def inline(line):
    """تنسيق سطر واحد: كود مضمّن، عناوين، عريض، مائل، روابط."""
    parts = re.split(r"(`[^`]*`)", line)
    out = []
    for part in parts:
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            out.append("<code>" + esc(part[1:-1]) + "</code>")
            continue
        s = esc(part)
        s = re.sub(r"^(#{1,6})\s+(.*)$", r"<b>\2</b>", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\*\w])\*(?!\s)([^*]+?)\*(?![\*\w])", r"<i>\1</i>", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
        out.append(s)
    return "".join(out)


def to_html(md):
    lines = md.split("\n")
    ranges = table_ranges(lines)
    out = []
    buf = []
    lang = ""
    in_code = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if in_code:
            if line.startswith("```"):
                body = esc("\n".join(buf))
                out.append(f'<pre><code class="language-{esc(lang)}">{body}</code></pre>' if lang else f"<pre>{body}</pre>")
                in_code = False
                buf = []
                lang = ""
            else:
                buf.append(line)
            i += 1
            continue
        if line.startswith("```"):
            in_code = True
            lang = line[3:].strip()
            buf = []
            i += 1
            continue
        if i in ranges:
            block = lines[i:ranges[i]]
            out.append(render_table(block))
            i = ranges[i]
            continue
        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(inline(re.sub(r"^>\s?", "", lines[i])))
                i += 1
            body = "\n".join(quote).strip()
            if body:
                out.append(f"<blockquote>{body}</blockquote>")
            continue
        out.append(inline(line))
        i += 1
    if in_code:
        out.append(f"<pre>{esc(chr(10).join(buf))}</pre>")
    return "\n".join(out)
