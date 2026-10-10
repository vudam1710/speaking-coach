"""Main pipeline: code finds the Vietnamese chunks -> 1 LLM call -> schema validation -> code checks."""
import json
from pathlib import Path

from anthropic import Anthropic
from pydantic import ValidationError

from core.checks import advanced_in_simple, bad_quotes, find_vi_chunks, uncovered_chunks, vietnamese_in_ways
from core.llm import MODEL, LLMError, call_tool
from core.schema import Feedback, tool_schema

PROMPT_VERSION = "coach_v1"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / f"{PROMPT_VERSION}.md"
MAX_TOKENS = 4000


def _inline_refs(schema: dict) -> dict:
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(dict(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


def _user_message(question: str, answer: str, chunks: list[str]) -> str:
    listed = "\n".join(f"- {c}" for c in chunks) or "(none — the learner wrote everything in English)"
    return (f"<question>\n{question.strip()}\n</question>\n\n<answer>\n{answer.strip()}\n</answer>\n\n"
            f"<vietnamese_chunks>\n{listed}\n</vietnamese_chunks>")


def coach(question: str, answer: str, client: Anthropic | None = None) -> dict:
    chunks = find_vi_chunks(answer)
    system = PROMPT_PATH.read_text(encoding="utf-8")
    user = _user_message(question, answer, chunks)
    schema = _inline_refs(tool_schema())

    usages, feedback = [], None
    for attempt in range(2):
        data, usage = call_tool(system, user, tool_name="submit_feedback",
                                tool_description="Submit structured expression feedback for this answer.",
                                schema=schema, max_tokens=MAX_TOKENS, client=client)
        usages.append(usage)
        try:
            feedback = Feedback.model_validate(data)
            break
        except ValidationError as e:
            if attempt == 1:
                raise LLMError(f"Output failed schema twice: {e}", json.dumps(data, ensure_ascii=False)) from e
            user += f"\n\n<previous_error>\nYour last answer failed validation:\n{e}\nFix it.\n</previous_error>"

    fb = feedback.model_dump()
    warnings = []
    if missed := uncovered_chunks(chunks, fb):
        warnings.append(f"No lesson for: {missed}")
    if fake := bad_quotes(answer, fb):
        warnings.append(f"Quotes not found in the answer: {fake}")
    if vi := vietnamese_in_ways(fb):
        warnings.append(f"Simple ways still contain Vietnamese: {vi}")
    if adv := advanced_in_simple(fb):
        warnings.append(f"Advanced phrase leaked into simple ways: {adv}")

    return {
        "feedback": fb,
        "detected_chunks": chunks,
        "warnings": warnings,
        "meta": {"prompt_version": PROMPT_VERSION, "model": MODEL, "llm_calls": len(usages),
                 "input_tokens": sum(u["input_tokens"] for u in usages),
                 "output_tokens": sum(u["output_tokens"] for u in usages)},
    }
