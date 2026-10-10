"""Export a whole topic set as ONE HTML file the learner downloads to study later (like writing-coach).

- Self-contained (CSS inline), LogiQ Hub colours; open in a browser, Ctrl+P → PDF.
- LEARNER version: no tokens, warnings or reviewer data.
- Built on the server and sent straight to the learner's device — nothing extra is stored.
- No streamlit import → testable with pytest.
"""
from datetime import datetime
from html import escape

from core.schema import CHANGE_LABELS_VI, NOTE_LABELS_VI, STRATEGY_LABELS_VI
from core.summary import set_summary
from core.upgrade import apply_changes

ZALO = ["0349 153 434", "0375 311 577"]
PART_NAMES = {1: "Part 1", 2: "Part 2", 3: "Part 3"}

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700;800&display=swap');
:root { --p:#1F5EEA; --ink:#111827; --muted:#6B7280; --panel:#F2F5FC; --border:#E5E7EB; }
* { box-sizing: border-box; }
body { margin:0; background:#fff; color:var(--ink); font-family:'Be Vietnam Pro',system-ui,sans-serif; line-height:1.55; }
.page { max-width:780px; margin:0 auto; padding:32px 20px 48px; }
.brand { display:inline-flex; align-items:center; gap:8px; border-bottom:3px solid var(--ink); padding-bottom:6px; font-size:1.1rem; }
.brand b { font-weight:800; } .brand i { font-style:normal; color:#4B5563; }
.dots { display:grid; grid-template-columns:repeat(2,5px); gap:3px; } .dots span { width:5px; height:5px; border-radius:50%; background:var(--ink); }
h1 { color:var(--p); font-size:2rem; font-weight:800; line-height:1.15; margin:20px 0 4px; letter-spacing:-.01em; }
h2 { font-size:1.25rem; font-weight:800; margin:32px 0 10px; padding-top:8px; border-top:1px solid var(--border); }
h3 { font-size:1.02rem; font-weight:700; margin:0 0 4px; }
.meta { color:var(--muted); font-size:.9rem; }
.eyebrow { text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:700; color:var(--p); margin-bottom:4px; }
.panel { background:var(--panel); border-radius:16px; padding:16px 20px; margin:14px 0; }
.card { border:1px solid var(--border); border-radius:14px; padding:14px 18px; margin:12px 0; break-inside:avoid; }
.tag { display:inline-block; font-size:.78rem; font-weight:600; border-radius:999px; padding:2px 10px; margin-right:6px;
  border:1px solid var(--border); color:var(--muted); }
.tag.high { color:#B91C1C; border-color:#FCA5A5; } .tag.medium { color:#B45309; border-color:#FCD34D; } .tag.low { color:#047857; border-color:#6EE7B7; }
blockquote { margin:8px 0; padding:6px 12px; border-left:3px solid var(--p); background:#FAFBFF; font-style:italic; }
.old { text-decoration:line-through; color:var(--muted); } .new { color:var(--p); font-weight:600; }
.ok { color:#047857; }
.essay { white-space:pre-wrap; font-size:.95rem; }
mark { background:#FEF3C7; padding:0 2px; border-radius:3px; }
.way { margin:4px 0 8px; } .way small { color:var(--muted); }
.lbl { font-size:.78rem; font-weight:600; color:var(--p); }
table { width:100%; border-collapse:collapse; font-size:.93rem; }
th, td { border-bottom:1px solid var(--border); padding:8px 6px; text-align:left; vertical-align:top; }
th { font-size:.72rem; text-transform:uppercase; letter-spacing:.1em; color:var(--muted); }
td.box { width:28px; font-size:1.1rem; color:var(--p); }
.bands { display:flex; gap:10px; flex-wrap:wrap; }
.band { flex:1; min-width:90px; border:1px solid var(--border); border-radius:12px; padding:10px; text-align:center; }
.band small { display:block; font-size:.7rem; letter-spacing:.12em; color:var(--muted); }
.band b { font-size:1.4rem; color:var(--p); }
.cta { display:inline-block; background:var(--p); color:#fff; text-decoration:none; border-radius:999px; padding:10px 20px; font-weight:700; }
.foot { color:var(--muted); font-size:.8rem; margin-top:28px; }
details summary { cursor:pointer; color:var(--p); font-weight:600; }
@media print { .page { padding:0; } h2 { break-after:avoid; } .cta { color:#fff; } details { display:block; } }
"""


def _e(x) -> str:
    return escape(str(x or ""))


def _way(w: dict) -> str:
    return (f'<div class="way">🗣️ <span class="new">{_e(w["sentence_en"])}</span><br>'
            f'<span class="lbl">{_e(STRATEGY_LABELS_VI[w["strategy"]])}</span> <small>— {_e(w["note_vi"])}</small></div>')


def _phrasebook(items: list[dict]) -> str:
    """The thing to keep: every stuck point → the simple ways → the advanced phrase, with a ☐ to tick."""
    rows = []
    for it in items:
        for sp in it["r"]["feedback"]["stuck_points"]:
            ways = "<br>".join(f'<span class="new">{_e(w["sentence_en"])}</span> '
                               f'<span class="meta">({_e(STRATEGY_LABELS_VI[w["strategy"]])})</span>'
                               for w in sp["simple_ways"])
            a = sp["advanced"]
            rows.append(f'<tr><td class="box">☐</td><td><b>{_e(sp["vi_chunk"])}</b><br>'
                        f'<span class="meta">{_e(sp["meaning_vi"])}</span></td><td>{ways}</td>'
                        f'<td>{_e(a["phrase_en"])}<br><span class="meta">{_e(a["cefr"])}</span></td></tr>')
    if not rows:
        return ""
    return ('<h2>📒 Sổ tay cách nói</h2><p class="meta">Những chỗ bạn đã bí và cách nói bằng từ bạn đã biết. '
            'Đánh dấu ☐ khi bạn tự nói được mà không cần nhìn.</p>'
            '<table><tr><th></th><th>Bạn muốn nói</th><th>Nói đơn giản</th><th>Từ xịn (bonus)</th></tr>'
            + "".join(rows) + "</table>")


def _answer(n: int, it: dict) -> str:
    fb = it["r"]["feedback"]
    out = [f"<h2>Câu {n}</h2><p><b>{_e(it['question'])}</b></p>",
           f'<blockquote class="essay">{_e(it["answer"])}</blockquote>', f"<p class='ok'>👍 {_e(fb['strength_vi'])}</p>"]
    for k, sp in enumerate(fb["stuck_points"], 1):
        a = sp["advanced"]
        out.append(f'<div class="card"><h3>Chỗ bí {k}: «{_e(sp["vi_chunk"])}»</h3>'
                   f'<p><b>Ý bạn muốn nói:</b> {_e(sp["meaning_vi"])}<br><b>Vì sao hay bí:</b> {_e(sp["trap_vi"])}</p>'
                   f'<p><b>Nói đơn giản bằng từ bạn đã biết:</b></p>' + "".join(_way(w) for w in sp["simple_ways"])
                   + f'<details><summary>⭐ Từ xịn (bonus)</summary><p><b>{_e(a["phrase_en"])}</b> ({_e(a["cefr"])})'
                     f' → <i>{_e(a["example_en"])}</i></p></details></div>')
    for e in fb["english_notes"]:
        out.append(f'<div class="card"><blockquote>{_e(e["quote_en"])}</blockquote>'
                   f'<p><b>{_e(NOTE_LABELS_VI[e["type"]])}:</b> {_e(e["why_vi"])}<br>→ <span class="new">{_e(e["better_en"])}</span> '
                   f'<span class="lbl">{_e(STRATEGY_LABELS_VI[e["strategy"]])}</span></p></div>')
    out.append(f'<div class="card"><h3>Nói ý chính theo cách khác</h3><p class="meta">{_e(fb["main_idea_vi"])}</p>'
               + "".join(_way(w) for w in fb["other_ways"]) + "</div>")
    out.append(f'<div class="panel">🎯 {_e(fb["summary_vi"])}</div>')
    up = it.get("up")
    if up:
        u = up["upgrade"]
        marked = [{**c, "original_en": _e(c["original_en"]),
                   "upgraded_en": f"<mark>{_e(c['upgraded_en'].strip().rstrip('.'))}</mark>"} for c in u["changes"]]
        body, _ = apply_changes(_e(u["base_answer_en"]), marked)
        out.append(f'<h3>⬆️ Nâng cấp lên {_e(up["target_level"])}</h3><div class="card essay">{body}</div><ol>'
                   + "".join(f'<li><span class="lbl">{_e(CHANGE_LABELS_VI[c["type"]])}</span><br>'
                             f'<span class="old">{_e(c["original_en"])}</span> → <span class="new">{_e(c["upgraded_en"])}</span>'
                             f'<br><span class="meta">{_e(c["why_vi"])}</span></li>' for c in u["changes"])
                   + f"</ol><p><b>🗣️ Đến lượt bạn:</b> {_e(u['practice_vi'])}</p>")
        if it.get("retell"):
            out.append(f'<p><b>Bạn đã nói lại:</b></p><blockquote>{_e(it["retell"])}</blockquote>')
    return "\n".join(out)


def build_html(part: int, topic: str, items: list[dict], created: datetime | None = None) -> str:
    """items: [{question, answer, r (coach result), up (upgrade result, optional), retell (optional)}]"""
    created = created or datetime.now()
    done = [it for it in items if it.get("r")]
    sm = set_summary([it["r"]["feedback"] for it in done])
    parts = [f'<div class="page"><div class="brand"><div class="dots"><span></span><span></span><span></span><span></span>'
             f'</div><span><b>Speaking Coach</b> <i>by</i> <b>LogiQ</b> <i>Hub</i></span></div>',
             f'<h1>Luyện diễn đạt · {_e(topic)}</h1><div class="meta">IELTS Speaking {PART_NAMES.get(part, "")} · '
             f'{created:%d/%m/%Y %H:%M}</div>',
             f'<div class="panel"><div class="eyebrow">Tổng kết</div><p>Câu đã trả lời <b>{sm["n_answers"]}</b> · '
             f'Chỗ bị bí <b>{sm["n_stuck"]}</b> · Trình độ ước lượng <b>{_e(sm["level"])}</b></p>'
             + (f'<p>{_e(sm["top_strategy_text"])}</p>' if sm["n_stuck"] else "") + "</div>",
             _phrasebook(done)]
    parts += [_answer(n, it) for n, it in enumerate(done, 1)]
    first = ZALO[0].replace(" ", "")
    parts.append(f'<div class="panel"><div class="eyebrow">Học cùng giáo viên</div><h3>Muốn luyện nói cùng giáo viên?</h3>'
                 f'<p>Zalo <b>{ZALO[0]}</b> · Zalo <b>{ZALO[1]}</b></p>'
                 f'<a class="cta" href="https://zalo.me/{first}">Nhắn Zalo cho giáo viên</a></div>'
                 f'<p class="foot">Tạo bởi Speaking Coach by LogiQ Hub — nói ý khó bằng từ dễ. '
                 f'Nhận xét do AI tạo, có thể chưa chính xác hoàn toàn.</p></div>')
    return (f'<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Luyện diễn đạt · {_e(topic)} · {created:%d-%m-%Y}</title><style>{_CSS}</style></head>'
            f'<body>{"".join(parts)}</body></html>')


def file_name(topic: str, created: datetime | None = None) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in topic.lower()).strip("-")
    return f"luyen-noi-{slug}-{(created or datetime.now()):%Y%m%d-%H%M}.html"
