"""Step 2 (button "Nâng cấp câu trả lời"): +1 level, 3-4 changes, learner's structure kept.

The LLM chooses WHAT to change; code builds the upgraded answer by applying the
replacements to the base answer, so nothing else can change silently.
"""
import json
import re
from pathlib import Path

from anthropic import Anthropic
from pydantic import ValidationError

from core.checks import has_vietnamese
from core.coach import _inline_refs
from core.llm import MODEL, LLMError, call_tool
from core.schema import Upgrade, upgrade_schema

PROMPT_VERSION = "upgrade_v1"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / f"{PROMPT_VERSION}.md"
MAX_TOKENS = 3000
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def next_level(cefr: str) -> str:
    i = CEFR_ORDER.index(cefr)
    return CEFR_ORDER[min(i + 1, len(CEFR_ORDER) - 1)]


def _find(text: str, phrase: str) -> tuple[int, int] | None:
    """Locate phrase in text, tolerant to whitespace and a trailing full stop."""
    p = re.escape(phrase.strip().rstrip(".")).replace(r"\ ", r"\s+")
    m = re.search(p, text, re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def apply_changes(base: str, changes: list[dict]) -> tuple[str, list[str]]:
    """Return (upgraded answer, originals that could not be found)."""
    spans, missing = [], []
    for c in changes:
        span = _find(base, c["original_en"])
        if span is None:
            missing.append(c["original_en"])
        else:
            spans.append((span, c["upgraded_en"].strip().rstrip(".")))
    out, last = [], 0
    for (start, end), new in sorted(spans):
        if start < last:            # overlapping change -> skip it
            missing.append(base[start:end])
            continue
        out += [base[last:start], new]
        last = end
    out.append(base[last:])
    return "".join(out), missing


def upgrade(question: str, answer: str, coach_feedback: dict, client: Anthropic | None = None) -> dict:
    target = next_level(coach_feedback["level_cefr"])
    simple = [{"vi": sp["vi_chunk"], "simple_ways": [w["sentence_en"] for w in sp["simple_ways"]]}
              for sp in coach_feedback["stuck_points"]]
    user = (f"<question>\n{question.strip()}\n</question>\n\n<answer>\n{answer.strip()}\n</answer>\n\n"
            f"<earlier_feedback>\n{json.dumps(simple, ensure_ascii=False, indent=1)}\n</earlier_feedback>\n\n"
            f"<learner_level>{coach_feedback['level_cefr']}</learner_level>\n<target_level>{target}</target_level>")
    system = PROMPT_PATH.read_text(encoding="utf-8")
    schema = _inline_refs(upgrade_schema())

    usages, up = [], None
    for attempt in range(2):
        data, usage = call_tool(system, user, tool_name="submit_upgrade",
                                tool_description="Submit the upgraded answer.",
                                schema=schema, max_tokens=MAX_TOKENS, client=client)
        usages.append(usage)
        try:
            up = Upgrade.model_validate(data)
            break
        except ValidationError as e:
            if attempt == 1:
                raise LLMError(f"Upgrade failed schema twice: {e}", json.dumps(data, ensure_ascii=False)) from e
            user += f"\n\n<previous_error>\nYour last answer failed validation:\n{e}\nFix it.\n</previous_error>"

    u = up.model_dump()
    upgraded, missing = apply_changes(u["base_answer_en"], u["changes"])
    warnings = []
    if missing:
        warnings.append(f"Changes not found in base answer (skipped): {missing}")
    if has_vietnamese(u["base_answer_en"]) or has_vietnamese(upgraded):
        warnings.append("Vietnamese left in the upgraded answer")
    if len(upgraded.split()) > 1.7 * len(u["base_answer_en"].split()):
        warnings.append("Upgraded answer is much longer than the original (>1.7x words)")

    return {
        "upgrade": u,
        "upgraded_answer_en": upgraded,
        "target_level": target,
        "warnings": warnings,
        "meta": {"prompt_version": PROMPT_VERSION, "model": MODEL, "llm_calls": len(usages),
                 "input_tokens": sum(x["input_tokens"] for x in usages),
                 "output_tokens": sum(x["output_tokens"] for x in usages)},
    }
