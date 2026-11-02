"""تقسيم الرسائل الطويلة مع الحفاظ على كتل الكود والجداول كاملة."""
import re

from bridge.presentation.table_renderer import mode, table_ranges

LIMIT = 3800


def chunks(md, limit=LIMIT):
    """يقسّم Markdown إلى رسائل لا تتجاوز limit حرفًا."""
    lines = md.split("\n")
    ranges = table_ranges(lines)
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
            if bsize <= limit and mode(block) == "pre":
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
