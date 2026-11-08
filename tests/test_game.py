import json
from datetime import datetime, timezone

import pytest

from blackjack.game import LABELS, allowed_actions, apply_action
from blackjack.state import initial_state
from tests.helpers import stacked_deck

NOW = datetime(2026, 11, 8, 5, 5, tzinfo=timezone.utc)


def play(state, action, top):
    return apply_action(state, action, actor="octocat", now=NOW,
                        deck_for=lambda gid: stacked_deck(top),
                        fetch_contributions=lambda login: 345)


def fresh(chips=100):
    s = initial_state()
    s["current_chips"] = chips
    return s


def test_deal_starts_playing_round():
    s = fresh()
    out = play(s, "deal", ["HK", "D5", "C9", "S7"])
    assert out.changed and out.message == "새 판 시작 · 베팅 10 · 합계 19"
    assert s["status"] == "playing" and s["current_chips"] == 90 and s["game_id"] == 1
    assert s["player_hand"] == ["HK", "C9"] and s["dealer_hand"] == ["D5"] and s["draw_index"] == 4


def test_deal_never_exposes_hole_card():
    s = fresh()
    out = play(s, "deal", ["HK", "D5", "C9", "S7"])
    assert "S7" not in out.message and "S7" not in json.dumps(s)


def test_player_blackjack_pays_25():
    s = fresh()
    out = play(s, "deal", ["SA", "D5", "HK", "S7"])
    assert s["result"] == "player_blackjack" and s["status"] == "finished"
    assert s["current_chips"] == 115 and s["dealer_hand"] == ["D5", "S7"]
    assert out.message == "새 판 시작 · 블랙잭 승리!"


def test_dealer_blackjack_wins():
    s = fresh()
    play(s, "deal", ["H9", "SA", "H8", "DK"])
    assert s["result"] == "dealer_win" and s["current_chips"] == 90


def test_both_blackjack_is_push():
    s = fresh()
    play(s, "deal", ["SA", "HA", "SK", "DK"])
    assert s["result"] == "push" and s["current_chips"] == 100


def test_hit_then_bust():
    top = ["HK", "D5", "C5", "S7", "C3", "SK"]
    s = fresh()
    play(s, "deal", top)
    out = play(s, "hit", top)
    assert out.message == "C3 받음 · 합계 18" and s["status"] == "playing"
    out = play(s, "hit", top)
    assert out.message == "SK 받음 · 합계 28 · 플레이어 버스트"
    assert s["result"] == "player_bust" and s["current_chips"] == 90 and s["dealer_hand"] == ["D5", "S7"]


def test_stand_player_wins():
    top = ["HK", "D5", "C9", "S7", "H6"]
    s = fresh()
    play(s, "deal", top)
    out = play(s, "stand", top)
    assert s["dealer_hand"] == ["D5", "S7", "H6"] and s["result"] == "player_win"
    assert s["current_chips"] == 110
    assert out.message == "딜러 D5 S7 H6 · 합계 18 · 플레이어 승리!"


def test_stand_dealer_bust():
    top = ["HK", "D5", "C9", "S7", "SQ"]
    s = fresh()
    play(s, "deal", top)
    play(s, "stand", top)
    assert s["result"] == "dealer_bust" and s["current_chips"] == 110


def test_dealer_stands_on_soft_17():
    top = ["HK", "SA", "C7", "H6"]
    s = fresh()
    play(s, "deal", top)
    play(s, "stand", top)
    assert s["dealer_hand"] == ["SA", "H6"] and s["result"] == "push" and s["current_chips"] == 100


def test_dealer_soft_ace_turns_hard():
    top = ["HK", "SA", "C9", "H5", "SK", "C2"]
    s = fresh()
    play(s, "deal", top)
    play(s, "stand", top)
    assert s["dealer_hand"] == ["SA", "H5", "SK", "C2"] and s["result"] == "player_win"


def test_losing_last_chips_goes_broke():
    top = ["HK", "D5", "C6", "S7", "H6"]   # 플레이어 16, 딜러 18
    s = fresh(chips=10)
    play(s, "deal", top)
    play(s, "stand", top)
    assert s["current_chips"] == 0 and s["status"] == "broke"


def test_push_with_last_chips_is_not_broke():
    top = ["HK", "SA", "C7", "H6"]
    s = fresh(chips=10)
    play(s, "deal", top)
    play(s, "stand", top)
    assert s["current_chips"] == 10 and s["status"] == "finished"


@pytest.mark.parametrize("status,action", [
    ("idle", "hit"), ("idle", "stand"), ("finished", "hit"),
    ("playing", "deal"), ("broke", "deal"), ("broke", "hit")])
def test_disallowed_action_changes_nothing(status, action):
    s = fresh()
    s["status"] = status
    before = json.dumps(s)
    out = play(s, action, ["HK", "D5", "C9", "S7"])
    assert not out.changed and json.dumps(s) == before
    assert out.message == f"지금은 {LABELS[action]}을(를) 할 수 없습니다. (현재 상태: {status})"


def test_deal_without_chips():
    s = fresh(chips=0)
    out = play(s, "deal", ["HK", "D5", "C9", "S7"])
    assert not out.changed and out.message == "칩이 부족합니다. Reset을 눌러 주세요."


@pytest.mark.parametrize("status,chips,expected", [
    ("idle", 0, ["reset"]), ("idle", 100, ["deal", "reset"]), ("playing", 90, ["hit", "stand"]),
    ("finished", 50, ["deal", "reset"]), ("broke", 0, ["reset"])])
def test_allowed_actions(status, chips, expected):
    s = fresh(chips)
    s["status"] = status
    assert allowed_actions(s) == expected
