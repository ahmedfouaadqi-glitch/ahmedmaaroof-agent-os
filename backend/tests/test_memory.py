from pathlib import Path
from app.services.memory import MemoryStore

def make_store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "agent.sqlite3")

def test_upsert_and_stats(tmp_path):
    store = make_store(tmp_path)
    result = store.upsert_document("Project Atlas", "A project about Iraqi market intelligence.", "test")
    assert result["chunks"] == 1
    assert store.stats() == {"documents": 1, "chunks": 1}

def test_search_returns_matching_content(tmp_path):
    store = make_store(tmp_path)
    store.upsert_document("Market Pulse", "Baghdad retail market intelligence and competitor signals.", "test")
    results = store.search("Baghdad competitor")
    assert results
    assert results[0]["title"] == "Market Pulse"

def test_upsert_replaces_existing_document(tmp_path):
    store = make_store(tmp_path)
    store.upsert_document("Notes", "Old content about logistics.", "manual")
    store.upsert_document("Notes", "New content about digital commerce.", "manual")
    assert store.stats() == {"documents": 1, "chunks": 1}
    assert store.search("digital commerce")

def test_ingest_vault_indexes_markdown(tmp_path):
    vault = tmp_path / "Vault"
    (vault / "Projects").mkdir(parents=True)
    (vault / "Projects" / "Maaroof.md").write_text("# Maaroof\n\nAgent operating system memory.", encoding="utf-8")
    store = make_store(tmp_path)
    result = store.ingest_vault(vault)
    assert result["documents_ingested"] == 1
    assert store.search("operating system")
