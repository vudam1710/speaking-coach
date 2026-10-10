"""review_items / markdown from a minimal fake result (no API)."""
from evaluation.render import ITEM_COLUMNS, render_markdown, review_items

WAY = {"sentence_en": "I paid the hospital.", "strategy": "noun_to_verb", "note_vi": "x"}
R = {"feedback": {"level_cefr": "A2", "strength_vi": "s", "summary_vi": "t", "main_idea_vi": "m",
                  "stuck_points": [{"vi_chunk": "viện phí", "meaning_vi": "m", "trap_vi": "t", "simple_ways": [WAY, WAY],
                                    "advanced": {"phrase_en": "hospital fees", "cefr": "B2", "example_en": "e"}}],
                  "english_notes": [], "other_ways": [WAY, WAY]},
     "warnings": ["No lesson for: ['áp lực']"], "detected_chunks": ["viện phí", "áp lực"]}
UP = {"upgrade": {"base_answer_en": "b", "practice_vi": "p",
                  "changes": [{"original_en": "a", "upgraded_en": "b", "type": "linking", "why_vi": "w"}] * 3},
      "upgraded_answer_en": "bb", "target_level": "B1", "warnings": []}


def test_review_items_one_row_per_thing_shown():
    rows = review_items("v1", "set", "a1", "Q?", R, UP, answer="I pay viện phí.", retell="I paid the bill.")
    ids = [r["item_id"] for r in rows]
    assert ids == ["ANSWER", "L", "SUM.strength", "S1", "S1.w1", "S1.w2", "S1.adv", "O", "O.w1", "O.w2",
                   "SUM.habit", "X1", "UP", "U1", "U2", "U3", "UP.task", "RETELL"]
    assert all(list(r) == ITEM_COLUMNS for r in rows)
    s1w1 = rows[4]
    assert s1w1["shown_en"] == "I paid the hospital." and s1w1["label"] == "Đổi danh từ khó → động từ dễ"


def test_markdown_has_all_sections():
    md = render_markdown("a1", "Q?", "I pay viện phí.", R, UP, retell="I paid the bill.")
    for tag in ("[S1]", "[S1.w2]", "[S1.adv]", "[O.w1]", "[UP]", "[U3]", "[UP.task]", "[RETELL]", "No lesson for"):
        assert tag in md


def test_score_groups():
    from evaluation.score import group
    assert [group(i) for i in ["S2.w3", "S1", "S1.adv", "SUM.habit", "U4", "UP", "UP.task", "O.w1", "M2"]] == \
        ["S.w", "S", "S.adv", "SUM", "U", "UP", "UP.task", "O.w", "M"]
