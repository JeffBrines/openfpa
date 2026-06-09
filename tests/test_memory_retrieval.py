from pyfpa.memory.retrieval import (
    build_context_pack,
    build_memory_index,
    load_memory_index,
    save_memory_index,
    search_memory,
)


def test_memory_index_finds_relevant_canonical_files(tmp_path):
    (tmp_path / "corrections").mkdir()
    (tmp_path / "business-profile.md").write_text(
        "# Acme Profile\n\nWholesale customers pay on net 45 terms.\n"
    )
    (tmp_path / "corrections" / "collections.md").write_text(
        "# Collections Correction\n\nCustomers usually pay 10 days late.\n"
    )

    index = build_memory_index(tmp_path)
    hits = search_memory(index, "wholesale customer collections payment")

    assert len(index.entries) == 2
    assert hits[0].path in {"business-profile.md", "corrections/collections.md"}
    assert all(hit.score > 0 for hit in hits)


def test_memory_search_can_filter_categories(tmp_path):
    (tmp_path / "corrections").mkdir()
    (tmp_path / "decisions").mkdir()
    (tmp_path / "corrections" / "cash.md").write_text("Cash collections lag.")
    (tmp_path / "decisions" / "cash.md").write_text("Approved cash policy.")
    index = build_memory_index(tmp_path)

    hits = search_memory(index, "cash", categories=["decisions"])

    assert [hit.category for hit in hits] == ["decisions"]


def test_memory_index_round_trip_and_context_pack(tmp_path):
    (tmp_path / "business-profile.md").write_text(
        "# Acme Profile\n\nInventory purchases peak before summer.\n"
    )
    index = build_memory_index(tmp_path)
    path = tmp_path / "index.yaml"
    save_memory_index(index, path)

    loaded = load_memory_index(path)
    pack = build_context_pack(loaded, "summer inventory cash")

    assert loaded == index
    assert "# Task Memory Pack" in pack
    assert "`business-profile.md`" in pack


def test_generated_index_does_not_index_itself(tmp_path):
    (tmp_path / "MEMORY.md").write_text("# Memory\n")
    save_memory_index(build_memory_index(tmp_path), tmp_path / "index.yaml")

    rebuilt = build_memory_index(tmp_path)

    assert [entry.path for entry in rebuilt.entries] == ["MEMORY.md"]
