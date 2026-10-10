"""Turn what the learner was shown into review material for the teacher:
- review_items.csv: 1 row = 1 thing shown to the learner, word for word → the teacher marks ✓ / ~ / ✗
- markdown: the whole page as the learner saw it (set summary + every answer + upgrade + retell)

Plain dicts only (no pydantic/anthropic import) → testable without the API.

item_id (headers S1 / E1 / O / UP / U1 also carry the reviewer's in-app ratings):
  L             estimated level of this answer
  SUM.strength  the praise line            SUM.habit   the "thinking habit to practise next"
  S1            stuck point 1: Vietnamese chunk → what the learner meant + why learners get stuck
  S1.w1..w3     each simple way (sentence + strategy label + note)
  S1.adv        the "advanced" phrase (bonus) + example sentence
  E1            note on an English part (quote → type → why → better sentence)
  O             main idea          O.w1, O.w2  the 2 other ways to say it
  X1            Vietnamese chunk found by code but given NO lesson
  UP            whole upgraded answer (base → upgraded)
  U1..U4        each upgrade change         UP.task  the "say it again" task
  RETELL        what the learner typed when saying it again (if sent)
  M1..          ADD BY HAND: something important the tool missed
"""
from core.schema import CHANGE_LABELS_VI, NOTE_LABELS_VI, STRATEGY_LABELS_VI

# verdict: ✓ correct & usable as is · ~ correct but needs work · ✗ wrong / harmful
PROBLEMS_VI = {"": "— loại lỗi —", "wrong_meaning": "Sai / lệch ý", "too_hard": "Quá trình độ",
               "not_simple": "Chưa đủ đơn giản", "unnatural": "Không tự nhiên",
               "wrong_strategy": "Gắn sai chiến lược", "too_many_changes": "Đổi quá nhiều / mất giọng học sinh",
               "unclear_vi": "Giải thích tiếng Việt khó hiểu", "missed": "Bỏ sót", "other": "Khác"}
PROBLEMS = [p for p in PROBLEMS_VI if p]

ITEM_COLUMNS = ["tag", "set_id", "answer_id", "question", "item_id", "section", "shown_en", "shown_vi", "label",
                "level", "verdict", "problem", "comment", "should_be"]


def review_items(tag: str, set_id: str, answer_id: str, question: str, r: dict, up: dict | None = None,
                 answer: str = "", retell: str = "") -> list[dict]:
    fb = r["feedback"]
    base = {"tag": tag, "set_id": set_id, "answer_id": answer_id, "question": question}
    rows = []

    def add(item_id, section, shown_en="", shown_vi="", label="", level=""):
        rows.append({**base, "item_id": item_id, "section": section, "shown_en": shown_en, "shown_vi": shown_vi,
                     "label": label, "level": level})

    add("ANSWER", "Câu trả lời của học sinh", answer, f"code tìm thấy tiếng Việt: {r.get('detected_chunks', [])}")
    add("L", "Trình độ ước lượng", level=fb["level_cefr"])
    add("SUM.strength", "Khen 👍", shown_vi=fb["strength_vi"])
    for n, sp in enumerate(fb["stuck_points"], 1):
        add(f"S{n}", f"Chỗ bí {n}", sp["vi_chunk"], f"Ý bạn muốn nói: {sp['meaning_vi']} | Vì sao hay bí: {sp['trap_vi']}")
        for k, w in enumerate(sp["simple_ways"], 1):
            add(f"S{n}.w{k}", f"Chỗ bí {n} — cách nói đơn giản {k}", w["sentence_en"], w["note_vi"],
                STRATEGY_LABELS_VI[w["strategy"]])
        a = sp["advanced"]
        add(f"S{n}.adv", f"Chỗ bí {n} — từ xịn (bonus)", f"{a['phrase_en']} → {a['example_en']}", level=a["cefr"])
    for n, e in enumerate(fb["english_notes"], 1):
        add(f"E{n}", f"Phần tiếng Anh {n}", f"{e['quote_en']} → {e['better_en']}", e["why_vi"],
            f"{NOTE_LABELS_VI[e['type']]} · {STRATEGY_LABELS_VI[e['strategy']]}")
    add("O", "Ý chính", shown_vi=fb["main_idea_vi"])
    for k, w in enumerate(fb["other_ways"], 1):
        add(f"O.w{k}", f"Nói ý chính theo cách khác {k}", w["sentence_en"], w["note_vi"],
            STRATEGY_LABELS_VI[w["strategy"]])
    add("SUM.habit", "Thói quen cần luyện 🎯", shown_vi=fb["summary_vi"])
    for n, w in enumerate([w for w in r.get("warnings", []) if w.startswith("No lesson for")], 1):
        add(f"X{n}", "Code thấy tiếng Việt nhưng tool KHÔNG dạy", shown_vi=w)
    if up:
        u = up["upgrade"]
        add("UP", "Nâng cấp — cả bài", f"{u['base_answer_en']}  ⟶  {up.get('upgraded_answer_en', '')}",
            " | ".join(up.get("warnings", [])), level=up.get("target_level", ""))
        for n, c in enumerate(u["changes"], 1):
            add(f"U{n}", f"Nâng cấp — chỗ đổi {n}", f"{c['original_en']} → {c['upgraded_en']}", c["why_vi"],
                CHANGE_LABELS_VI[c["type"]], level=up.get("target_level", ""))
        add("UP.task", "Nhiệm vụ nói lại", shown_vi=u["practice_vi"])
    if retell:
        add("RETELL", "Học sinh nói lại (gửi cho giáo viên)", retell)
    return [{c: row.get(c, "") for c in ITEM_COLUMNS} for row in rows]


