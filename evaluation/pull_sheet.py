"""Pull everything learners were shown from the Google Sheet → review files.

    python evaluation/pull_sheet.py                    # everything
    python evaluation/pull_sheet.py --since 2026-10-15 # only from this date

Reads .streamlit/secrets.toml (SHEET_ID + [gcp_service_account]).
Output evaluation/results/live-<YYYYMMDD-HHMM>/
    summary.csv            1 row / answer, numbers only (no text)                           → commit
    raw/<set_id>.md        1 file / topic set: the page exactly as the learner saw it         → gitignored
    raw/review_items.csv   1 row / thing shown to the learner, word for word
                           + in-app ratings of each reviewer (<name>_verdict / _problem / _comment)
                           + empty verdict / problem / comment / should_be for you             → gitignored
Learners do not rate anything — only the teacher reviews.
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.storage import SheetStore  # noqa: E402
from core.summary import set_summary  # noqa: E402
from evaluation.common import SUMMARY_COLUMNS, summary_row, write_csv  # noqa: E402
from evaluation.render import ITEM_COLUMNS, render_markdown, render_set_markdown, review_items  # noqa: E402

REVIEW_FIELDS = ["verdict", "problem", "comment"]


def load_secrets() -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:          # Python < 3.11
        import tomli as tomllib
    return tomllib.loads((ROOT / ".streamlit" / "secrets.toml").read_text(encoding="utf-8"))


def latest(rows: list[dict], key) -> dict:
    """Keep the last row per key (sorted by created_at)."""
    out = {}
    for r in sorted(rows, key=lambda r: str(r["created_at"])):
        out[key(r)] = r
    return out


def agreement(fb: dict) -> tuple[int, int]:
    by_item = defaultdict(dict)
    for (sid, item, tester), f in fb.items():
        if f["role"] == "reviewer" and f["verdict"]:
            by_item[(sid, item)][tester] = f["verdict"]
    same = total = 0
    for votes in by_item.values():
        for a, b in combinations(votes.values(), 2):
            total += 1
            same += a == b
    return same, total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="", help="only answers from this date (YYYY-MM-DD)")
    args = ap.parse_args()

    sec = load_secrets()
    subs, feedback = SheetStore(sec["gcp_service_account"], sec["SHEET_ID"]).all_records()
    subs = [s for s in subs if str(s["created_at"]) >= args.since]
    step = lambda name: latest([s for s in subs if s["step"] == name], lambda s: str(s["submission_id"]))  # noqa: E731
    coach_rows, upgrades, retells = step("coach"), step("upgrade"), step("practice")
    fb = latest(feedback, lambda f: (str(f["submission_id"]), str(f["item_id"]), f["tester"]))
    reviewers = sorted({t for (_, _, t), f in fb.items() if f["role"] == "reviewer"})

    out = ROOT / "evaluation" / "results" / f"live-{datetime.now():%Y%m%d-%H%M}"
    raw = out / "raw"
    raw.mkdir(parents=True)

    items, summaries = [], []
    sets = defaultdict(list)
    for aid, s in coach_rows.items():
        meta = {"question_id": s["question_id"], "tester": s["tester"], "seconds": s["seconds"]}
        if not s.get("result_json"):            # error (or saved before storage was always-on)
            summaries.append({"tag": "live", "set_id": s["set_id"], "answer_id": aid, "status": s["status"],
                              "prompt_version": s["prompt_version"], **meta})
            continue
        r = json.loads(s["result_json"])
        u = upgrades.get(aid)
        up = json.loads(u["result_json"]) if u and u.get("result_json") else None
        retell = str(retells[aid]["answer"]) if aid in retells else ""
        sets[str(s["set_id"])].append((s, r, render_markdown(aid, s["question"], s["answer"], r, up, retell)))
        row = summary_row("live", s["set_id"], aid, r, up, **meta)
        row["retold"] = "yes" if retell else ""
        summaries.append(row)
        for it in review_items("live", s["set_id"], aid, s["question"], r, up, answer=s["answer"], retell=retell):
            it["tester"] = s["tester"]
            for name in reviewers:
                f = fb.get((aid, it["item_id"], name), {})
                it.update({f"{name}_{c}": f.get(c, "") for c in REVIEW_FIELDS})
            items.append(it)

    for set_id, answers in sets.items():
        first = answers[0][0]
        header = (f"# {first['question_id'].rsplit('_', 1)[0]} · {first['tester']} · {first['created_at']}  \n"
                  f"<sub>set_id {set_id}</sub>")
        md = render_set_markdown(header, set_summary([r["feedback"] for _, r, _ in answers]), [m for _, _, m in answers])
        general = [f["comment"] for (fs, fi, _), f in fb.items() if fs == set_id and fi == "GENERAL" and f["comment"]]
        if general:
            md += "\n---\n**Góp ý chung của reviewer:** " + " | ".join(general) + "\n"
        (raw / f"{set_id}.md").write_text(md, encoding="utf-8")

    cols = (ITEM_COLUMNS[:-4] + ["tester"] + [f"{n}_{c}" for n in reviewers for c in REVIEW_FIELDS]
            + ITEM_COLUMNS[-4:])
    write_csv(raw / "review_items.csv", cols, items)
    write_csv(out / "summary.csv", SUMMARY_COLUMNS, summaries)

    same, total = agreement(fb)
    print(f"✅ {len(sets)} sets · {len(coach_rows)} answers · {len(items)} items · {len(upgrades)} upgrades · "
          f"{len(retells)} retells → {out.relative_to(ROOT)}")
    print(f"   Reviewers who rated in the app: {', '.join(reviewers) or '(none yet)'}")
    if total:
        print(f"   Reviewer agreement: {same}/{total} pairs with the same verdict ({same / total:.0%})")
    print("   Review order: S* (stuck points) → X* (missed by tool) → U*/UP (upgrade) → the rest")


if __name__ == "__main__":
    main()
