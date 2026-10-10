"""Deterministic checks (code, not LLM).

1. find_vi_chunks: find the Vietnamese parts of an answer, so the LLM is TOLD
   where the learner got stuck instead of guessing.
   - runs of words that contain Vietnamese diacritics ("viện phí", "bồi thường")
   - anything inside [square brackets] (for learners typing without diacritics: [vien phi])
2. coverage / quote checks on the LLM output.
"""
import re

_VI_CHARS = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
_VI_WORD = re.compile(rf"\b\w*[{_VI_CHARS}]\w*\b", re.IGNORECASE)
_BRACKET = re.compile(r"\[([^\]]+)\]")
_WORD = re.compile(r"\S+")


def find_vi_chunks(answer: str) -> list[str]:
    chunks = [m.group(1).strip() for m in _BRACKET.finditer(answer)]
    text = _BRACKET.sub(" ", answer)

    # group consecutive Vietnamese words; a single unaccented word between two
    # Vietnamese words is kept ("tiền con cái" -> one chunk)
    tokens = [(m.group(0), bool(_VI_WORD.search(m.group(0)))) for m in _WORD.finditer(text)]
    run: list[str] = []
    gap: list[str] = []

    def flush():
        if run:
            chunks.append(" ".join(run).strip(".,;!?\"'()"))
        run.clear()
        gap.clear()

    for tok, is_vi in tokens:
        if is_vi:
            run.extend(gap + [tok])
            gap.clear()
            if tok[-1] in ".,;!?":
                flush()
        elif run and not gap and tok[-1] not in ".,;!?":
            gap.append(tok)
        else:
            flush()
    flush()
    seen, out = set(), []
    for c in chunks:
        if c and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


def has_vietnamese(text: str) -> bool:
    return bool(_VI_WORD.search(text))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower().strip(".,;!?\"'")


def uncovered_chunks(detected: list[str], feedback: dict) -> list[str]:
    """Detected Vietnamese chunks that got no lesson."""
    covered = [_norm(sp["vi_chunk"]) for sp in feedback["stuck_points"]]
    return [c for c in detected if not any(_norm(c) in cv or cv in _norm(c) for cv in covered)]


def bad_quotes(answer: str, feedback: dict) -> list[str]:
    """Quotes that are not in the answer (= invented)."""
    a = _norm(answer)
    quotes = [sp["vi_chunk"] for sp in feedback["stuck_points"]] + [n["quote_en"] for n in feedback["english_notes"]]
    return [q for q in quotes if _norm(q) not in a]


def vietnamese_in_ways(feedback: dict) -> list[str]:
    """A 'simple way' that still contains Vietnamese is useless."""
    ways = [w["sentence_en"] for sp in feedback["stuck_points"] for w in sp["simple_ways"]]
    ways += [w["sentence_en"] for w in feedback["other_ways"]]
    return [w for w in ways if has_vietnamese(w)]


def advanced_in_simple(feedback: dict) -> list[str]:
    """The 'advanced' phrase must not sneak into the simple ways (that defeats the point)."""
    out = []
    for sp in feedback["stuck_points"]:
        adv = _norm(sp["advanced"]["phrase_en"])
        if any(adv in _norm(w["sentence_en"]) for w in sp["simple_ways"]):
            out.append(sp["advanced"]["phrase_en"])
    return out
