"""ui/dashboard.compute_stats — no Streamlit / Google Sheet needed."""
from core.storage import submission_row
from tests.test_render import R, UP
from ui.dashboard import compute_stats

META = {**R, "meta": {"prompt_version": "coach_v1", "model": "m", "llm_calls": 1, "input_tokens": 1000,
                      "output_tokens": 1000, "cache_read_tokens": 2000}}


def _subs():
    row = lambda sid, set_id, user, step, qid, r, status="ok": submission_row(  # noqa: E731
        sid, set_id, user, "student", True, step, qid, "Q?", "I pay viện phí.", r, 10, status=status)
    up = {**UP, "meta": {"input_tokens": 500, "output_tokens": 500, "cache_read_tokens": 0}}
    return [row("a-1", "a", "minh", "coach", "p1_tiredness_1", META),
            row("a-2", "a", "minh", "coach", "p1_tiredness_2", META),
            row("a-1", "a", "minh", "upgrade", "p1_tiredness_1", up),
            row("a-1", "a", "minh", "practice", "p1_tiredness_1", None),
            row("b-1", "b", "lan", "coach", "p3_money_1", META, status="ok (cached)"),
            row("b-2", "b", "lan", "coach", "p3_money_2", None, status="error: boom")]


def test_empty():
    assert compute_stats([], [])["n_answers"] == 0


def test_counts_cost_and_learning_signals():
    d = compute_stats(_subs(), [])
    assert (d["n_answers"], d["n_sets"], d["n_users"], d["n_errors"], d["n_reused"]) == (4, 2, 2, 1, 1)
    assert d["upgrade_rate"] == 1 / 3 and d["retell_rate"] == 1.0
    assert d["top_chunks"]["viện phí"] == 3                      # 3 answers with a stored result
    assert dict(d["per_part"]) == {"Part 1": 2, "Part 3": 2}
    # cost: 2 real coach calls + 1 upgrade; the reused answer ("ok (cached)") costs nothing
    expected = (2 * (1000 * 3 + 2000 * 0.3 + 1000 * 15) + (500 * 3 + 500 * 15)) / 1e6
    assert abs(d["cost_usd"] - expected) < 1e-9
    u = d["per_user"].set_index("Người dùng")
    assert u.loc["minh", "Câu"] == 2 and u.loc["minh", "Nâng cấp"] == 1 and u.loc["minh", "Nói lại"] == 1


def test_reviewer_verdicts_grouped_like_score_py():
    fb = [{"submission_id": "a-1", "created_at": "2026-10-10 10:00:00", "tester": "co", "role": "reviewer",
           "item_id": i, "rating": "", "verdict": v, "problem": p, "comment": ""}
          for i, v, p in [("S1", "✓", ""), ("U1", "✗", "too_hard"), ("U2", "✓", "")]]
    d = compute_stats(_subs(), fb)
    assert d["reviewer"].loc["Nâng cấp — chỗ đổi (U)", "Tỉ lệ ✓"] == 0.5
    assert d["problems"]["too_hard"] == 1
