"""عرض جداول Markdown داخل تيليجرام.

جدول ضيّق → <pre> مصفوف (خط ثابت العرض)، وجدول عريض → بطاقات لكل سطر
لأن التمرير الأفقي في الجوال غير عملي.
"""
import re

from bridge.presentation.html_escape import esc

SEP_RE = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")
CELL_MAX = 56
PRE_MAX_WIDTH = 48


def cells(line):
    """يقسّم سطر جدول إلى خلايا منزوعة الأطراف."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def cell_text(cell):
    """إزالة تنسيقات Markdown داخل خلية (لا تُفهم داخل <pre>)."""
    s = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r"\1", cell)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<![\*\w])\*(?!\s)([^*]+?)\*(?![\*\w])", r"\1", s)
    s = s.replace("`", "").replace("<", "").replace(">", "")
    return s.strip()


def is_table_start(lines, i):
    if i + 1 >= len(lines):
        return False
    head, sep = lines[i], lines[i + 1]
    if "|" not in head or "|" not in sep or "-" not in sep:
        return False
    if not SEP_RE.match(sep):
        return False
    return len(cells(head)) >= 2


def table_ranges(lines):
    """{سطر البداية: سطر ما بعد النهاية} لكل جدول Markdown."""
    ranges = {}
    i = 0
    n = len(lines)
    while i < n:
        if is_table_start(lines, i):
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
    for cell in cells(sep):
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
    header = [cell_text(c) for c in cells(block[0])]
    aligns = _aligns(block[1]) if len(block) > 1 else []
    rows = [header]
    for line in block[2:]:
        rows.append([cell_text(c) for c in cells(line)])
    cols = max(len(r) for r in rows)
    rows = [r + [""] * (cols - len(r)) for r in rows]
    aligns += ["left"] * (cols - len(aligns))
    return rows, aligns


def mode(block):
    """جدول ضيّق → 'pre'، جدول عريض → 'cards'."""
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


def render_pre(block):
    rows, aligns = _grid(block)
    cols = len(rows[0])
    widths = [max(3, min(max(len(r[c]) for r in rows), CELL_MAX)) for c in range(cols)]
    lines = []
    for idx, row in enumerate(rows):
        cells_out = []
        for c, cell in enumerate(row):
            text = _fit(cell, widths[c])
            if aligns[c] == "right":
                cells_out.append(text.rjust(widths[c]))
            elif aligns[c] == "center":
                cells_out.append(text.center(widths[c]))
            else:
                cells_out.append(text.ljust(widths[c]))
        lines.append(" | ".join(cells_out).rstrip())
        if idx == 0:
            lines.append("-+-".join("-" * w for w in widths))
    return "<pre>" + esc("\n".join(lines)) + "</pre>"


def render_cards(block):
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


def render_table(block):
    return render_pre(block) if mode(block) == "pre" else render_cards(block)
