"""Speaking Coach — Streamlit UI (pilot).

Flow: access code → pick a topic set (Part 1 / Part 3: 3–5 questions; Part 2: one cue card)
→ answer all questions (Vietnamese where stuck) → ONE click analyses every answer in parallel
→ set summary (computed by code) + one tab per answer → optional upgrade per answer → rate items.

Cost control: quota counts answers (= LLM calls), identical resubmissions reuse the earlier result,
prompt caching in core/llm.py. Without secrets → dev mode (nothing saved).
"""
import hashlib
import html
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
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
from core.summary import set_summary  # noqa: E402
from core.storage import SheetStore, now, submission_row  # noqa: E402
from core.upgrade import apply_changes, upgrade  # noqa: E402
from evaluation.render import PROBLEMS_VI as PROBLEMS  # noqa: E402  (same labels as review_items.csv)
from ui.theme import apply_theme, brand, contact, hero  # noqa: E402

MIN_WORDS = 5
MAX_WORDS = {1: 150, 2: 400, 3: 250}
PART_NAMES = {1: "Part 1", 2: "Part 2", 3: "Part 3"}
STAGGER_SECONDS = 2.0   # let the 1st call write the prompt cache before the others start


st.set_page_config(page_title="Speaking Coach · LogiQ Hub", page_icon="🗣️", layout="centered")
apply_theme()


@st.cache_data
def load_sets() -> list[dict]:
    path = Path(__file__).parent / "data" / "questions.json"
    return json.loads(path.read_text(encoding="utf-8"))["sets"]


@st.cache_resource(show_spinner=False)
def get_store():
    info, sheet_id = secret("gcp_service_account"), secret("SHEET_ID")
    if not (info and sheet_id):
        return None
    return SheetStore(info, sheet_id)


@st.cache_resource(show_spinner=False)
def result_memo() -> dict:
    """Shared across users of this server: (question, answer) hash → coach() result. Stops spam resubmits."""
    return {}


def _key(question: str, answer: str) -> str:
    return hashlib.sha256(f"{question.strip()}\n{' '.join(answer.split())}".encode()).hexdigest()


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
    if (sid, item_id) not in st.session_state._items:
        st.session_state._items.append((sid, item_id))
    if role != "reviewer":          # students only read & practise; the teacher reviews everything
        return
    k = f"{sid}:{item_id}"
    c1, c2, c3 = st.columns([2, 3, 5])
    c1.radio("Đánh giá", ["✓", "~", "✗"], index=None, horizontal=True, key=k + ":verdict",
             label_visibility="collapsed")
    c2.selectbox("Loại lỗi", list(PROBLEMS), format_func=PROBLEMS.get, key=k + ":problem",
                 label_visibility="collapsed")
    c3.text_input("Góp ý", key=k + ":comment", placeholder="Góp ý / đáp án đúng", label_visibility="collapsed")


def collect(res: dict, user: User) -> list[dict]:
    ss, rows = st.session_state, []
    items = ss.get("_items", []) + [(res["set_id"], "GENERAL")]
    for sid, item in items:
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


def show_summary(res: dict) -> None:
    """Set-level summary computed by code (core/summary.py, no extra LLM call)."""
    sm = set_summary([it["r"]["feedback"] for it in res["items"] if it.get("r")])
    with st.container(border=True):
        st.markdown("#### 📊 Tổng kết bộ câu hỏi")
        c1, c2, c3 = st.columns(3)
        c1.metric("Câu đã trả lời", sm["n_answers"])
        c2.metric("Chỗ bị bí", sm["n_stuck"])
        c3.metric("Trình độ ước lượng", sm["level"])
        if sm["n_stuck"]:
            st.markdown("**Những chỗ bạn bí:** " + " · ".join(f"«{c}»" for c in sm["chunks"]))
            st.markdown(sm["top_strategy_text"])
        else:
            st.markdown("Bạn không để lại chỗ tiếng Việt nào 👏 — xem từng câu để thấy thêm cách nói khác cho cùng ý.")


