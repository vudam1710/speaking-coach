"""Statistics page for reviewers — reads straight from the Google Sheet (like writing-coach).

compute_stats(): pure pandas → testable. render(): Streamlit.
Charts: 1 series per chart, 1 colour (primary), no legend; rates shown in TABLES with a progress bar
(numbers always visible, never colour only).
"""
import json
from collections import Counter

import pandas as pd

from evaluation.score import GROUPS, group

# USD / 1M tokens (Sonnet — check current pricing). input_tokens from the API excludes cache reads.
PRICE_IN, PRICE_CACHE_READ, PRICE_OUT = 3.0, 0.3, 15.0
PART_NAMES = {"1": "Part 1", "2": "Part 2", "3": "Part 3"}


def _num(s: pd.DataFrame, cols) -> None:
    for c in cols:
        s[c] = pd.to_numeric(s.get(c), errors="coerce").fillna(0)


def _feedback_of(row) -> dict | None:
    try:
        return json.loads(row)["feedback"] if row else None
    except (ValueError, KeyError, TypeError):
        return None


def compute_stats(subs: list[dict], feedback: list[dict]) -> dict:
    s = pd.DataFrame(subs)
    out = {"n_answers": 0}
    if s.empty:
        return out
    s["date"] = s["created_at"].astype(str).str[:10]
    s["status"] = s["status"].astype(str)
    _num(s, ["input_tokens", "output_tokens", "cache_read_tokens", "seconds"])
    s["cost"] = ((s["input_tokens"] * PRICE_IN + s["cache_read_tokens"] * PRICE_CACHE_READ
                  + s["output_tokens"] * PRICE_OUT) / 1e6).where(s["status"] == "ok", 0)   # reused = free
    coach = s[s["step"] == "coach"].copy()
    ok = coach[coach["status"].str.startswith("ok")]
    llm = s[s["step"].isin(["coach", "upgrade"]) & (s["status"] == "ok")]      # real API calls (not "ok (cached)")
    upgrades = s[(s["step"] == "upgrade") & (s["status"] == "ok")]
    retells = s[s["step"] == "practice"]
    today = pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").strftime("%Y-%m-%d")

    coach["part"] = coach["question_id"].astype(str).str[1:2].map(PART_NAMES).fillna("Khác")
    coach["topic"] = coach["question_id"].astype(str).str.rsplit("_", n=1).str[0]
    fbs = coach["result_json"].map(_feedback_of) if "result_json" in coach else pd.Series(dtype=object)
    coach["n_stuck"] = fbs.map(lambda f: len(f["stuck_points"]) if f else None)
    coach["level"] = fbs.map(lambda f: f["level_cefr"] if f else None)
    chunks = Counter(sp["vi_chunk"].lower() for f in fbs if f for sp in f["stuck_points"])
    strategies = Counter(w["strategy"] for f in fbs if f for sp in f["stuck_points"] for w in sp["simple_ways"])
    cost = s["cost"].sum()
    in_all = (llm["input_tokens"] + llm["cache_read_tokens"]).sum()

    out.update({
        "n_answers": len(coach),
        "n_today": int((coach["date"] == today).sum()),
        "n_sets": coach["set_id"].nunique(),
        "n_users": coach["tester"].nunique(),
        "n_errors": int((~coach["status"].str.startswith("ok")).sum()),
        "n_reused": int((coach["status"] == "ok (cached)").sum()),
        "avg_seconds": ok.loc[ok["status"] == "ok", "seconds"].mean(),
        "cost_usd": cost,
        "cost_per_answer": cost / len(ok) if len(ok) else 0.0,
        "cache_share": (llm["cache_read_tokens"].sum() / in_all) if in_all else 0.0,
        "upgrade_rate": len(upgrades) / len(ok) if len(ok) else 0.0,
        "retell_rate": len(retells) / len(upgrades) if len(upgrades) else 0.0,
        "stuck_per_answer": coach["n_stuck"].mean(),
        "share_with_stuck": (coach["n_stuck"] > 0).mean() if coach["n_stuck"].notna().any() else 0.0,
        "per_day": coach.groupby("date").size().rename("Số câu trả lời"),
        "per_part": coach.groupby("part").size().rename("Số câu trả lời"),
        "topics": coach.groupby("topic").agg(so_cau=("submission_id", "size"), so_bo=("set_id", "nunique"))
                       .sort_values("so_cau", ascending=False).rename(columns={"so_cau": "Số câu", "so_bo": "Số bộ"}),
        "top_chunks": pd.Series(dict(chunks.most_common(20)), name="Số lần", dtype="int64"),
        "strategies": pd.Series(dict(strategies.most_common()), name="Số cách nói", dtype="int64"),
    })
    per_user = coach.groupby(["tester", "role"]).agg(
        cau=("submission_id", "size"), bo=("set_id", "nunique"), hom_nay=("date", lambda d: int((d == today).sum())),
        bi_tb=("n_stuck", "mean"), trinh_do=("level", lambda x: x.mode().iat[0] if x.notna().any() else ""),
        lan_cuoi=("created_at", "max")).reset_index()
    per_user["nang_cap"] = per_user["tester"].map(upgrades.groupby("tester").size()).fillna(0).astype(int)
    per_user["noi_lai"] = per_user["tester"].map(retells.groupby("tester").size()).fillna(0).astype(int)
    out["per_user"] = per_user.sort_values("cau", ascending=False).rename(columns={
        "tester": "Người dùng", "role": "Vai trò", "cau": "Câu", "bo": "Bộ", "hom_nay": "Hôm nay",
        "bi_tb": "Chỗ bí / câu", "trinh_do": "Trình độ", "lan_cuoi": "Lần cuối",
        "nang_cap": "Nâng cấp", "noi_lai": "Nói lại"})
    # progress: stuck points per answer by week, per learner (falling = learner gets stuck less often)
    coach["week"] = pd.to_datetime(coach["date"], errors="coerce").dt.strftime("%G-W%V")
    out["progress"] = (coach.pivot_table(index="tester", columns="week", values="n_stuck", aggfunc="mean")
                       .round(1)) if coach["n_stuck"].notna().any() else pd.DataFrame()
    out["recent"] = (s.sort_values("created_at", ascending=False)
                     [["created_at", "tester", "step", "question_id", "seconds", "input_tokens",
                       "cache_read_tokens", "output_tokens", "status"]].head(30))

    f = pd.DataFrame(feedback)
    if not f.empty:
        f = f.sort_values("created_at").drop_duplicates(["submission_id", "item_id", "tester"], keep="last")
        rv = f[(f["role"] == "reviewer") & (f["verdict"].astype(str) != "")].copy()
        if not rv.empty:
            rv["Phần"] = rv["item_id"].astype(str).map(lambda i: GROUPS.get(group(i), group(i)))
            v = rv.groupby("Phần")["verdict"].value_counts().unstack(fill_value=0)
            v.columns.name = None
            for c in ("✓", "~", "✗"):
                if c not in v:
                    v[c] = 0
            v = v[["✓", "~", "✗"]]
            v["Tỉ lệ ✓"] = v["✓"] / v.sum(axis=1)
            out["reviewer"] = v.sort_values("Tỉ lệ ✓")
            out["problems"] = rv[rv["problem"].astype(str) != ""]["problem"].value_counts().rename("Số lần")
        out["comments"] = (f[f["comment"].astype(str).str.strip() != ""]
                           [["created_at", "tester", "item_id", "comment"]]
                           .sort_values("created_at", ascending=False).head(30))
    return out


