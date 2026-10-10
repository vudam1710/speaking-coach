"""Output contract between the LLM and the UI (Pydantic -> JSON schema for tool use).

The learner answers an IELTS Speaking question in English and leaves the parts
they cannot say in Vietnamese ("I had to pay viện phí"). Feedback is ONLY about
expression (not about the quality of ideas):
- stuck_points: one lesson per Vietnamese chunk -> 2-3 simple ways + strategy + the "advanced" word
- english_notes: up to 3 English parts that are unclear / too complex / unnatural
- other_ways: 2 more simple ways to say the learner's main idea (variety)
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CEFR = Literal["A1", "A2", "B1", "B2", "C1", "C2"]

# Teaching strategies (draft, to be reviewed by the teacher after real examples).
Strategy = Literal["noun_to_verb", "general_plus_detail", "cause_effect", "example", "split_sentence", "other"]
STRATEGY_LABELS_VI = {
    "noun_to_verb": "Đổi danh từ khó → động từ dễ",
    "general_plus_detail": "Từ chung + chi tiết",
    "cause_effect": "Nói theo nguyên nhân → kết quả",
    "example": "Đưa ví dụ cụ thể",
    "split_sentence": "Tách thành câu ngắn",
    "other": "Cách khác",
}

# Order = the teacher's success criteria: understood > within level > natural.
NoteType = Literal["unclear", "too_complex", "unnatural"]
NOTE_LABELS_VI = {
    "unclear": "Người nghe dễ hiểu sai",
    "too_complex": "Phức tạp hơn mức cần",
    "unnatural": "Hiểu được, nói tự nhiên hơn thế này",
}

MAX_ENGLISH_NOTES = 3   # a ceiling, not a quota (lesson from writing-coach)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Way(_Strict):
    sentence_en: str = Field(description="A full English sentence, simple words only (within the learner's level)")
    strategy: Strategy
    note_vi: str = Field(description="1 short sentence: how this way thinks about the idea")


class Advanced(_Strict):
    phrase_en: str = Field(description="The 'advanced' word/phrase a native speaker would use, e.g. 'hospital fees'")
    cefr: CEFR
    example_en: str = Field(description="The learner's sentence rewritten with this phrase")


class StuckPoint(_Strict):
    vi_chunk: str = Field(description="Vietnamese text copied EXACTLY from the answer")
    meaning_vi: str = Field(description="What the learner wanted to say, in plain Vietnamese")
    trap_vi: str = Field(description="Why learners get stuck here (e.g. hunting for one exact noun)")
    simple_ways: list[Way] = Field(min_length=2, max_length=3)
    advanced: Advanced


class EnglishNote(_Strict):
    quote_en: str = Field(description="English text copied EXACTLY from the answer")
    type: NoteType
    why_vi: str
    better_en: str = Field(description="One simpler/clearer sentence, still within level")
    strategy: Strategy


class Feedback(_Strict):
    level_cefr: CEFR = Field(description="Estimated level from the English parts of the answer")
    strength_vi: str = Field(description="1 sentence: what the learner already does well when expressing ideas")
    stuck_points: list[StuckPoint]
    english_notes: list[EnglishNote] = Field(max_length=MAX_ENGLISH_NOTES)
    main_idea_vi: str = Field(description="The learner's main idea in 1 Vietnamese sentence")
    other_ways: list[Way] = Field(min_length=2, max_length=2,
                                  description="2 MORE simple ways to say the main idea, using different strategies")
    summary_vi: str = Field(description="1-2 sentences: the one thinking habit to practise next")


def tool_schema() -> dict:
    return Feedback.model_json_schema()


# ---------------------------------------------------------------- step 2: upgrade (+1 level)
# Keep the learner's answer and structure; make only 3-4 changes. Upgrades come from
# naturalness and variety (chunks, linking, sentence structure, extending), NOT rare words.
ChangeType = Literal["natural_chunk", "linking", "structure", "extend"]
CHANGE_LABELS_VI = {
    "natural_chunk": "Cụm từ tự nhiên",
    "linking": "Nối ý mượt hơn",
    "structure": "Đa dạng cấu trúc câu",
    "extend": "Mở rộng ý (lý do / ví dụ)",
}


class Change(_Strict):
    original_en: str = Field(description="A sentence or phrase copied EXACTLY from base_answer_en")
    upgraded_en: str = Field(description="Its replacement at the target level")
    type: ChangeType
    why_vi: str = Field(description="1 short sentence: why this sounds better")


class Upgrade(_Strict):
    base_answer_en: str = Field(description="The learner's answer with Vietnamese parts filled in simply; "
                                            "everything else unchanged")
    changes: list[Change] = Field(min_length=3, max_length=4)
    practice_vi: str = Field(description="A task: say the answer again in your own words using >= 2 of the changes")


def upgrade_schema() -> dict:
    return Upgrade.model_json_schema()
