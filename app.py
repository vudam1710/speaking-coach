"""Speaking Coach — Streamlit UI (pilot).

Flow: access code → pick an IELTS question → type the answer (Vietnamese where stuck)
→ step 1: expression feedback → step 2 (button): upgrade +1 level → rate items.
Submissions + ratings go to a Google Sheet (core/storage.py). Without secrets → dev mode (nothing saved).
"""
import html
import json
import os
import time
import uuid
from pathlib import Path

import streamlit as st


def secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:          # no secrets.toml
        return default


# API key / model from secrets → env vars (core/llm.py reads them). Must run BEFORE importing core.coach.
for _k in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
    if secret(_k):
        os.environ.setdefault(_k, str(secret(_k)))

from core.auth import User, check_code, load_codes, quota_message, remaining  # noqa: E402
from core.checks import find_vi_chunks  # noqa: E402
from core.coach import coach  # noqa: E402
from core.schema import CHANGE_LABELS_VI, NOTE_LABELS_VI, STRATEGY_LABELS_VI  # noqa: E402
from core.storage import SheetStore, now, submission_row  # noqa: E402
from core.upgrade import apply_changes, upgrade  # noqa: E402
from ui.theme import apply_theme, brand, contact, hero  # noqa: E402

MIN_WORDS, MAX_WORDS = 10, 400
CUSTOM = "custom"
PART_NAMES = {1: "Part 1", 2: "Part 2", 3: "Part 3"}
# Reviewer problem labels (speaking-specific; same idea as writing-coach review_items.csv)
PROBLEMS = {"": "— loại lỗi —", "wrong_meaning": "Sai / lệch ý", "too_hard": "Quá trình độ",
            "not_simple": "Chưa đủ đơn giản", "unnatural": "Không tự nhiên", "wrong_strategy": "Gắn sai chiến lược",
            "too_many_changes": "Đổi quá nhiều / mất giọng học sinh", "other": "Khác"}

st.set_page_config(page_title="Speaking Coach · LogiQ Hub", page_icon="🗣️", layout="centered")
apply_theme()


@st.cache_data
def load_questions() -> list[dict]:
    path = Path(__file__).parent / "data" / "questions.json"
    return json.loads(path.read_text(encoding="utf-8"))["questions"]


@st.cache_resource(show_spinner=False)
def get_store():
    info, sheet_id = secret("gcp_service_account"), secret("SHEET_ID")
    if not (info and sheet_id):
        return None
    return SheetStore(info, sheet_id)


def store_or_none():
    try:
        return get_store()
    except Exception as e:
        st.warning(f"Không kết nối được Google Sheet — kết quả sẽ không được lưu. ({e})")
        return None


def save(store, row: dict) -> None:
    if store:
        try:
            store.add_submission(row)
        except Exception as e:
            st.warning(f"Không lưu được vào Google Sheet. ({e})")


# ------------------------------------------------------------------ login
def login() -> User:
    if "user" in st.session_state:
        return st.session_state.user
    codes = load_codes(secret("access_codes", {}))
    if not codes:                                     # local, no codes configured → dev mode
        st.session_state.user = User("local-dev", "reviewer")
        return st.session_state.user
    brand()
    hero(big=True)
    code = st.text_input("Mã truy cập", type="password", placeholder="Mã trong tin nhắn mời")
    if st.button("Vào", type="primary"):
        user = check_code(code, codes)
        if user:
            st.session_state.user = user
            st.rerun()
        st.error("Mã không đúng. Bạn kiểm tra lại tin nhắn mời nhé.")
    st.stop()


