from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


EntrypointKind = Literal[
    "forecast",
    "close",
    "cash",
    "research",
    "report",
    "connector",
    "custom",
]


def _relative_path(value: str) -> str:
    value = value.strip()
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be a non-empty relative path without '..'")
    return path.as_posix()


class CompanyEntrypoint(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    kind: EntrypointKind
    description: str
    command: list[str] = Field(min_length=1)
    working_directory: str = "."
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("description must not be empty")
        return value

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: list[str]) -> list[str]:
        command = [item.strip() for item in value]
        if any(not item for item in command):
            raise ValueError("command arguments must not be empty")
        return command

    @field_validator("working_directory")
    @classmethod
    def validate_working_directory(cls, value: str) -> str:
        if value == ".":
            return value
        return _relative_path(value)

    @field_validator("inputs", "outputs")
    @classmethod
    def validate_paths(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(_relative_path(item) for item in value))


class EntrypointRegistry(BaseModel):
    schema_version: int = 1
    entrypoints: list[CompanyEntrypoint] = Field(default_factory=list)


def load_entrypoint_registry(path: str | Path) -> EntrypointRegistry:
    path = Path(path)
    if not path.exists():
        return EntrypointRegistry()
    return EntrypointRegistry.model_validate(yaml.safe_load(path.read_text()) or {})


def save_entrypoint_registry(registry: EntrypointRegistry, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry.model_dump(), sort_keys=False))


def register_entrypoint(
    registry: EntrypointRegistry,
    entrypoint: CompanyEntrypoint,
    *,
    overwrite: bool = False,
) -> EntrypointRegistry:
    existing = next(
        (item for item in registry.entrypoints if item.name == entrypoint.name),
        None,
    )
    if existing is not None and not overwrite:
        raise ValueError(f"entrypoint already registered: {entrypoint.name}")
    retained = [
        item for item in registry.entrypoints if item.name != entrypoint.name
    ]
    return registry.model_copy(
        update={"entrypoints": sorted(
            [*retained, entrypoint],
            key=lambda item: item.name,
        )}
    )
