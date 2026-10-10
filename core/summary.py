"""Set-level summary shown to the learner — computed by code, no LLM call."""
from collections import Counter

from core.schema import STRATEGY_LABELS_VI


def set_summary(feedbacks: list[dict]) -> dict:
    stuck = [sp for fb in feedbacks for sp in fb["stuck_points"]]
    strategies = Counter(w["strategy"] for sp in stuck for w in sp["simple_ways"])
    levels = Counter(fb["level_cefr"] for fb in feedbacks)
    out = {"n_answers": len(feedbacks), "n_stuck": len(stuck), "chunks": [sp["vi_chunk"] for sp in stuck],
           "level": levels.most_common(1)[0][0] if levels else "—", "top_strategy_vi": "", "top_strategy_text": ""}
    if stuck:
        top, n = strategies.most_common(1)[0]
        out["top_strategy_vi"] = STRATEGY_LABELS_VI[top]
        out["top_strategy_text"] = (f"Cách gỡ dùng nhiều nhất: {STRATEGY_LABELS_VI[top]} ({n}/{sum(strategies.values())} "
                                    "cách nói gợi ý). Lần sau bí từ, thử nghĩ theo hướng này trước.")
    return out