# ------------------------------------------------------------------ rating widgets
def rate(sid: str, item_id: str, role: str) -> None:
    st.session_state.setdefault("_items", [])
    if item_id not in st.session_state._items:
        st.session_state._items.append(item_id)
    k = f"{sid}:{item_id}"
    if role == "student":
        st.feedback("thumbs", key=k + ":rating")
        return
    c1, c2, c3 = st.columns([2, 3, 5])
    c1.radio("Đánh giá", ["✓", "~", "✗"], index=None, horizontal=True, key=k + ":verdict",
             label_visibility="collapsed")
    c2.selectbox("Loại lỗi", list(PROBLEMS), format_func=PROBLEMS.get, key=k + ":problem",
                 label_visibility="collapsed")
    c3.text_input("Góp ý", key=k + ":comment", placeholder="Góp ý / đáp án đúng", label_visibility="collapsed")


def collect(sid: str, user: User) -> list[dict]:
    ss, rows = st.session_state, []
    for item in ss.get("_items", []) + ["GENERAL", "PRACTICE"]:
        k = f"{sid}:{item}"
        row = {"submission_id": sid, "created_at": now(), "tester": user.name, "role": user.role, "item_id": item,
               "rating": {1: "up", 0: "down"}.get(ss.get(k + ":rating"), ""),
               "verdict": ss.get(k + ":verdict") or "", "problem": ss.get(k + ":problem") or "",
               "comment": (ss.get(k + ":comment") or "").strip()}
        if any(row[c] for c in ("rating", "verdict", "problem", "comment")):
            rows.append(row)
    return rows


# ------------------------------------------------------------------ result display
def way_line(w: dict) -> str:
    return f"🗣️ *{w['sentence_en']}*  \n<small>**{STRATEGY_LABELS_VI[w['strategy']]}** — {w['note_vi']}</small>"


def show_coach(res: dict, role: str) -> None:
    r, sid = res["r"], res["sid"]
    fb = r["feedback"]
    st.success(f"👍 {fb['strength_vi']}")
    st.caption(f"Trình độ ước lượng: **{fb['level_cefr']}** — cách nói gợi ý bên dưới nằm trong tầm của bạn.")

    if fb["stuck_points"]:
        st.subheader("Chỗ bạn bị bí")
    for n, sp in enumerate(fb["stuck_points"], 1):
        with st.container(border=True):
            st.markdown(f"#### {n}. «{sp['vi_chunk']}»")
            st.markdown(f"**Ý bạn muốn nói:** {sp['meaning_vi']}  \n**Vì sao hay bí:** {sp['trap_vi']}")
            st.markdown("**Nói đơn giản bằng từ bạn đã biết:**")
            for w in sp["simple_ways"]:
                st.markdown(way_line(w), unsafe_allow_html=True)
            with st.expander("⭐ Từ xịn (bonus — xem sau khi đã đọc các cách trên)"):
                a = sp["advanced"]
                st.markdown(f"**{a['phrase_en']}** ({a['cefr']})  \n→ *{a['example_en']}*")
            rate(sid, f"S{n}", role)

    if fb["english_notes"]:
        st.subheader("Phần bạn đã nói bằng tiếng Anh")
        for n, note in enumerate(fb["english_notes"], 1):
            with st.container(border=True):
                st.markdown(f"> {note['quote_en']}")
                st.markdown(f"**{NOTE_LABELS_VI[note['type']]}:** {note['why_vi']}  \n"
                            f"→ *{note['better_en']}*  \n<small>{STRATEGY_LABELS_VI[note['strategy']]}</small>",
                            unsafe_allow_html=True)
                rate(sid, f"E{n}", role)

    st.subheader("Nói ý chính theo cách khác")
    with st.container(border=True):
        st.markdown(f"**Ý chính:** {fb['main_idea_vi']}")
        for w in fb["other_ways"]:
            st.markdown(way_line(w), unsafe_allow_html=True)
        rate(sid, "O", role)
    st.info(f"🎯 {fb['summary_vi']}")

    if role == "reviewer":
        for w in r["warnings"]:
            st.warning(w)
        m = r["meta"]
        st.caption(f"Chỗ tiếng Việt code tìm thấy: {r['detected_chunks']} · {m['prompt_version']} · "
                   f"{m['input_tokens']} in / {m['output_tokens']} out · {res['seconds']:.0f}s")


