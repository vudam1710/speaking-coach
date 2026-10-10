"""Offline eval round: run step 1 + step 2 on a fixed set of answers, write files to review.

    python evaluation/run_eval.py --tag v1                    # data/samples/*.txt
    python evaluation/run_eval.py --tag v2 --dir data/gold    # real learner answers (gitignored)

File format: question, a line `---`, then the answer.
Output evaluation/results/<tag>/
    summary.csv            1 row / answer, numbers only (no answer text)      → commit
    raw/<id>.md / .json    readable feedback + full output                    → gitignored
    raw/review_items.csv   1 row / feedback item + empty verdict/problem/comment/should_be → you fill in
Then: python evaluation/score.py evaluation/results/<tag>/raw/review_items.csv
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.coach import coach  # noqa: E402
from core.upgrade import upgrade  # noqa: E402
from evaluation.common import SUMMARY_COLUMNS, summary_row, write_csv  # noqa: E402
from evaluation.render import ITEM_COLUMNS, render_markdown, review_items  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="round name, e.g. v1 (one change per round)")
    ap.add_argument("--dir", default="data/samples")
    ap.add_argument("--no-upgrade", action="store_true")
    args = ap.parse_args()

    out = ROOT / "evaluation" / "results" / args.tag
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    items, summaries = [], []
    for f in sorted((ROOT / args.dir).glob("*.txt")):
        question, answer = f.read_text(encoding="utf-8").split("\n---\n", 1)
        try:
            r = coach(question, answer)
            up = None if args.no_upgrade else upgrade(question, answer, r["feedback"])
        except Exception as e:
            print(f"✗ {f.name}: {e}")
            summaries.append(summary_row(args.tag, f.parent.name, f.stem, None))
            continue
        (raw / f"{f.stem}.json").write_text(json.dumps({"coach": r, "upgrade": up}, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
        (raw / f"{f.stem}.md").write_text(render_markdown(f.stem, question, answer, r, up), encoding="utf-8")
        items += review_items(args.tag, f.parent.name, f.stem, question.strip(), r, up, answer=answer.strip())
        summaries.append(summary_row(args.tag, f.parent.name, f.stem, r, up))
        print(f"✓ {f.name} · warnings {len(r['warnings']) + len(up['warnings'] if up else [])}")
    write_csv(raw / "review_items.csv", ITEM_COLUMNS, items)
    write_csv(out / "summary.csv", SUMMARY_COLUMNS, summaries)
    print(f"💾 {out.relative_to(ROOT)} · {len(items)} items to review → raw/review_items.csv")


if __name__ == "__main__":
    main()
