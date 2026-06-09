from __future__ import annotations

import argparse

from pyfpa.cli_helpers import _failure, _root, _success
from pyfpa.memory.workspace import workspace_path


def command_correction_record(args: argparse.Namespace) -> int:
    from pyfpa.memory.corrections import Correction, Override, save_correction

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "correction-record",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before recording corrections",
        )
    try:
        override = None
        if args.override_path is not None:
            override = Override(path=args.override_path, value=args.override_value)
        correction = Correction(
            slug=args.slug,
            type=args.type,
            target=args.target,
            status=args.status,
            date=args.date,
            override=override,
            notes=args.notes or "",
        )
        save_correction(correction, workspace / "corrections")
    except Exception as exc:
        return _failure("correction-record", root, "invalid_correction", str(exc))
    return _success(
        "correction-record",
        root,
        {
            "slug": correction.slug,
            "type": correction.type,
            "target": correction.target,
            "status": correction.status,
            "date": correction.date,
            "override": correction.override.model_dump() if correction.override else None,
            "corrections_dir": str(workspace / "corrections"),
        },
    )


def command_correction_list(args: argparse.Namespace) -> int:
    from pyfpa.memory.corrections import load_corrections

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "correction-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing corrections",
        )
    try:
        corrections = load_corrections(workspace / "corrections")
    except Exception as exc:
        return _failure("correction-list", root, "invalid_correction", str(exc))
    filtered = [
        c for c in corrections
        if args.status is None or c.status == args.status
    ]
    return _success(
        "correction-list",
        root,
        {
            "corrections": [
                {"slug": c.slug, "type": c.type, "target": c.target, "status": c.status}
                for c in filtered
            ],
            "correction_count": len(filtered),
            "writes_performed": False,
        },
    )


def command_scorecard_render(args: argparse.Namespace) -> int:
    from pyfpa.backtest.learn import render_scorecard
    from pyfpa.backtest.snapshot import load_snapshot

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "scorecard-render",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before rendering scorecard",
        )
    forecasts_dir = workspace / "forecasts"
    snapshots = []
    parse_errors = []
    if forecasts_dir.is_dir():
        for snap_path in sorted(forecasts_dir.glob("*.yaml")):
            try:
                snapshots.append(load_snapshot(snap_path))
            except Exception as exc:
                parse_errors.append(f"{snap_path.name}: {exc}")
    if parse_errors:
        return _failure(
            "scorecard-render",
            root,
            "invalid_snapshot",
            "; ".join(parse_errors),
        )
    scored = [s for s in snapshots if s.score is not None]
    unscored = [s for s in snapshots if s.score is None]
    scorecard_path = workspace / "scorecard.md"
    try:
        scorecard_path.write_text(render_scorecard(snapshots))
    except Exception as exc:
        return _failure("scorecard-render", root, "render_failed", str(exc))
    return _success(
        "scorecard-render",
        root,
        {
            "scorecard_path": str(scorecard_path),
            "snapshot_count": len(snapshots),
            "scored_count": len(scored),
            "unscored_count": len(unscored),
        },
    )


def command_experiment_list(args: argparse.Namespace) -> int:
    from pyfpa.memory.experiments import load_experiments

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "experiment-list",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before listing experiments",
        )
    try:
        experiments = load_experiments(workspace / "experiments")
    except Exception as exc:
        return _failure("experiment-list", root, "invalid_experiment", str(exc))
    filtered = [
        e for e in experiments
        if args.status is None or e.status == args.status
    ]
    return _success(
        "experiment-list",
        root,
        {
            "experiments": [
                {
                    "slug": e.slug,
                    "status": e.status,
                    "hypothesis": e.hypothesis,
                    "snapshot": e.snapshot,
                    "created": e.created,
                }
                for e in filtered
            ],
            "experiment_count": len(filtered),
            "writes_performed": False,
        },
    )


def command_context_pack(args: argparse.Namespace) -> int:
    from pyfpa.memory.retrieval import build_context_pack, build_memory_index, search_memory

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "context-pack",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before building a context pack",
        )
    try:
        index = build_memory_index(workspace)
        pack = build_context_pack(
            index,
            args.task,
            categories=args.category or None,
            limit=args.limit,
        )
        hits = search_memory(index, args.task, categories=args.category or None, limit=args.limit)
    except Exception as exc:
        return _failure("context-pack", root, "context_pack_failed", str(exc))
    return _success(
        "context-pack",
        root,
        {
            "pack": pack,
            "hit_count": len(hits),
            "entry_count": len(index.entries),
            "writes_performed": False,
        },
    )


def command_onboarding_render(args: argparse.Namespace) -> int:
    from pyfpa.memory.intake import load_intake
    from pyfpa.memory.onboarding import ArchitectureProposal, write_onboarding_outputs

    root = _root(args.path)
    workspace = workspace_path(root)
    if not workspace.is_dir():
        return _failure(
            "onboarding-render",
            root,
            "workspace_not_initialized",
            "initialize the company workspace before rendering onboarding outputs",
        )
    try:
        intake = load_intake(workspace / "intake.md")
        proposal = ArchitectureProposal(
            summary=args.proposal_summary,
            connectors=args.connector or [],
            model_components=args.model_component or [],
            generated_skills=args.generated_skill or [],
            risks=args.risk or [],
            validation_checks=args.validation_check or [],
        )
        profile_path, proposal_path = write_onboarding_outputs(intake, workspace, proposal)
    except Exception as exc:
        return _failure("onboarding-render", root, "onboarding_render_failed", str(exc))
    return _success(
        "onboarding-render",
        root,
        {
            "profile_path": str(profile_path),
            "proposal_path": str(proposal_path),
        },
    )