def show_upgrade(res: dict, role: str) -> None:
    u, sid = res["up"], res["sid"]
    up = u["upgrade"]
    st.subheader(f"⬆️ Nâng cấp lên {u['target_level']}")
    st.caption("Vẫn là bài của bạn — chỉ đổi vài chỗ để nghe tự nhiên và đa dạng hơn, không dùng từ khó.")
    marked = [{**c, "original_en": html.escape(c["original_en"]),
               "upgraded_en": f"<mark>{html.escape(c['upgraded_en'].strip().rstrip('.'))}</mark>"}
              for c in up["changes"]]
    body, _ = apply_changes(html.escape(up["base_answer_en"]), marked)
    with st.container(border=True):
        st.markdown(body, unsafe_allow_html=True)
    with st.expander("Xem bản trước khi nâng cấp"):
        st.write(up["base_answer_en"])
    for n, c in enumerate(up["changes"], 1):
        with st.container(border=True):
            st.markdown(f"**{n}. {CHANGE_LABELS_VI[c['type']]}**  \n~~{c['original_en']}~~  \n→ *{c['upgraded_en']}*  \n"
                        f"{c['why_vi']}")
            rate(sid, f"U{n}", role)
    st.markdown(f"#### 🗣️ Đến lượt bạn\n{up['practice_vi']}")
    st.text_area("Nói lại (gõ ra đây, không bắt buộc — gửi cùng đánh giá bên dưới)", key=f"{sid}:PRACTICE:comment")
    if role == "reviewer":
        for w in u["warnings"]:
            st.warning(w)
        m = u["meta"]
        st.caption(f"{m['prompt_version']} · {m['input_tokens']} in / {m['output_tokens']} out")


# ------------------------------------------------------------------ main page
user = login()
store = store_or_none()

with st.sidebar:
    st.markdown(f"👤 **{user.name}** · {'Giáo viên (reviewer)' if user.role == 'reviewer' else 'Học sinh'}")
    if "used" in st.session_state:
        st.caption(f"Còn {remaining(user, st.session_state.used, secret('limits'))} lượt hôm nay")
    if store is None:
        st.warning("Chế độ chưa lưu dữ liệu (thiếu cấu hình Google Sheet).")
    if st.button("Đăng xuất"):
        st.session_state.clear()
        st.rerun()

brand()

if "result" in st.session_state:
    res = st.session_state.result
    if st.button("✏️ Trả lời câu khác"):
        for k in ("result", "_items"):
            st.session_state.pop(k, None)
        st.rerun()
    st.markdown(f"**{res['question']}**  \n> {res['answer']}")
    show_coach(res, user.role)

    if "up" not in res:
        st.divider()
        st.markdown("Đã hiểu các cách nói đơn giản? Giờ thử làm câu trả lời **hay hơn một bậc**.")
        if st.button("⬆️ Nâng cấp câu trả lời", type="primary"):
            t0 = time.time()
            try:
                with st.spinner("Đang nâng cấp… khoảng 20–40 giây"):
                    u = upgrade(res["question"], res["answer"], res["r"]["feedback"])
            except Exception as e:
                u, err = None, str(e)
            save(store, submission_row(res["sid"], user.name, user.role, res["consent"], "upgrade", res["qid"],
                                       res["question"], res["answer"], u, time.time() - t0,
                                       status="ok" if u else f"error: {err}"[:300]))
            if u is None:
                st.error("Có lỗi khi nâng cấp, bạn thử lại nhé.")
                if user.role == "reviewer":
                    st.code(err)
            else:
                res["up"] = u
                st.rerun()
    else:
        st.divider()
        show_upgrade(res, user.role)

    st.divider()
    st.text_area("Góp ý chung (không bắt buộc)", key=f"{res['sid']}:GENERAL:comment")
    if st.button("📨 Gửi đánh giá", type="primary"):
        rows = collect(res["sid"], user)
        if not rows:
            st.warning("Bạn chưa đánh giá mục nào.")
        elif store:
            try:
                store.add_feedback(rows)
                st.success(f"Đã gửi {len(rows)} đánh giá. Cảm ơn bạn!")
            except Exception as e:
                st.error(f"Chưa gửi được, bạn thử lại nhé. ({e})")
        else:
            st.info("Chế độ dev — không lưu. Dữ liệu sẽ gửi:")
            st.json(rows)
    contact("result")
    st.stop()

