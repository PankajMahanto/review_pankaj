"""Citation-key helper: <first-author-surname><year><first-content-word-of-title>, e.g. yang2025neural."""
import re
import unicodedata

STOP = {"a", "an", "the", "on", "of", "for", "in", "to", "and", "with", "via", "towards", "toward", "from",
        "is", "are", "do", "does", "can", "beyond", "using", "by", "at", "as", "into", "what", "when", "how", "why"}


def ascii_lower(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def surname(author):
    a = re.sub(r"\s+\d{4}$", "", author or "").strip()
    if "," in a:
        a = a.split(",")[0]
    else:
        a = a.split()[-1] if a.split() else "anon"
    return re.sub(r"[^a-z]", "", ascii_lower(a)) or "anon"


def first_word(title):
    for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]*", title or ""):
        lw = ascii_lower(w).replace("-", "")
        if lw not in STOP and len(lw) > 1:
            return re.sub(r"[^a-z0-9]", "", lw)
    return "paper"


def make_key(authors, year, title, taken=None):
    base = f"{surname(authors[0] if authors else 'anon')}{year or 'nd'}{first_word(title)}"
    if taken is None:
        return base
    k, i = base, 0
    while k in taken:
        i += 1
        k = base + "abcdefghijklmnopqrstuvwxyz"[i - 1]
    taken.add(k)
    return k
