from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from pyfpa.research.epochs import ResearchEpoch


class ModelVersion(BaseModel):
    model_id: str
    created: str
    artifact: str
    source_epoch: str | None = None
    description: str = ""


class PromotionRecord(BaseModel):
    from_model: str
    to_model: str
    epoch_id: str
    approved_by: str
    approved_at: str
    notes: str = ""


class ModelRegistry(BaseModel):
    schema_version: int = 1
    champion: ModelVersion | None = None
    challengers: list[ModelVersion] = Field(default_factory=list)
    retired: list[ModelVersion] = Field(default_factory=list)
    promotions: list[PromotionRecord] = Field(default_factory=list)


def save_model_registry(registry: ModelRegistry, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry.model_dump(), sort_keys=False))


def load_model_registry(path: str | Path) -> ModelRegistry:
    path = Path(path)
    if not path.exists():
        return ModelRegistry()
    return ModelRegistry.model_validate(yaml.safe_load(path.read_text()))


def register_challenger(
    registry: ModelRegistry,
    challenger: ModelVersion,
) -> ModelRegistry:
    """Return a new registry with a uniquely named challenger."""
    ids = {
        version.model_id
        for version in [
            *registry.challengers,
            *registry.retired,
            *([registry.champion] if registry.champion else []),
        ]
    }
    if challenger.model_id in ids:
        raise ValueError(f"model id already registered: {challenger.model_id}")
    return registry.model_copy(
        update={"challengers": [*registry.challengers, challenger]}
    )


def promote_challenger(
    registry: ModelRegistry,
    *,
    challenger_id: str,
    epoch: ResearchEpoch,
    approved_by: str,
    approved_at: str,
    notes: str = "",
) -> ModelRegistry:
    """Promote a challenger only with an explicit human approval record."""
    if not approved_by.strip():
        raise ValueError("promotion requires approved_by")
    if epoch.status != "proposed" or not epoch.evaluation.promotion_eligible:
        raise ValueError("promotion requires a proposed, promotion-eligible epoch")
    challenger = next(
        (item for item in registry.challengers if item.model_id == challenger_id),
        None,
    )
    if challenger is None:
        raise ValueError(f"challenger not found: {challenger_id}")
    if epoch.challenger_id != challenger_id:
        raise ValueError("epoch challenger does not match registry challenger")
    if challenger.source_epoch != epoch.epoch_id:
        raise ValueError("challenger source epoch does not match promotion epoch")
    retired = list(registry.retired)
    if registry.champion is not None:
        retired.append(registry.champion)
    promotion = PromotionRecord(
        from_model=registry.champion.model_id if registry.champion else "",
        to_model=challenger.model_id,
        epoch_id=epoch.epoch_id,
        approved_by=approved_by,
        approved_at=approved_at,
        notes=notes,
    )
    return registry.model_copy(update={
        "champion": challenger,
        "challengers": [
            item for item in registry.challengers if item.model_id != challenger_id
        ],
        "retired": retired,
        "promotions": [*registry.promotions, promotion],
    })