hero(big=False)

questions = load_questions()
part = st.radio("Phần thi", [1, 2, 3, CUSTOM], horizontal=True,
                format_func=lambda p: "Tự nhập câu hỏi" if p == CUSTOM else PART_NAMES[p])
if part == CUSTOM:
    qid, question = CUSTOM, st.text_input("Câu hỏi", placeholder="Dán câu hỏi IELTS Speaking…")
else:
    pool = [q for q in questions if q["part"] == part]
    q = st.selectbox("Câu hỏi", pool, format_func=lambda q: f"{q['topic']} — {q['question']}")
    qid, question = q["id"], q["question"]

st.markdown("Trả lời bằng **tiếng Anh** như khi nói. Chỗ nào **bí từ, cứ viết tiếng Việt** — "
            "đó chính là chỗ công cụ sẽ dạy bạn.  \n<small>Ví dụ: *When I was sick, I had to pay viện phí.* "
            "Gõ không dấu thì để trong ngoặc vuông: *[vien phi]*.</small>", unsafe_allow_html=True)
answer = st.text_area("Câu trả lời của bạn", height=200)
wc = len(answer.split())
chunks = find_vi_chunks(answer) if answer.strip() else []
st.caption(f"{wc} từ" + (f" · Chỗ bí sẽ được dạy: {', '.join('«' + c + '»' for c in chunks)}" if chunks else ""))
consent = st.checkbox("Mình đồng ý cho lưu câu hỏi và câu trả lời để cải thiện công cụ (không bắt buộc)")
st.caption("Câu trả lời được gửi tới AI (Anthropic) để nhận xét. Nếu không tick ô trên, chỉ lưu số liệu thống kê.")

if st.button("🔎 Nhận xét cách diễn đạt", type="primary"):
    if not question.strip():
        st.error("Bạn chọn hoặc nhập câu hỏi nhé.")
        st.stop()
    if not MIN_WORDS <= wc <= MAX_WORDS:
        st.error(f"Câu trả lời cần từ {MIN_WORDS} đến {MAX_WORDS} từ (hiện có {wc}).")
        st.stop()
    if store:
        try:
            mine, total = store.usage_today(user.name)
        except Exception:
            mine, total = 0, 0
        st.session_state.used = mine
        msg = quota_message(user, mine, total, secret("limits"))
        if msg:
            st.error(msg)
            contact("limit")
            st.stop()
    sid, t0, r, err = uuid.uuid4().hex[:12], time.time(), None, None
    try:
        with st.spinner("Đang đọc câu trả lời… khoảng 20–40 giây, bạn đừng tắt trang nhé."):
            r = coach(question, answer)
    except Exception as e:
        err = str(e)
    seconds = time.time() - t0
    save(store, submission_row(sid, user.name, user.role, consent, "coach", qid, question, answer, r, seconds,
                               status="ok" if r else f"error: {err}"[:300]))
    if store and r:
        st.session_state.used = st.session_state.get("used", 0) + 1
    if r is None:
        st.error("Có lỗi khi nhận xét, bạn thử lại sau ít phút nhé.")
        if user.role == "reviewer":
            st.code(err)
        st.stop()
    st.session_state.result = {"sid": sid, "r": r, "seconds": seconds, "qid": qid, "question": question,
                               "answer": answer, "consent": consent}
    st.session_state.pop("_items", None)
    st.rerun()
