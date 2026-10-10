"""Gọi Claude và nhận về JSON ĐÚNG CẤU TRÚC bằng tool use.

Vì sao không để model tự viết JSON dạng text?
→ Chỉ cần 1 dấu " không escape là json.loads() hỏng cả bài (lỗi run v0, sample_01).
Với tool use: ta khai báo schema, ép model "gọi tool" → API trả về dict đã parse sẵn.
"""
import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
# Lưu ý: API/SDK hiện tại (anthropic 1.11) KHÔNG còn tham số temperature → không ép được "hết ngẫu nhiên".
# Thay vào đó: đo độ dao động bằng cách chạy lại cùng bộ bài 2 lần (xem evals/CHANGELOG.md).


class LLMError(Exception):
    """Lỗi khi gọi LLM. `raw` giữ output gốc để debug (run_eval lưu ra file .error.txt)."""

    def __init__(self, message: str, raw: str | None = None):
        super().__init__(message)
        self.raw = raw


def call_tool(system: str, user: str, tool_name: str, tool_description: str, schema: dict,
              max_tokens: int, client: Anthropic | None = None) -> tuple[dict, dict]:
    """Ép model trả lời bằng đúng 1 lần gọi tool `tool_name`. Trả về (data, usage)."""
    client = client or Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        tools=[{"name": tool_name, "description": tool_description, "input_schema": schema}],
        tool_choice={"type": "tool", "name": tool_name},   # bắt buộc dùng tool này
        messages=[{"role": "user", "content": user}],
    )
    raw = json.dumps([b.model_dump() for b in response.content], ensure_ascii=False, indent=2)

    if response.stop_reason == "max_tokens":
        raise LLMError("Output bị cắt giữa chừng (max_tokens) — tăng max_tokens.", raw)
    blocks = [b for b in response.content if b.type == "tool_use" and b.name == tool_name]
    if not blocks:
        raise LLMError(f"Model không gọi tool '{tool_name}'.", raw)

    usage = {"input_tokens": response.usage.input_tokens,
             "output_tokens": response.usage.output_tokens, "model": MODEL}
    return blocks[0].input, usage
