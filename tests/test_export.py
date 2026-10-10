"""Learner export: one HTML file per topic set (no API)."""
from tests.test_render import R, UP
from ui.export import build_html, file_name


def test_export_contains_everything_the_learner_saw():
    up = {**UP, "upgrade": {**UP["upgrade"], "base_answer_en": "I pay a lot."}}   # "a" → changed to "b"
    items = [{"question": "Q1?", "answer": "I pay viện phí.", "r": R, "up": up, "retell": "I paid the bill."},
             {"question": "Q2?", "answer": "x", "r": None, "error": "boom"}]
    html = build_html(3, "Money", items)
    for text in ("Sổ tay cách nói", "viện phí", "I paid the hospital.", "hospital fees", "Nâng cấp lên B1",
                 "<mark>", "Bạn đã nói lại", "Zalo", "Câu 1"):
        assert text in html, text
    assert "Câu 2" not in html            # failed answers are left out
    assert "No lesson for" not in html    # no reviewer/debug info in the learner file


def test_file_name_is_safe():
    assert file_name("Laws and rules").startswith("luyen-noi-laws-and-rules-")
