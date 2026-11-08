from datetime import datetime, timezone

from blackjack.state import (add_history, find_history, initial_state, kst_iso,
                             load_state, save_state)

NOW = datetime(2026, 11, 8, 5, 5, tzinfo=timezone.utc)


def test_missing_file_gives_initial_state(tmp_path):
    s = load_state(tmp_path / "none.json")
    assert s["status"] == "idle" and s["current_chips"] == 0 and s["last_processed_issue"] == 0
    assert "deck" not in s


def test_round_trip_keeps_korean(tmp_path):
    p = tmp_path / "s.json"
    s = initial_state()
    add_history(s, issue=1, action="Hit", detail="C3 받음 · 합계 18", actor="octocat", now=NOW)
    save_state(s, p)
    assert "받음" in p.read_text(encoding="utf-8")
    assert load_state(p) == s


def test_kst_iso():
    assert kst_iso(NOW) == "2026-11-08T14:05:00+09:00"


def test_history_newest_first_and_capped_at_10():
    s = initial_state()
    for n in range(1, 13):
        add_history(s, issue=n, action="Hit", detail=f"d{n}", actor="a", now=NOW)
    assert len(s["history"]) == 10
    assert s["history"][0]["issue"] == 12 and s["history"][-1]["issue"] == 3
    assert find_history(s, 12)["detail"] == "d12" and find_history(s, 1) is None
