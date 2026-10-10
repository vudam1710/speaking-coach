"""Small shared helpers for evaluation scripts."""
import csv
from pathlib import Path

SUMMARY_COLUMNS = ["tag", "set_id", "answer_id", "question_id", "tester", "status", "prompt_version", "level",
                   "n_detected", "n_stuck", "n_english_notes", "n_warnings", "upgraded", "n_changes",
                   "retold", "input_tokens", "cache_read_tokens", "output_tokens", "seconds"]


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:   # BOM → Excel reads Vietnamese correctly
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summary_row(tag: str, set_id: str, answer_id: str, r: dict | None, up: dict | None = None, **extra) -> dict:
    row = {"tag": tag, "set_id": set_id, "answer_id": answer_id, "status": "ok" if r else "error", **extra}
    if r:
        fb, m = r["feedback"], r["meta"]
        row.update({"prompt_version": m["prompt_version"], "level": fb["level_cefr"],
                    "n_detected": len(r.get("detected_chunks", [])), "n_stuck": len(fb["stuck_points"]),
                    "n_english_notes": len(fb["english_notes"]), "n_warnings": len(r.get("warnings", [])),
                    "input_tokens": m["input_tokens"], "cache_read_tokens": m.get("cache_read_tokens", ""),
                    "output_tokens": m["output_tokens"]})
    if up:
        row.update({"upgraded": "yes", "n_changes": len(up["upgrade"]["changes"]),
                    "n_warnings": row.get("n_warnings", 0) + len(up.get("warnings", []))})
    return row
