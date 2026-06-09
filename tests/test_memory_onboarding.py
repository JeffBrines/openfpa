import pytest

from pyfpa.memory.intake import Intake, next_intake_questions, record_intake_fact
from pyfpa.memory.onboarding import (
    ArchitectureProposal,
    render_architecture_proposal,
    render_business_profile,
    write_onboarding_outputs,
)


def _ready_intake() -> Intake:
    intake = Intake(business_name="Acme")
    while questions := next_intake_questions(intake):
        for question in questions:
            intake = record_intake_fact(
                intake,
                key=question.key,
                answer=f"Known {question.key}",
                source_type="user",
                sources=["CFO interview"],
            )
    return intake


def _proposal() -> ArchitectureProposal:
    return ArchitectureProposal(
        summary="Build a driver-based monthly forecast and direct cash model.",
        connectors=["QuickBooks P&L and balance sheet export"],
        model_components=["Channel revenue model", "13-week cash model"],
        generated_skills=["wholesale-collections"],
        risks=["Collections timing is operationally managed outside the GL."],
        validation_checks=["Reconcile imported totals", "Backtest ending cash"],
    )


def test_render_business_profile_includes_sources_and_confidence():
    profile = render_business_profile(_ready_intake())

    assert "# Acme Business Profile" in profile
    assert "confidence: 100%" in profile
    assert "source: CFO interview" in profile


def test_architecture_proposal_is_an_explicit_human_gate():
    proposal = render_architecture_proposal(_ready_intake(), _proposal())

    assert "Human approval required before scaffolding" in proposal
    assert "## Proposed Connectors" in proposal
    assert "QuickBooks P&L and balance sheet export" in proposal
    assert "- [ ] Approved to scaffold" in proposal


def test_write_onboarding_outputs_requires_ready_intake(tmp_path):
    with pytest.raises(ValueError, match="not ready"):
        write_onboarding_outputs(Intake(), tmp_path, _proposal())


def test_write_onboarding_outputs_creates_profile_and_decision(tmp_path):
    profile, proposal = write_onboarding_outputs(
        _ready_intake(),
        tmp_path,
        _proposal(),
    )

    assert profile == tmp_path / "business-profile.md"
    assert proposal == tmp_path / "decisions" / "initial-model-architecture.md"
    assert profile.exists()
    assert proposal.exists()
