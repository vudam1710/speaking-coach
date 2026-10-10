"""Tests for the deterministic parts (no API calls)."""
import json
from pathlib import Path

from core.checks import advanced_in_simple, bad_quotes, find_vi_chunks, uncovered_chunks
from core.upgrade import apply_changes, next_level


def test_find_vi_chunks_diacritics_and_brackets():
    a = "If I break something I need to bồi thường, but [vien phi] is too high. Tiền con cái học rất đắt."
    assert find_vi_chunks(a) == ["vien phi", "bồi thường", "Tiền con cái học rất đắt"]


def test_find_vi_chunks_english_only():
    assert find_vi_chunks("I like cooking because it is cheap.") == []


def test_find_vi_chunks_stops_at_english():
    assert find_vi_chunks("I had to pay viện phí and it was expensive.") == ["viện phí"]


def _fb(chunk, quote, adv, way):
    return {"stuck_points": [{"vi_chunk": chunk, "advanced": {"phrase_en": adv},
                              "simple_ways": [{"sentence_en": way}]}],
            "english_notes": [{"quote_en": quote}], "other_ways": []}


def test_coverage_and_quotes():
    fb = _fb("viện phí", "it was very cheap", "hospital fees", "I paid the hospital.")
    assert uncovered_chunks(["viện phí", "áp lực"], fb) == ["áp lực"]
    assert bad_quotes("I had to pay viện phí and it was expensive.", fb) == ["it was very cheap"]


def test_advanced_leak():
    fb = _fb("viện phí", "x", "hospital fees", "The hospital fees were high.")
    assert advanced_in_simple(fb) == ["hospital fees"]


def test_apply_changes_only_touches_chosen_parts():
    base = "I pay money for the hospital. It is expensive. Many families cannot pay."
    changes = [{"original_en": "pay money for the hospital", "upgraded_en": "pay the hospital bill"},
               {"original_en": "Many families cannot pay.", "upgraded_en": "That's why many families can't afford it."}]
    out, missing = apply_changes(base, changes)
    assert out == "I pay the hospital bill. It is expensive. That's why many families can't afford it."
    assert missing == []


def test_apply_changes_reports_missing():
    _, missing = apply_changes("I like it.", [{"original_en": "not here", "upgraded_en": "x"}])
    assert missing == ["not here"]


def test_next_level_caps_at_c2():
    assert next_level("B1") == "B2" and next_level("C2") == "C2"


def test_question_bank_shape():
    sets = json.loads((Path(__file__).parent.parent / "data" / "questions.json").read_text(encoding="utf-8"))["sets"]
    ids = {s["id"] for s in sets}
    assert len(ids) == len(sets)
    for s in sets:
        assert (len(s["questions"]) == 1) if s["part"] == 2 else (3 <= len(s["questions"]) <= 5), s["id"]
        if s.get("part3"):
            assert s["part3"] in ids


def test_quota_counts_answers():
    from core.auth import User, quota_message
    u = User("a", "student")
    lim = {"student_daily": 5, "global_daily": 100}
    assert quota_message(u, 0, 0, lim, needed=5) is None
    assert "bỏ bớt 2" in quota_message(u, 3, 3, lim, needed=4)
    assert quota_message(u, 5, 5, lim, needed=1) is not None
    assert quota_message(u, 0, 99, lim, needed=2) is not None
