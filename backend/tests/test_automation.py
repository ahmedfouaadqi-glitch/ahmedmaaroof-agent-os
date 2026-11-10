from app.services.automation import AutomationStore

def test_automation_lifecycle(tmp_path):
    store = AutomationStore(tmp_path / "agent.sqlite3")
    created = store.create("Morning brief", "Prepare a short daily brief.", 1440)
    assert created["enabled"] is False
    assert store.list()[0]["id"] == created["id"]
    enabled = store.set_enabled(created["id"], True)
    assert enabled["enabled"] is True
    assert store.delete(created["id"]) is True
    assert store.get(created["id"]) is None

def test_missing_automation_toggle_returns_none(tmp_path):
    store = AutomationStore(tmp_path / "agent.sqlite3")
    assert store.set_enabled("missing", True) is None
