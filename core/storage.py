"""Save submissions + ratings to a dedicated Google Sheet (gspread + service account).

Adapted from writing-coach. Tab `submissions`: 1 row per LLM step (step = coach | upgrade).
Without consent, question_text / answer / result_json are left empty.
Tab `feedback`: 1 row per rated item (student: up/down; reviewer: ✓/~/✗ + problem + comment).
Tabs and headers are created on first run.
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

SUBMISSION_COLS = ["submission_id", "created_at", "tester", "role", "consent", "step", "question_id",
                   "question", "answer", "level_cefr", "n_stuck", "n_warnings", "prompt_version", "model",
                   "llm_calls", "input_tokens", "output_tokens", "seconds", "status", "result_json"]
FEEDBACK_COLS = ["submission_id", "created_at", "tester", "role", "item_id", "rating",
                 "verdict", "problem", "comment"]


def now() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def submission_row(sid: str, user_name: str, role: str, consent: bool, step: str, question_id: str,
                   question: str, answer: str, r: dict | None, seconds: float, status: str = "ok") -> dict:
    """r = output of coach() or upgrade() (None on error)."""
    row = {"submission_id": sid, "created_at": now(), "tester": user_name, "role": role,
           "consent": "yes" if consent else "no", "step": step, "question_id": question_id,
           "seconds": round(seconds, 1), "status": status}
    if r:
        m = r.get("meta", {})
        fb = r.get("feedback") or {}
        row.update({"level_cefr": fb.get("level_cefr", r.get("target_level", "")),
                    "n_stuck": len(fb.get("stuck_points", [])) if fb else "",
                    "n_warnings": len(r.get("warnings", [])),
                    "prompt_version": m.get("prompt_version", ""), "model": m.get("model", ""),
                    "llm_calls": m.get("llm_calls", ""), "input_tokens": m.get("input_tokens", ""),
                    "output_tokens": m.get("output_tokens", "")})
    if consent:
        row.update({"question": question, "answer": answer,
                    "result_json": json.dumps(r, ensure_ascii=False, separators=(",", ":")) if r else ""})
    return {c: row.get(c, "") for c in SUBMISSION_COLS}


class SheetStore:
    def __init__(self, service_account_info: dict, sheet_id: str):
        import gspread  # lazy import: local tests/CLI do not need gspread
        self._gspread = gspread
        self.sheet = gspread.service_account_from_dict(dict(service_account_info)).open_by_key(sheet_id)
        self.subs = self._tab("submissions", SUBMISSION_COLS)
        self.fb = self._tab("feedback", FEEDBACK_COLS)

    def _tab(self, title: str, cols: list[str]):
        try:
            ws = self.sheet.worksheet(title)
        except self._gspread.WorksheetNotFound:
            ws = self.sheet.add_worksheet(title=title, rows=1000, cols=len(cols))
            ws.append_row(cols, value_input_option="RAW")
        return ws

    def add_submission(self, row: dict) -> None:
        self.subs.append_row([row.get(c, "") for c in SUBMISSION_COLS], value_input_option="RAW")

    def add_feedback(self, rows: list[dict]) -> None:
        if rows:
            self.fb.append_rows([[r.get(c, "") for c in FEEDBACK_COLS] for r in rows], value_input_option="RAW")

    def usage_today(self, tester: str) -> tuple[int, int]:
        """(answers today by tester, answers today in total) — counts step=coach only, Vietnam time."""
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        col = lambda name: self.subs.col_values(SUBMISSION_COLS.index(name) + 1)[1:]  # noqa: E731
        mine = total = 0
        for d, t, s in zip(col("created_at"), col("tester"), col("step")):
            if d.startswith(today) and s == "coach":
                total += 1
                mine += t == tester
        return mine, total

    def all_records(self) -> tuple[list[dict], list[dict]]:
        return self.subs.get_all_records(), self.fb.get_all_records()