def render(store) -> None:
    import streamlit as st

    from core.schema import STRATEGY_LABELS_VI
    st.markdown('<div class="lq-title small">Thống kê</div>', unsafe_allow_html=True)
    if store is None:
        st.info("Chưa kết nối Google Sheet nên chưa có dữ liệu.")
        return

    @st.cache_data(ttl=60, show_spinner="Đang đọc Google Sheet…")
    def load(_store, key):
        return _store.all_records()

    if st.button("🔄 Làm mới"):
        load.clear()
    subs, fb = load(store, "all")
    d = compute_stats(subs, fb)
    if d["n_answers"] == 0:
        st.info("Chưa có câu trả lời nào.")
        return

    c = st.columns(4)
    c[0].metric("Câu trả lời", d["n_answers"], f"+{d['n_today']} hôm nay")
    c[1].metric("Bộ câu hỏi", d["n_sets"])
    c[2].metric("Người dùng", d["n_users"])
    c[3].metric("Chi phí ước tính", f"${d['cost_usd']:.2f}")
    c = st.columns(4)
    c[0].metric("Chờ trung bình", f"{d['avg_seconds']:.0f}s" if pd.notna(d["avg_seconds"]) else "—")
    c[1].metric("Chỗ bí / câu", f"{d['stuck_per_answer']:.1f}" if pd.notna(d["stuck_per_answer"]) else "—")
    c[2].metric("Bấm nâng cấp", f"{d['upgrade_rate']:.0%}")
    c[3].metric("Nói lại sau nâng cấp", f"{d['retell_rate']:.0%}")
    st.caption(f"Câu có ít nhất 1 chỗ bí: {d['share_with_stuck']:.0%} · Lỗi: {d['n_errors']} · "
               f"Nộp trùng (không tốn token): {d['n_reused']} · Token đọc từ cache: {d['cache_share']:.0%} · "
               f"Trung bình \\${d['cost_per_answer']:.3f}/câu (cả nâng cấp) — tính theo \\${PRICE_IN:g} vào / "
               f"\\${PRICE_CACHE_READ:g} cache / \\${PRICE_OUT:g} ra mỗi triệu token, chỉ ước tính.")

    st.markdown("#### Số câu trả lời theo ngày")
    st.bar_chart(d["per_day"], color="#1F5EEA", height=220, x_label="", y_label="Số câu")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Học sinh hay bí ở đâu")
        st.caption("Chỗ tiếng Việt xuất hiện nhiều nhất — gợi ý chủ đề cho buổi dạy.")
        st.dataframe(d["top_chunks"], use_container_width=True)
    with col2:
        st.markdown("#### Chiến lược tool gợi ý")
        st.dataframe(d["strategies"].rename(index=STRATEGY_LABELS_VI), use_container_width=True)

    pct = {"format": "percent", "min_value": 0, "max_value": 1}
    if "reviewer" in d:
        st.markdown("#### Giáo viên chấm theo phần")
        st.caption("Phần có tỉ lệ ✓ thấp nhất ở trên cùng — chỉ tính phần chấm trên app; "
                   "chấm trên file CSV thì xem bằng `evaluation/score.py`.")
        st.dataframe(d["reviewer"], use_container_width=True,
                     column_config={"Tỉ lệ ✓": st.column_config.ProgressColumn("Tỉ lệ ✓", **pct)})
        if len(d.get("problems", [])):
            st.markdown("**Loại lỗi gắn nhiều nhất**")
            st.dataframe(d["problems"], use_container_width=True)

    st.markdown("#### Người dùng")
    st.dataframe(d["per_user"], use_container_width=True, hide_index=True,
                 column_config={"Chỗ bí / câu": st.column_config.NumberColumn(format="%.1f")})
    if not d["progress"].empty and d["progress"].shape[1] > 1:
        with st.expander("Tiến bộ: số chỗ bí trung bình mỗi câu, theo tuần (giảm dần = tốt)"):
            st.dataframe(d["progress"], use_container_width=True)
    with st.expander("Phần thi & chủ đề"):
        st.dataframe(d["per_part"], use_container_width=True)
        st.dataframe(d["topics"], use_container_width=True)
    if len(d.get("comments", [])):
        with st.expander(f"Góp ý gần đây ({len(d['comments'])})"):
            st.dataframe(d["comments"], use_container_width=True, hide_index=True)
    with st.expander("30 lượt gần nhất"):
        st.dataframe(d["recent"], use_container_width=True, hide_index=True)
    st.caption("Review chi tiết từng nhận xét: chạy `python evaluation/pull_sheet.py` ở máy (xem docs/review_guide.md).")