def show_coach(it: dict, role: str) -> None:
    r, sid = it["r"], it["sid"]
    fb = r["feedback"]
    st.success(f"👍 {fb['strength_vi']}")
    for n, sp in enumerate(fb["stuck_points"], 1):
        with st.container(border=True):
            st.markdown(f"#### Chỗ bí {n}: «{sp['vi_chunk']}»")
            st.markdown(f"**Ý bạn muốn nói:** {sp['meaning_vi']}  \n**Vì sao hay bí:** {sp['trap_vi']}")
            st.markdown("**Nói đơn giản bằng từ bạn đã biết:**")
            for w in sp["simple_ways"]:
                st.markdown(way_line(w), unsafe_allow_html=True)
            with st.expander("⭐ Từ xịn (bonus — xem sau khi đã đọc các cách trên)"):
                a = sp["advanced"]
                st.markdown(f"**{a['phrase_en']}** ({a['cefr']})  \n→ *{a['example_en']}*")
            rate(sid, f"S{n}", role)
    for n, note in enumerate(fb["english_notes"], 1):
        with st.container(border=True):
            st.markdown(f"> {note['quote_en']}")
            st.markdown(f"**{NOTE_LABELS_VI[note['type']]}:** {note['why_vi']}  \n"
                        f"→ *{note['better_en']}*  \n<small>{STRATEGY_LABELS_VI[note['strategy']]}</small>",
                        unsafe_allow_html=True)
            rate(sid, f"E{n}", role)
    with st.container(border=True):
        st.markdown(f"**Nói ý chính theo cách khác** — {fb['main_idea_vi']}")
        for w in fb["other_ways"]:
            st.markdown(way_line(w), unsafe_allow_html=True)
        rate(sid, "O", role)
    st.info(f"🎯 {fb['summary_vi']}")
    rate(sid, "SUM", role)
    if role == "reviewer":
        st.caption(f"[L] Trình độ ước lượng câu này: **{fb['level_cefr']}**")
        rate(sid, "L", role)
        for w in r["warnings"]:
            st.warning(w)
        m = r["meta"]
        st.caption(f"Code tìm thấy: {r['detected_chunks']} · {m['prompt_version']} · {m['input_tokens']} in "
                   f"({m.get('cache_read_tokens', 0)} cached) / {m['output_tokens']} out · {it['seconds']:.0f}s"
                   + (" · dùng lại kết quả cũ" if it.get("cached") else ""))


def show_upgrade(it: dict, role: str) -> None:
    u, sid = it["up"], it["sid"]
    up = u["upgrade"]
    st.markdown(f"#### ⬆️ Nâng cấp lên {u['target_level']}")
    st.caption("Vẫn là câu trả lời của bạn — chỉ đổi vài chỗ để nghe tự nhiên và đa dạng hơn, không dùng từ khó.")
    marked = [{**c, "original_en": html.escape(c["original_en"]),
               "upgraded_en": f"<mark>{html.escape(c['upgraded_en'].strip().rstrip('.'))}</mark>"}
              for c in up["changes"]]
    body, _ = apply_changes(html.escape(up["base_answer_en"]), marked)
    with st.container(border=True):
        st.markdown(body, unsafe_allow_html=True)
        st.caption("Cả bài sau khi nâng cấp — vẫn giống câu trả lời của bạn chứ?")
        rate(sid, "UP", role)
    for n, c in enumerate(up["changes"], 1):
        with st.container(border=True):
            st.markdown(f"**{n}. {CHANGE_LABELS_VI[c['type']]}**  \n~~{c['original_en']}~~  \n→ *{c['upgraded_en']}*  \n"
                        f"{c['why_vi']}")
            rate(sid, f"U{n}", role)
    st.markdown(f"**🗣️ Đến lượt bạn:** {up['practice_vi']}")
    retell = st.text_area("Nói lại (gõ ra đây, không bắt buộc)", key=f"{sid}:PRACTICE")
    if retell.strip() and st.button("📩 Gửi cho giáo viên xem", key=f"{sid}:PRACTICE:send"):
        save(st.session_state.get("_store"), submission_row(
            sid, st.session_state.result["set_id"], st.session_state.user.name, st.session_state.user.role, True,
            "practice", it["qid"], it["question"], retell, None, 0, status="ok"))
        st.success("Đã gửi. Giáo viên sẽ xem bài nói lại của bạn.")
    if role == "reviewer":
        for w in u["warnings"]:
            st.warning(w)


