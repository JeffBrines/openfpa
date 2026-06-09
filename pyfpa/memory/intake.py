from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


FactStatus = Literal["confirmed", "inferred", "conflict"]
FactSource = Literal["user", "local_file", "external", "inference"]
QuestionReason = Literal["missing", "confirm", "conflict"]

_KNOWN_CONFIDENCE = 0.7


class IntakeFact(BaseModel):
    key: str
    topic: str
    question: str
    answer: str
    status: FactStatus
    confidence: float = Field(ge=0, le=1)
    source_type: FactSource
    sources: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)


class IntakeQuestion(BaseModel):
    key: str
    topic: str
    prompt: str
    reason: QuestionReason
    current_answer: str = ""


class Intake(BaseModel):
    schema_version: int = 1
    business_name: str = "Company"
    facts: list[IntakeFact] = Field(default_factory=list)
    notes: str = ""


_QUESTION_BANK = (
    IntakeQuestion(
        key="business_model",
        topic="business",
        prompt="What does the company sell, and who are the primary customers?",
        reason="missing",
    ),
    IntakeQuestion(
        key="revenue_model",
        topic="business",
        prompt="How is revenue earned and billed, including pricing and payment terms?",
        reason="missing",
    ),
    IntakeQuestion(
        key="customer_channels",
        topic="business",
        prompt="Which channels, products, or segments should the model distinguish?",
        reason="missing",
    ),
    IntakeQuestion(
        key="collections",
        topic="cash_cycle",
        prompt="When do customers usually pay, and what causes collections to vary?",
        reason="missing",
    ),
    IntakeQuestion(
        key="supplier_payments",
        topic="cash_cycle",
        prompt="When are suppliers, payroll, inventory, and other major obligations paid?",
        reason="missing",
    ),
    IntakeQuestion(
        key="seasonality",
        topic="cash_cycle",
        prompt="What is seasonal or lumpy across revenue, costs, inventory, and cash?",
        reason="missing",
    ),
    IntakeQuestion(
        key="entities",
        topic="finance_structure",
        prompt="Which legal entities, currencies, and intercompany relationships matter?",
        reason="missing",
    ),
    IntakeQuestion(
        key="financing",
        topic="finance_structure",
        prompt="What debt, credit lines, covenants, or other financing is in place?",
        reason="missing",
    ),
    IntakeQuestion(
        key="data_sources",
        topic="finance_structure",
        prompt="Which systems and files contain the financial and operating actuals?",
        reason="missing",
    ),
    IntakeQuestion(
        key="planning_cadence",
        topic="planning",
        prompt="How often do you close, reforecast, report, and make planning decisions?",
        reason="missing",
    ),
    IntakeQuestion(
        key="cfo_priorities",
        topic="planning",
        prompt="Which decisions, risks, or questions matter most to the CFO right now?",
        reason="missing",
    ),
)

_QUESTIONS_BY_KEY = {question.key: question for question in _QUESTION_BANK}
_REQUIRED_KEYS = frozenset(_QUESTIONS_BY_KEY)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        _, frontmatter, body = text.split("---", 2)
        return yaml.safe_load(frontmatter) or {}, body.strip()
    return {}, text.strip()


def save_intake(intake: Intake, path: str | Path) -> None:
    """Save intake as YAML frontmatter plus human-readable markdown notes."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = intake.model_dump()
    notes = data.pop("notes", "")
    text = "---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n"
    if notes:
        text += notes.rstrip() + "\n"
    path.write_text(text)


def load_intake(path: str | Path) -> Intake:
    """Load and validate an intake markdown file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"intake not found: {path}")
    frontmatter, notes = _split_frontmatter(path.read_text())
    return Intake.model_validate({**frontmatter, "notes": notes})


def _fact_by_key(intake: Intake) -> dict[str, IntakeFact]:
    return {fact.key: fact for fact in intake.facts}


