from datetime import datetime, timezone

from blackjack.cards import full_deck
from blackjack.game import apply_action
from blackjack.state import initial_state

KST_EVENING = datetime(2026, 11, 8, 14, 59, tzinfo=timezone.utc)   # KST 11-08 23:59
KST_MIDNIGHT = datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc)   # KST 11-09 00:00


def reset(s, actor="octocat", now=KST_EVENING, fetch=lambda login: 345):
    return apply_action(s, "reset", actor=actor, now=now,
                        deck_for=lambda g: full_deck(), fetch_contributions=fetch)


def test_reset_sets_chips_from_contributions():
    s = initial_state()
    out = reset(s)
    assert out.changed and out.message == "칩을 🪙 345개로 설정 (최근 1년 기여 345)"
    assert s["current_chips"] == 345 and s["commit_chips"] == 345 and s["status"] == "idle"


def test_reset_floor_is_10():
    s = initial_state()
    out = reset(s, fetch=lambda login: 3)
    assert s["current_chips"] == 10 and s["commit_chips"] == 3
    assert out.message == "칩을 🪙 10개로 설정 (최근 1년 기여 3)"


def test_reset_queries_owner_not_actor():
    asked = []
    s = initial_state()
    reset(s, actor="visitor", fetch=lambda login: asked.append(login) or 50)
    assert asked == ["how-to-song"]


def test_reset_from_finished_and_broke():
    for status in ("finished", "broke"):
        s = initial_state()
        s["status"] = status
        s["player_hand"] = ["HK"]
        assert reset(s).changed and s["status"] == "idle" and s["player_hand"] == []


def test_reset_blocked_while_playing_and_not_counted():
    s = initial_state()
    s["status"] = "playing"
    out = reset(s)
    assert not out.changed and out.message == "지금은 Reset을(를) 할 수 없습니다. (현재 상태: playing)"
    assert s["reset_log"]["counts"] == {}


def test_sixth_reset_in_a_day_is_rejected():
    s = initial_state()
    for _ in range(5):
        assert reset(s).changed
    out = reset(s)
    assert not out.changed and out.message == "오늘 Reset 횟수를 다 쓰셨습니다"
    assert s["reset_log"] == {"date": "2026-11-08", "counts": {"octocat": 5}}


def test_limit_is_per_person():
    s = initial_state()
    for _ in range(5):
        reset(s)
    assert reset(s, actor="someone").changed


def test_reset_count_ignores_login_case():
    s = initial_state()
    for _ in range(5):
        reset(s, actor="Octocat")
    assert not reset(s, actor="octocat").changed


def test_count_resets_at_kst_midnight():
    s = initial_state()
    for _ in range(5):
        reset(s, now=KST_EVENING)
    assert not reset(s, now=KST_EVENING).changed
    assert reset(s, now=KST_MIDNIGHT).changed
    assert s["reset_log"] == {"date": "2026-11-09", "counts": {"octocat": 1}}


def test_fetch_failure_changes_nothing_and_is_not_counted():
    s = initial_state()
    s["current_chips"] = 40
    s["status"] = "finished"

    def boom(login):
        raise RuntimeError("api down")

    out = reset(s, fetch=boom)
    assert not out.changed and out.message == "기여 수를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
    assert s["current_chips"] == 40 and s["status"] == "finished"
    assert s["reset_log"]["counts"] == {}