def upgrade_button(it: dict, res: dict, user: User, store) -> None:
    st.markdown("Đã hiểu các cách nói đơn giản? Thử làm câu trả lời này **hay hơn một bậc**.")
    if not st.button("⬆️ Nâng cấp câu trả lời này", key=f"up:{it['sid']}"):
        return
    t0, u, err = time.time(), None, ""
    try:
        with st.spinner("Đang nâng cấp… khoảng 20–40 giây"):
            u = upgrade(it["question"], it["answer"], it["r"]["feedback"])
    except Exception as e:
        err = str(e)
    save(store, submission_row(it["sid"], res["set_id"], user.name, user.role, res["consent"], "upgrade", it["qid"],
                               it["question"], it["answer"], u, time.time() - t0,
                               status="ok" if u else f"error: {err}"[:300]))
    if u is None:
        st.error("Có lỗi khi nâng cấp, bạn thử lại nhé.")
        if user.role == "reviewer":
            st.code(err)
        return
    it["up"] = u
    st.rerun()


def reviewer_submit(res: dict, user: User, store) -> None:
    st.divider()
    st.text_area("Góp ý chung cho bộ này (không bắt buộc)", key=f"{res['set_id']}:GENERAL:comment")
    if st.button("📨 Gửi đánh giá", type="primary"):
        rows = collect(res, user)
        if not rows:
            st.warning("Bạn chưa đánh giá mục nào.")
        elif store:
            try:
                store.add_feedback(rows)
                st.success(f"Đã gửi {len(rows)} đánh giá.")
            except Exception as e:
                st.error(f"Chưa gửi được, thử lại nhé. ({e})")
        else:
            st.info("Chế độ dev — không lưu. Dữ liệu sẽ gửi:")
            st.json(rows)


# ------------------------------------------------------------------ analysis
def run_set(todo: list[dict]) -> None:
    """Fill it['r'] / it['error'] / it['seconds'] for every answer; parallel, first call staggered."""
    memo = result_memo()

    def one(it):
        t0 = time.time()
        k = _key(it["question"], it["answer"])
        if k in memo:
            it.update(r=memo[k], cached=True, seconds=0.0)
            return
        try:
            it["r"] = coach(it["question"], it["answer"])
            memo[k] = it["r"]
        except Exception as e:
            it["error"] = str(e)
        it["seconds"] = time.time() - t0

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = []
        for n, it in enumerate(todo):
            futures.append(pool.submit(one, it))
            if n == 0 and len(todo) > 1:
                time.sleep(STAGGER_SECONDS)
        for f in futures:
            f.result()


# ------------------------------------------------------------------ main page
user = login()
store = store_or_none()
st.session_state._store = store
if store is None and user.role == "student":
    # No Sheet → no quota enforcement → students could spend unlimited tokens. Only reviewers/dev may continue.
    brand()
    st.error("Hệ thống đang bảo trì, bạn quay lại sau ít phút nhé.")
    st.stop()
sets = load_sets()
by_id = {s["id"]: s for s in sets}

with st.sidebar:
    st.markdown(f"👤 **{user.name}** · {'Giáo viên (reviewer)' if user.role == 'reviewer' else 'Học sinh'}")
    if "used" in st.session_state:
        st.caption(f"Còn {remaining(user, st.session_state.used, secret('limits'))} câu trả lời hôm nay")
    if store is None:
        st.warning("Chế độ chưa lưu dữ liệu (thiếu cấu hình Google Sheet).")
    if st.button("Đăng xuất"):
        st.session_state.clear()
        st.rerun()

brand()

# ---- result page
if "result" in st.session_state:
    res = st.session_state.result
    qset = by_id[res["set_id_base"]]
    c1, c2 = st.columns(2)
    if c1.button("✏️ Làm bộ câu hỏi khác"):
        for k in ("result", "_items"):
            st.session_state.pop(k, None)
        st.rerun()
    if qset.get("part3") and c2.button("➡️ Làm tiếp Part 3 cùng chủ đề", type="primary"):
        for k in ("result", "_items"):
            st.session_state.pop(k, None)
        st.session_state.pick = qset["part3"]
        st.rerun()
    st.markdown(f"### {PART_NAMES[qset['part']]} · {qset['topic']}")
    show_summary(res)
    done = [it for it in res["items"] if it.get("r")]
    for it in res["items"]:
        if it.get("error"):
            st.error(f"Câu {it['n']}: có lỗi khi nhận xét, bạn thử lại sau nhé."
                     + (f" ({it['error']})" if user.role == "reviewer" else ""))
    tabs = st.tabs([f"Câu {it['n']}" for it in done]) if len(done) > 1 else [st.container()]
    for tab, it in zip(tabs, done):
        with tab:
            st.markdown(f"**{it['question']}**  \n> {it['answer']}")
            show_coach(it, user.role)
            st.divider()
            if "up" in it:
                show_upgrade(it, user.role)
            else:
                upgrade_button(it, res, user, store)
    if user.role == "reviewer":
        reviewer_submit(res, user, store)
    contact("result")
    st.stop()