def render_markdown(answer_id: str, question: str, answer: str, r: dict, up: dict | None = None,
                    retell: str = "") -> str:
    """One answer, everything the learner saw, with item_id tags so the .md and the CSV line up."""
    fb = r["feedback"]
    s = STRATEGY_LABELS_VI
    out = [f"## {answer_id}", f"**Câu hỏi:** {question}", "", f"**Học sinh trả lời:** {answer}", "",
           f"<sub>code tìm thấy: {r.get('detected_chunks', [])}</sub>", "",
           f"**[L]** Trình độ {fb['level_cefr']}", f"**[SUM.strength]** 👍 {fb['strength_vi']}", ""]
    for n, sp in enumerate(fb["stuck_points"], 1):
        a = sp["advanced"]
        out += [f"### [S{n}] Chỗ bí {n}: «{sp['vi_chunk']}»", f"- Ý bạn muốn nói: {sp['meaning_vi']}",
                f"- Vì sao hay bí: {sp['trap_vi']}", "- Nói đơn giản bằng từ bạn đã biết:"]
        out += [f"  - **[S{n}.w{k}]** *{w['sentence_en']}* — **{s[w['strategy']]}** — {w['note_vi']}"
                for k, w in enumerate(sp["simple_ways"], 1)]
        out += [f"- **[S{n}.adv]** ⭐ Từ xịn: **{a['phrase_en']}** ({a['cefr']}) → *{a['example_en']}*", ""]
    for n, e in enumerate(fb["english_notes"], 1):
        out += [f"### [E{n}] Phần tiếng Anh", f"> {e['quote_en']}",
                f"**{NOTE_LABELS_VI[e['type']]}:** {e['why_vi']}", f"→ *{e['better_en']}* ({s[e['strategy']]})", ""]
    out += ["### [O] Nói ý chính theo cách khác", f"Ý chính: {fb['main_idea_vi']}"]
    out += [f"- **[O.w{k}]** *{w['sentence_en']}* — **{s[w['strategy']]}** — {w['note_vi']}"
            for k, w in enumerate(fb["other_ways"], 1)]
    out += ["", f"**[SUM.habit]** 🎯 {fb['summary_vi']}", ""]
    out += [f"⚠️ _{w}_" for w in r.get("warnings", [])]
    if up:
        u = up["upgrade"]
        out += ["", f"### [UP] ⬆️ Nâng cấp lên {up.get('target_level', '')}", f"_Trước:_ {u['base_answer_en']}", "",
                f"_Sau:_ {up.get('upgraded_answer_en', '')}", ""]
        out += [f"- **[U{n}] {CHANGE_LABELS_VI[c['type']]}:** ~~{c['original_en']}~~ → *{c['upgraded_en']}* — {c['why_vi']}"
                for n, c in enumerate(u["changes"], 1)]
        out += ["", f"**[UP.task]** 🗣️ {u['practice_vi']}"] + [f"⚠️ _{w}_" for w in up.get("warnings", [])]
    if retell:
        out += ["", f"**[RETELL]** Học sinh nói lại: {retell}"]
    return "\n".join(out) + "\n"


def render_set_markdown(header: str, summary: dict, answers_md: list[str]) -> str:
    """A whole topic set, in the order the learner saw it."""
    out = [header, "", "### 📊 Tổng kết bộ câu hỏi (học sinh thấy ở đầu trang)",
           f"Câu đã trả lời {summary['n_answers']} · Chỗ bị bí {summary['n_stuck']} · Trình độ {summary['level']}"]
    if summary["n_stuck"]:
        out += ["Những chỗ bạn bí: " + " · ".join(f"«{c}»" for c in summary["chunks"]), summary["top_strategy_text"]]
    return "\n".join(out) + "\n\n---\n\n" + "\n---\n\n".join(answers_md)
