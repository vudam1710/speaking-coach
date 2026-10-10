"""Run the coach on one or more sample files and write a readable Markdown review.

File format: the IELTS question, a line `---`, then the learner's answer.

    python cli.py                      # all samples, step 1 + step 2 (upgrade)
    python cli.py --no-upgrade         # step 1 only
    python cli.py data/samples/s01_health.txt
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from core.coach import coach
from core.schema import CHANGE_LABELS_VI, NOTE_LABELS_VI, STRATEGY_LABELS_VI
from core.upgrade import apply_changes, upgrade

ROOT = Path(__file__).parent


def to_markdown(name: str, question: str, answer: str, r: dict) -> str:
    fb = r["feedback"]
    s = STRATEGY_LABELS_VI
    out = [f"# {name}", f"**Question:** {question.strip()}", f"**Answer:** {answer.strip()}",
           f"*Detected Vietnamese:* {r['detected_chunks']} · *Level:* {fb['level_cefr']}", "",
           f"👍 {fb['strength_vi']}", ""]
    for i, sp in enumerate(fb["stuck_points"], 1):
        out += [f"## Chỗ bí {i}: «{sp['vi_chunk']}»", f"- Ý em muốn nói: {sp['meaning_vi']}",
                f"- Vì sao hay bí: {sp['trap_vi']}", "- Cách nói đơn giản:"]
        out += [f"  - *{w['sentence_en']}* — [{s[w['strategy']]}] {w['note_vi']}" for w in sp["simple_ways"]]
        a = sp["advanced"]
        out += [f"- ⭐ Từ xịn: **{a['phrase_en']}** ({a['cefr']}) → *{a['example_en']}*", ""]
    if fb["english_notes"]:
        out.append("## Phần tiếng Anh")
        for n in fb["english_notes"]:
            out += [f"- «{n['quote_en']}» — {NOTE_LABELS_VI[n['type']]}: {n['why_vi']}",
                    f"  → *{n['better_en']}* [{s[n['strategy']]}]"]
        out.append("")
    out += ["## Nói ý chính theo cách khác", f"Ý chính: {fb['main_idea_vi']}"]
    out += [f"- *{w['sentence_en']}* — [{s[w['strategy']]}] {w['note_vi']}" for w in fb["other_ways"]]
    out += ["", f"🎯 {fb['summary_vi']}", ""]
    out += [f"⚠️ {w}" for w in r["warnings"]]
    m = r["meta"]
    out += [f"<sub>{m['prompt_version']} · {m['model']} · {m['input_tokens']} in / {m['output_tokens']} out</sub>", ""]
    return "\n".join(out)


def upgrade_markdown(u: dict) -> str:
    up = u["upgrade"]
    bold = [{**c, "upgraded_en": f"**{c['upgraded_en'].strip().rstrip('.')}**"} for c in up["changes"]]
    highlighted, _ = apply_changes(up["base_answer_en"], bold)
    out = [f"## ⬆️ Nâng cấp lên {u['target_level']}", f"*Bản gốc (đã điền chỗ tiếng Việt):* {up['base_answer_en']}", "",
           f"*Bản nâng cấp:* {highlighted}", ""]
    for i, c in enumerate(up["changes"], 1):
        out += [f"{i}. [{CHANGE_LABELS_VI[c['type']]}] «{c['original_en']}» → *{c['upgraded_en']}*", f"   {c['why_vi']}"]
    out += ["", f"🗣️ {up['practice_vi']}", ""]
    out += [f"⚠️ {w}" for w in u["warnings"]]
    m = u["meta"]
    out += [f"<sub>{m['prompt_version']} · {m['input_tokens']} in / {m['output_tokens']} out</sub>", ""]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=Path, nargs="*", help="default: all data/samples/*.txt")
    parser.add_argument("--no-upgrade", action="store_true", help="skip step 2 (upgrade)")
    args = parser.parse_args()
    files = args.files or sorted((ROOT / "data" / "samples").glob("*.txt"))
    out_dir = ROOT / "_scratch" / f"run_{datetime.now():%Y%m%d_%H%M%S}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = []
    for f in files:
        question, answer = f.read_text(encoding="utf-8").split("\n---\n", 1)
        r = coach(question, answer)
        md = to_markdown(f.stem, question, answer, r)
        if not args.no_upgrade:
            r["upgrade"] = upgrade(question, answer, r["feedback"])
            md += "\n" + upgrade_markdown(r["upgrade"])
        (out_dir / f"{f.stem}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        report.append(md)
        print(f"✓ {f.name} · warnings: {len(r['warnings'])}")
    (out_dir / "review.md").write_text("\n---\n\n".join(report), encoding="utf-8")
    print(f"💾 {out_dir / 'review.md'}")


if __name__ == "__main__":
    main()