# ---- input page
hero(big=False)
pick = st.session_state.pop("pick", None)
default_part = by_id[pick]["part"] if pick else 1
part = st.radio("Phần thi", [1, 2, 3], index=default_part - 1, horizontal=True, format_func=PART_NAMES.get)
pool = [s for s in sets if s["part"] == part]
idx = next((i for i, s in enumerate(pool) if s["id"] == pick), 0)
qset = st.selectbox("Chủ đề", pool, index=idx, format_func=lambda s: s["topic"], key=f"topic:{part}")

st.markdown("Trả lời bằng **tiếng Anh** như khi nói. Chỗ nào **bí từ, cứ viết tiếng Việt** — "
            "đó chính là chỗ công cụ sẽ dạy bạn.  \n<small>Ví dụ: *When I was sick, I had to pay viện phí.* "
            "Gõ không dấu thì để trong ngoặc vuông: *[vien phi]*. Câu nào chưa muốn làm thì để trống.</small>",
            unsafe_allow_html=True)

answers = []
for n, q in enumerate(qset["questions"], 1):
    label = f"**{n}. {q}**" if part != 2 else f"**{q}**"
    a = st.text_area(label, key=f"ans:{qset['id']}:{n}", height=220 if part == 2 else 110,
                     placeholder="Bạn có 1 phút chuẩn bị, rồi nói 1–2 phút." if part == 2 else "")
    wc = len(a.split())
    chunks = find_vi_chunks(a) if a.strip() else []
    if a.strip():
        st.caption(f"{wc} từ" + (f" · Chỗ bí sẽ được dạy: {', '.join('«' + c + '»' for c in chunks)}" if chunks else ""))
    answers.append((n, q, a, wc))

filled = [(n, q, a, wc) for n, q, a, wc in answers if a.strip()]
consent = True   # pilot: every answer + feedback is stored so the teacher can review all of it
st.caption("Câu trả lời được gửi tới AI (Anthropic) để nhận xét, và được **lưu lại để giáo viên đọc** "
           "và kiểm tra nhận xét của công cụ. Mỗi câu trả lời tính là 1 lượt.")

if st.button(f"🔎 Nhận xét {len(filled)} câu trả lời" if filled else "🔎 Nhận xét", type="primary"):
    if not filled:
        st.error("Bạn trả lời ít nhất 1 câu nhé.")
        st.stop()
    bad = [n for n, q, a, wc in filled if not MIN_WORDS <= wc <= MAX_WORDS[part]]
    if bad:
        st.error(f"Câu {', '.join(map(str, bad))}: mỗi câu trả lời cần từ {MIN_WORDS} đến {MAX_WORDS[part]} từ.")
        st.stop()
    if store:
        try:
            mine, total = store.usage_today(user.name)
        except Exception:
            mine, total = 0, 0
        st.session_state.used = mine
        msg = quota_message(user, mine, total, secret("limits"), needed=len(filled))
        if msg:
            st.error(msg)
            contact("limit")
            st.stop()
    set_sid = uuid.uuid4().hex[:10]
    items = [{"n": n, "qid": f"{qset['id']}_{n}", "question": q, "answer": a, "sid": f"{set_sid}-{n}"}
             for n, q, a, wc in filled]
    with st.spinner(f"Đang nhận xét {len(items)} câu cùng lúc… khoảng 30–60 giây, bạn đừng tắt trang nhé."):
        run_set(items)
    for it in items:
        save(store, submission_row(it["sid"], set_sid, user.name, user.role, consent, "coach", it["qid"],
                                   it["question"], it["answer"], it.get("r"), it.get("seconds", 0),
                                   status=("ok (cached)" if it.get("cached") else "ok") if it.get("r")
                                   else f"error: {it.get('error')}"[:300]))
    if store:
        st.session_state.used = st.session_state.get("used", 0) + len(items)
    if not any(it.get("r") for it in items):
        st.error("Có lỗi khi nhận xét, bạn thử lại sau ít phút nhé.")
        if user.role == "reviewer":
            st.code(items[0].get("error"))
        st.stop()
    st.session_state.result = {"set_id": set_sid, "set_id_base": qset["id"], "items": items, "consent": consent}
    st.session_state.pop("_items", None)
    st.rerun()
