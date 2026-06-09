import pytest

from pyfpa.memory.intake import (
    Intake,
    intake_ready,
    load_intake,
    next_intake_questions,
    record_intake_fact,
    save_intake,
)


def _record_required(intake: Intake) -> Intake:
    while questions := next_intake_questions(intake):
        for question in questions:
            intake = record_intake_fact(
                intake,
                key=question.key,
                answer=f"Answer for {question.key}",
                source_type="user",
            )
    return intake


def test_intake_round_trip_preserves_frontmatter_and_notes(tmp_path):
    intake = Intake(business_name="Acme", notes="## Interview Notes\n\nKeep this readable.")
    intake = record_intake_fact(
        intake,
        key="business_model",
        answer="Commercial coffee roasting",
        source_type="user",
        sources=["intake call"],
    )
    path = tmp_path / "intake.md"

    save_intake(intake, path)

    assert load_intake(path) == intake
    assert path.read_text().startswith("---\n")


def test_direct_answers_are_confirmed_immediately():
    intake = record_intake_fact(
        Intake(),
        key="financing",
        answer="A $500K revolving line",
        source_type="user",
    )

    fact = intake.facts[0]
    assert fact.status == "confirmed"
    assert fact.confidence == 1.0
    assert fact.source_type == "user"


def test_high_confidence_evidence_suppresses_redundant_question():
    intake = record_intake_fact(
        Intake(),
        key="business_model",
        answer="Premium furniture manufacturing",
        source_type="local_file",
        sources=["README.md"],
        confidence=0.9,
    )

    questions = next_intake_questions(intake)

    assert all(question.key != "business_model" for question in questions)
    assert {question.topic for question in questions} == {"business"}


def test_low_confidence_and_conflict_are_prioritized_for_confirmation():
    intake = record_intake_fact(
        Intake(),
        key="business_model",
        answer="Wholesale distributor",
        source_type="inference",
        confidence=0.4,
    )
    questions = next_intake_questions(intake)
    assert questions[0].key == "business_model"
    assert questions[0].reason == "confirm"

    intake = record_intake_fact(
        intake,
        key="business_model",
        answer="Direct-to-consumer manufacturer",
        source_type="local_file",
        sources=["website-export.md"],
        confidence=0.8,
    )
    questions = next_intake_questions(intake)
    assert questions[0].key == "business_model"
    assert questions[0].reason == "conflict"


def test_user_answer_resolves_inferred_conflict():
    intake = record_intake_fact(
        Intake(),
        key="business_model",
        answer="Wholesale distributor",
        source_type="local_file",
        sources=["website-export.md"],
    )
    intake = record_intake_fact(
        intake,
        key="business_model",
        answer="Direct-to-consumer manufacturer",
        source_type="local_file",
    )
    intake = record_intake_fact(
        intake,
        key="business_model",
        answer="Both wholesale and direct-to-consumer",
        source_type="user",
    )

    fact = intake.facts[0]
    assert fact.status == "confirmed"
    assert fact.answer == "Both wholesale and direct-to-consumer"
    assert fact.alternatives == []
    assert fact.sources == ["website-export.md"]


def test_question_round_is_related_and_limited():
    questions = next_intake_questions(Intake(), limit=3)

    assert len(questions) == 3
    assert {question.topic for question in questions} == {"business"}


def test_intake_readiness_requires_all_critical_topics():
    intake = Intake()
    assert intake_ready(intake) is False

    intake = _record_required(intake)

    assert intake_ready(intake) is True
    assert next_intake_questions(intake) == []


def test_question_limit_must_be_positive():
    with pytest.raises(ValueError, match="at least 1"):
        next_intake_questions(Intake(), limit=0)
