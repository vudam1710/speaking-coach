"""Giao diện theo nhận diện LogiQ Hub — CSS + các khối HTML dùng chung.

Màu cơ bản đặt trong .streamlit/config.toml (cách chính thức của Streamlit).
File này chỉ thêm những gì config không làm được: font Be Vietnam Pro, logo chữ, tiêu đề lớn,
nhãn nhỏ viết hoa giãn chữ, nút dạng viên thuốc, khối liên hệ Zalo.
Streamlit đổi tên class khi nâng cấp → nếu giao diện vỡ, chỉ cần sửa ở đây.
"""
import streamlit as st

PRIMARY, INK, MUTED, PANEL, BORDER = "#1F5EEA", "#111827", "#6B7280", "#F2F5FC", "#E5E7EB"
ZALO = ["0349 153 434", "0375 311 577"]

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

/* Font: chỉ đặt cho các phần tử chữ (không dùng *, để không làm hỏng font icon của Streamlit) */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp [data-testid="stMarkdownContainer"] {{
  font-family: 'Be Vietnam Pro', system-ui, sans-serif;
}}
.stApp h1, .stApp h2, .stApp h3 {{ font-weight: 800; letter-spacing: -0.01em; }}
.stApp h3 {{ color: {INK}; }}

/* Nút chính: viên thuốc, đậm */
.stButton button[kind="primary"], [data-testid="stBaseButton-primary"] {{
  border-radius: 999px; padding: 0.55rem 1.6rem; font-weight: 700;
}}
.stButton button[kind="secondary"], [data-testid="stBaseButton-secondary"] {{ border-radius: 999px; }}

/* Card viền nhạt (st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 16px; }}

/* Band: nhãn viết hoa giãn chữ như "HỌC PHÍ", số màu xanh */
[data-testid="stMetricLabel"] p {{ text-transform: uppercase; letter-spacing: .12em; font-size: .75rem; color: {MUTED}; }}
[data-testid="stMetricValue"] {{ color: {PRIMARY}; font-weight: 800; }}

/* ---- khối HTML riêng ---- */
.lq-brand {{ display: inline-flex; align-items: center; gap: .55rem; padding-bottom: .45rem;
  border-bottom: 3px solid {INK}; margin-bottom: 1.2rem; }}
.lq-dots {{ display: grid; grid-template-columns: repeat(2, 6px); gap: 3px; }}
.lq-dots span {{ width: 6px; height: 6px; border-radius: 50%; background: {INK}; }}
.lq-word {{ font-size: 1.35rem; color: {INK}; line-height: 1; }}
.lq-word b {{ font-weight: 800; }} .lq-word i {{ font-style: normal; font-weight: 400; color: #4B5563; }}
.lq-title {{ font-size: clamp(2rem, 6vw, 3.1rem); font-weight: 800; color: {PRIMARY};
  line-height: 1.08; letter-spacing: -0.02em; margin: 0 0 .9rem 0; }}
.lq-title.small {{ font-size: clamp(1.6rem, 4.5vw, 2.2rem); }}
.lq-tag {{ display: inline-block; border: 1.5px solid {PRIMARY}; color: {PRIMARY}; border-radius: 999px;
  padding: .3rem 1rem; font-weight: 600; font-size: .9rem; margin-bottom: 1rem; }}
.lq-lead {{ font-size: 1.05rem; color: {INK}; margin-bottom: 1.2rem; }}
.lq-lead em {{ font-style: normal; color: {PRIMARY}; font-weight: 700; }}
.lq-eyebrow {{ text-transform: uppercase; letter-spacing: .14em; font-size: .75rem; font-weight: 700; color: {PRIMARY}; }}
.lq-panel {{ background: {PANEL}; border-radius: 20px; padding: 1.4rem 1.6rem; margin: 1.5rem 0; }}
.lq-panel h4 {{ margin: .25rem 0 .4rem 0; font-size: 1.25rem; font-weight: 800; color: {INK}; }}
.lq-panel p {{ color: #374151; margin: 0 0 .8rem 0; }}
.lq-contact {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .8rem; }}
.lq-phones {{ font-weight: 600; color: {INK}; line-height: 1.6; }}
.lq-phones b {{ color: {PRIMARY}; }}
a.lq-cta {{ display: inline-block; background: {PRIMARY}; color: #fff !important; text-decoration: none;
  border-radius: 999px; padding: .7rem 1.6rem; font-weight: 700; }}
a.lq-cta:hover {{ filter: brightness(1.08); }}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def brand() -> None:
    """Logo chữ: ⁘ Speaking Coach by LogiQ Hub (dựng lại từ poster, chưa có file logo)."""
    st.markdown('<div class="lq-brand"><div class="lq-dots"><span></span><span></span><span></span><span></span>'
                '</div><div class="lq-word"><b>Speaking Coach</b> <i>by</i> <b>LogiQ</b> <i>Hub</i></div></div>',
                unsafe_allow_html=True)


def hero(big: bool = True) -> None:
    title = "Nói ý khó<br>bằng từ dễ" if big else "Luyện diễn đạt"
    st.markdown(f'<div class="lq-title{"" if big else " small"}">{title}</div>'
                '<div class="lq-tag">IELTS Speaking · Dùng cái em đã biết</div>', unsafe_allow_html=True)
    if big:
        st.markdown('<div class="lq-lead">Bí từ không phải vì em thiếu từ, mà vì em đang tìm <em>một cách nói duy nhất</em>. '
                    'Công cụ chỉ cho em <em>nhiều cách nói đơn giản</em> cho cùng một ý, rồi giúp em nói '
                    '<em>hay hơn một bậc</em>.</div>', unsafe_allow_html=True)


def contact(reason: str = "result") -> None:
    """Khối liên hệ Zalo (giống chân poster). reason: "result" (cuối trang kết quả) | "limit" (hết lượt)."""
    eyebrow, heading, text = {
        "limit": ("Hết lượt hôm nay", "Muốn được chữa bài thường xuyên?",
                  "Nhắn Zalo để được giáo viên luyện nói cùng và có lộ trình riêng cho bạn."),
        "result": ("Học cùng giáo viên", "Muốn luyện nói cùng giáo viên?",
                   "Công cụ cho bạn cách nghĩ — giáo viên giúp bạn luyện đến khi nói thành phản xạ."),
    }[reason]
    first = ZALO[0].replace(" ", "")
    phones = "<br>".join(f"Zalo <b>{p}</b>" for p in ZALO)
    st.markdown(f'<div class="lq-panel"><div class="lq-eyebrow">{eyebrow}</div><h4>{heading}</h4><p>{text}</p>'
                f'<div class="lq-contact"><div class="lq-phones">{phones}</div>'
                f'<a class="lq-cta" href="https://zalo.me/{first}" target="_blank">Nhắn Zalo cho giáo viên</a>'
                f'</div></div>', unsafe_allow_html=True)
