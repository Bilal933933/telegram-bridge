"""تحويل Markdown إلى HTML المفهوم في تيليجرام + تقسيم ذكي للرسائل."""
import html
import re

LIMIT = 3800
SEP_RE = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")
CELL_MAX = 56
PRE_MAX_WIDTH = 48


def esc(text):
    return html.escape(text, quote=False)


def _inline(line):
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


# ---------- الجداول ----------

def _cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _cell_text(cell):
    """إزالة تنسيقات Markdown داخل خلية (لا تُفهم داخل <pre>)."""
    s = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r"\1", cell)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<![\*\w])\*(?!\s)([^*]+?)\*(?![\*\w])", r"\1", s)
    s = s.replace("`", "").replace("<", "").replace(">", "")
    return s.strip()


def _is_table_start(lines, i):
    if i + 1 >= len(lines):
        return False
    head, sep = lines[i], lines[i + 1]
    if "|" not in head or "|" not in sep or "-" not in sep:
        return False
    if not SEP_RE.match(sep):
        return False
    return len(_cells(head)) >= 2


def _table_ranges(lines):
    """{سطر البداية: سطر ما بعد النهاية} لكل جدول Markdown."""
    ranges = {}
    i = 0
    n = len(lines)
    while i < n:
        if _is_table_start(lines, i):
            j = i + 2
            while j < n and "|" in lines[j] and lines[j].strip():
                j += 1
            ranges[i] = j
            i = j
        else:
            i += 1
    return ranges


def _aligns(sep):
    out = []
    for cell in _cells(sep):
        cell = cell.strip()
        if cell.startswith(":") and cell.endswith(":"):
            out.append("center")
        elif cell.endswith(":"):
            out.append("right")
        else:
            out.append("left")
    return out


def _fit(text, width):
    return text if len(text) <= width else text[: width - 1] + "…"


def _grid(block):
    header = [_cell_text(c) for c in _cells(block[0])]
    aligns = _aligns(block[1]) if len(block) > 1 else []
    rows = [header]
    for line in block[2:]:
        rows.append([_cell_text(c) for c in _cells(line)])
    cols = max(len(r) for r in rows)
    rows = [r + [""] * (cols - len(r)) for r in rows]
    aligns += ["left"] * (cols - len(aligns))
    return rows, aligns


def _mode(block):
    """جدول ضيّق → <pre> مصفوف؛ جدول عريض → بطاقات لكل سطر (أوضح على الجوال)."""
    if block_width(block) <= PRE_MAX_WIDTH:
        return "pre"
    return "cards"


def block_width(block):
    rows, _ = _grid(block)
    cols = len(rows[0])
    widths = [max(len(r[c]) for r in rows) for c in range(cols)]
    if max(widths) > 40:
        return 10 ** 6
    return sum(min(w, CELL_MAX) for w in widths) + 3 * (cols - 1)


def _render_pre(block):
    rows, aligns = _grid(block)
    cols = len(rows[0])
    widths = [max(3, min(max(len(r[c]) for r in rows), CELL_MAX)) for c in range(cols)]
    lines = []
    for idx, row in enumerate(rows):
        cells = []
        for c, cell in enumerate(row):
            text = _fit(cell, widths[c])
            if aligns[c] == "right":
                cells.append(text.rjust(widths[c]))
            elif aligns[c] == "center":
                cells.append(text.center(widths[c]))
            else:
                cells.append(text.ljust(widths[c]))
        lines.append(" | ".join(cells).rstrip())
        if idx == 0:
            lines.append("-+-".join("-" * w for w in widths))
    return "<pre>" + esc("\n".join(lines)) + "</pre>"


def _render_cards(block):
    rows, _ = _grid(block)
    header = rows[0]
    out = []
    for row in rows[1:]:
        if not any(row):
            continue
        label = row[0]
        fields = [(header[i], row[i]) for i in range(1, len(row)) if row[i]]
        head = f"<b>{esc(label)}</b>" if label else f"<b>{esc(header[0])}</b>"
        if not fields:
            out.append(f"• {head}")
            continue
        body = "\n".join(f"   {esc(name) or '—'}: {esc(val)}" for name, val in fields)
        out.append(f"• {head}\n{body}")
    return "\n\n".join(out)


def _render_table(block):
    return _render_pre(block) if _mode(block) == "pre" else _render_cards(block)


# ---------- التحويل ----------

def to_html(md):
    lines = md.split("\n")
    ranges = _table_ranges(lines)
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
            out.append(_render_table(block))
            i = ranges[i]
            continue
        out.append(_inline(line))
        i += 1
    if in_code:
        out.append(f"<pre>{esc(chr(10).join(buf))}</pre>")
    return "\n".join(out)


def _is_atomic_table(block, limit):
    return _mode(block) == "pre" and sum(len(x) + 1 for x in block) <= limit


def chunks(md, limit=LIMIT):
    """تقسيم مع الحفاظ على كتل الكود والجداول كاملة."""
    lines = md.split("\n")
    ranges = _table_ranges(lines)
    out = []
    cur = []
    size = 0

    def flush():
        nonlocal cur, size
        if cur:
            out.append("\n".join(cur))
            cur = []
            size = 0

    in_code = False
    lang = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            if not in_code:
                in_code = True
                lang = line[3:].strip()
            else:
                in_code = False
        if not in_code and i in ranges:
            block = lines[i:ranges[i]]
            bsize = sum(len(x) + 1 for x in block)
            if bsize <= limit and _mode(block) == "pre":
                if size + bsize > limit:
                    flush()
                cur.extend(block)
                size += bsize
                i = ranges[i]
                continue
            head = block[:2]
            for k, row in enumerate(block):
                need = len(row) + 1
                if size + need > limit and cur:
                    flush()
                    if k > 1:
                        cur.extend(head)
                        size += sum(len(x) + 1 for x in head)
                cur.append(row)
                size += need
            i = ranges[i]
            continue
        need = len(line) + 1
        if size + need > limit and cur:
            if in_code:
                cur.append("```")
            flush()
            if in_code:
                cur = ["```" + lang]
                size = len(cur[0]) + 1
        cur.append(line)
        size += need
        i += 1
    flush()
    return out


def plain(md):
    """إزالة تنسيقات بسيطة عند فشل HTML."""
    text = re.sub(r"```\w*", "", md)
    text = text.replace("`", "")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text
