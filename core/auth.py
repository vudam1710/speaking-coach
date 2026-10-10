"""Mã truy cập + trần số lượt (giai đoạn test với người dùng). Không phụ thuộc Streamlit → test được.

Google login (st.login) như thiết kế mục 8 để sau; giai đoạn test dùng MÃ TRUY CẬP riêng cho từng người.

secrets.toml:
    [access_codes]
    minh_hs = "minh-2841"                                  # mặc định role = student
    co_lan  = { code = "lan-7392", role = "reviewer" }

    [limits]                                               # không bắt buộc
    student_daily = 10
    reviewer_daily = 20
    global_daily = 50
"""
from collections.abc import Mapping
from dataclasses import dataclass

ROLES = ("student", "reviewer")
DEFAULT_LIMITS = {"student_daily": 10, "reviewer_daily": 20, "global_daily": 50}


@dataclass(frozen=True)
class User:
    name: str
    role: str   # "student" | "reviewer"


def load_codes(access_codes: dict) -> dict[str, User]:
    """{tên: "mã"} hoặc {tên: {code, role}} → {mã: User}. Bỏ qua dòng sai định dạng."""
    out = {}
    for name, v in (access_codes or {}).items():
        if isinstance(v, str):
            code, role = v, "student"
        elif isinstance(v, Mapping) and v.get("code"):   # st.secrets trả AttrDict, không phải dict
            code, role = v["code"], v.get("role", "student")
        else:
            continue
        if role not in ROLES:
            role = "student"
        out[str(code).strip()] = User(name=name, role=role)
    return out


def check_code(code: str, codes: dict[str, User]) -> User | None:
    return codes.get((code or "").strip())


def quota_message(user: User, used_by_user: int, used_total: int, limits: dict | None = None) -> str | None:
    """None = được chạy tiếp; ngược lại trả câu báo lỗi (tiếng Việt) để hiện cho người dùng."""
    lim = {**DEFAULT_LIMITS, **(limits or {})}
    if used_total >= lim["global_daily"]:
        return "Hôm nay hệ thống đã đạt giới hạn số bài. Bạn quay lại vào ngày mai nhé."
    mine = lim["reviewer_daily"] if user.role == "reviewer" else lim["student_daily"]
    if used_by_user >= mine:
        return f"Bạn đã dùng hết {mine} lượt hôm nay. Hẹn bạn ngày mai nhé!"
    return None


def remaining(user: User, used_by_user: int, limits: dict | None = None) -> int:
    lim = {**DEFAULT_LIMITS, **(limits or {})}
    mine = lim["reviewer_daily"] if user.role == "reviewer" else lim["student_daily"]
    return max(0, mine - used_by_user)

