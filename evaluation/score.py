"""Score a coded review_items.csv (after you filled the verdict column).

    python evaluation/score.py evaluation/results/v1/raw/review_items.csv

Prints ✓ / ~ / ✗ by item kind and the most common problems → copy into EXPERIMENTS.md.
Rows without a verdict are ignored (count shown).
"""
import csv
import sys
from collections import Counter, defaultdict

GROUPS = {"S": "Chỗ bí — phần giải thích (S)", "S.w": "Chỗ bí — cách nói đơn giản (S.w)",
          "S.adv": "Chỗ bí — từ xịn (S.adv)", "E": "Phần tiếng Anh (E)", "O": "Ý chính (O)",
          "O.w": "Cách nói khác (O.w)", "SUM": "Khen / thói quen (SUM)", "L": "Trình độ (L)",
          "UP": "Nâng cấp — cả bài (UP)", "UP.task": "Nhiệm vụ nói lại", "U": "Nâng cấp — chỗ đổi (U)",
          "X": "Code bắt, tool bỏ sót (X)", "M": "Tool bỏ sót (M)", "ANSWER": "Câu trả lời", "RETELL": "Học sinh nói lại"}


def group(item_id: str) -> str:
    """S2.w3 → S.w · S1 → S · SUM.habit → SUM · U4 → U · UP.task → UP.task"""
    head, _, tail = item_id.partition(".")
    letters = head.rstrip("0123456789")
    if letters in ("SUM",):
        return "SUM"
    if tail and letters in ("S", "O"):
        return f"{letters}.{tail.rstrip('0123456789')}"
    return f"{letters}.{tail}" if tail else letters


def main(path: str) -> None:
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    coded = [r for r in rows if r["verdict"].strip()]
    by = defaultdict(Counter)
    problems = Counter()
    for r in coded:
        by[group(r["item_id"])][r["verdict"].strip()] += 1
        if r["problem"].strip():
            problems[r["problem"].strip()] += 1
    print(f"{len(coded)}/{len(rows)} items coded\n")
    print("| Nhóm | ✓ | ~ | ✗ | ✓ % |\n|---|---|---|---|---|")
    total = Counter()
    for g, c in by.items():
        n = sum(c.values())
        total += c
        print(f"| {GROUPS.get(g, g)} | {c['✓']} | {c['~']} | {c['✗']} | {c['✓'] / n:.0%} ({c['✓']}/{n}) |")
    n = sum(total.values())
    if n:
        print(f"| **Tổng** | {total['✓']} | {total['~']} | {total['✗']} | **{total['✓'] / n:.0%}** ({total['✓']}/{n}) |")
    if problems:
        print("\nProblems: " + " · ".join(f"{p} {k}" for p, k in problems.most_common()))


if __name__ == "__main__":
    main(sys.argv[1])