def record_intake_fact(
    intake: Intake,
    *,
    key: str,
    answer: str,
    source_type: FactSource,
    sources: list[str] | None = None,
    confidence: float | None = None,
    topic: str | None = None,
    question: str | None = None,
) -> Intake:
    """Return a new intake with one fact recorded under progressive authority.

    Direct user answers are confirmed immediately. Matching evidence strengthens
    an existing fact. Conflicting non-user evidence is retained for confirmation.
    """
    answer = answer.strip()
    if not answer:
        raise ValueError("intake answer must not be empty")
    template = _QUESTIONS_BY_KEY.get(key)
    resolved_topic = topic or (template.topic if template else "other")
    resolved_question = question or (template.prompt if template else key)
    resolved_sources = list(dict.fromkeys(sources or []))
    resolved_confidence = confidence
    if resolved_confidence is None:
        resolved_confidence = 1.0 if source_type == "user" else 0.8

    existing = _fact_by_key(intake).get(key)
    if source_type == "user":
        prior_sources = existing.sources if existing is not None else []
        updated = IntakeFact(
            key=key,
            topic=resolved_topic,
            question=resolved_question,
            answer=answer,
            status="confirmed",
            confidence=1.0,
            source_type="user",
            sources=list(dict.fromkeys([*prior_sources, *resolved_sources])),
        )
    elif existing is not None and existing.answer.casefold() != answer.casefold():
        alternatives = list(dict.fromkeys([*existing.alternatives, answer]))
        updated = existing.model_copy(
            update={
                "status": "conflict",
                "confidence": min(existing.confidence, resolved_confidence),
                "sources": list(dict.fromkeys([*existing.sources, *resolved_sources])),
                "alternatives": alternatives,
            }
        )
    elif existing is not None:
        updated = existing.model_copy(
            update={
                "confidence": max(existing.confidence, resolved_confidence),
                "sources": list(dict.fromkeys([*existing.sources, *resolved_sources])),
            }
        )
    else:
        updated = IntakeFact(
            key=key,
            topic=resolved_topic,
            question=resolved_question,
            answer=answer,
            status="inferred",
            confidence=resolved_confidence,
            source_type=source_type,
            sources=resolved_sources,
        )

    facts = [fact for fact in intake.facts if fact.key != key]
    facts.append(updated)
    return intake.model_copy(update={"facts": facts})


def _known(fact: IntakeFact | None) -> bool:
    return bool(
        fact
        and fact.status != "conflict"
        and (fact.status == "confirmed" or fact.confidence >= _KNOWN_CONFIDENCE)
    )


def intake_ready(intake: Intake) -> bool:
    """Return whether all architecture-critical intake topics are known."""
    facts = _fact_by_key(intake)
    return all(_known(facts.get(key)) for key in _REQUIRED_KEYS)


def next_intake_questions(intake: Intake, *, limit: int = 3) -> list[IntakeQuestion]:
    """Return up to `limit` related unresolved questions for the next round."""
    if limit < 1:
        raise ValueError("question limit must be at least 1")
    facts = _fact_by_key(intake)
    pending: list[IntakeQuestion] = []
    for template in _QUESTION_BANK:
        fact = facts.get(template.key)
        if fact is None:
            pending.append(template)
        elif fact.status == "conflict":
            pending.append(template.model_copy(update={
                "prompt": (
                    f"I found conflicting answers for this: {fact.answer!r} and "
                    f"{', '.join(repr(value) for value in fact.alternatives)}. "
                    "Which is correct?"
                ),
                "reason": "conflict",
                "current_answer": fact.answer,
            }))
        elif fact.status == "inferred" and fact.confidence < _KNOWN_CONFIDENCE:
            pending.append(template.model_copy(update={
                "prompt": f"I inferred {fact.answer!r}. Is that accurate?",
                "reason": "confirm",
                "current_answer": fact.answer,
            }))

    if not pending:
        return []
    topic = pending[0].topic
    return [question for question in pending if question.topic == topic][:limit]
