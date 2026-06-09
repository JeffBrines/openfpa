import pytest

from pyfpa.memory.entrypoints import (
    CompanyEntrypoint,
    EntrypointRegistry,
    load_entrypoint_registry,
    register_entrypoint,
    save_entrypoint_registry,
)


def entrypoint(name: str = "forecast") -> CompanyEntrypoint:
    return CompanyEntrypoint(
        name=name,
        kind="forecast",
        description="Run the company monthly forecast.",
        command=["python3", "models/generated/forecast.py"],
        inputs=["data/actuals.csv"],
        outputs=["output/forecast.xlsx"],
    )


def test_entrypoint_registry_round_trip(tmp_path):
    path = tmp_path / "entrypoints.yaml"
    registry = register_entrypoint(EntrypointRegistry(), entrypoint())

    save_entrypoint_registry(registry, path)

    assert load_entrypoint_registry(path) == registry


def test_entrypoint_registration_requires_explicit_overwrite():
    registry = register_entrypoint(EntrypointRegistry(), entrypoint())

    with pytest.raises(ValueError, match="already registered"):
        register_entrypoint(registry, entrypoint())

    replacement = entrypoint().model_copy(
        update={"description": "Run the revised company forecast."}
    )
    updated = register_entrypoint(registry, replacement, overwrite=True)
    assert updated.entrypoints == [replacement]


@pytest.mark.parametrize(
    "field,value",
    [
        ("working_directory", "../outside"),
        ("inputs", ["/absolute/input.csv"]),
        ("outputs", ["../outside.xlsx"]),
    ],
)
def test_entrypoint_paths_must_stay_relative(field, value):
    with pytest.raises(ValueError, match="relative path"):
        CompanyEntrypoint(
            name="forecast",
            kind="forecast",
            description="Run forecast.",
            command=["python3", "forecast.py"],
            **{field: value},
        )
