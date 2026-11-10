from datetime import datetime, timedelta, timezone
import sqlite3

from app.services.automation import AutomationStore


def test_automation_lifecycle(tmp_path):
    store = AutomationStore(tmp_path / "agent.sqlite3")
    created = store.create("Morning brief", "Prepare a short daily brief.", 1440)
    assert created["enabled"] is False
    assert store.list()[0]["id"] == created["id"]
    enabled = store.set_enabled(created["id"], True)
    assert enabled["enabled"] is True
    assert enabled["next_run_at"] is not None
    disabled = store.set_enabled(created["id"], False)
    assert disabled["next_run_at"] is None
    assert store.delete(created["id"]) is True
    assert store.get(created["id"]) is None


def test_missing_automation_toggle_returns_none(tmp_path):
    store = AutomationStore(tmp_path / "agent.sqlite3")
    assert store.set_enabled("missing", True) is None


def test_claim_is_atomic_and_execution_is_recorded(tmp_path):
    path = tmp_path / "agent.sqlite3"
    store = AutomationStore(path)
    item = store.create("Due task", "Do the task.", 30)
    store.set_enabled(item["id"], True)
    with sqlite3.connect(path) as db:
        due = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        db.execute("UPDATE automations SET next_run_at = ? WHERE id = ?", (due, item["id"]))

    claimed = store.claim_due()
    assert claimed is not None
    assert claimed["id"] == item["id"]
    assert store.claim_due() is None
    store.finish(item["id"], claimed["execution_id"], "Completed safely")
    history = store.executions(item["id"])
    assert len(history) == 1
    assert history[0]["status"] == "completed"
    assert history[0]["answer"] == "Completed safely"


def test_failed_execution_is_logged_and_rescheduled(tmp_path):
    path = tmp_path / "agent.sqlite3"
    store = AutomationStore(path)
    item = store.create("Retry task", "Do the task.", 30)
    store.set_enabled(item["id"], True)
    with sqlite3.connect(path) as db:
        due = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        db.execute("UPDATE automations SET next_run_at = ? WHERE id = ?", (due, item["id"]))
    claimed = store.claim_due()
    store.fail(item["id"], claimed["execution_id"], "provider unavailable")
    history = store.executions(item["id"])
    assert history[0]["status"] == "failed"
    assert history[0]["error"] == "provider unavailable"
    updated = store.get(item["id"])
    assert updated["failure_count"] == 1
    assert updated["lease_until"] is None
    assert updated["next_run_at"] is not None
