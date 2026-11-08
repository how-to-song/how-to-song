"""행동 적용, 판정, 정산."""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from blackjack.cards import hand_value, is_blackjack
from blackjack.state import KST

ACTIONS = ("deal", "hit", "stand", "reset")
LABELS = {"deal": "Deal", "hit": "Hit", "stand": "Stand", "reset": "Reset"}
BET = 10
MIN_CHIPS = 10
RESET_LIMIT = 5

RESULT_TEXT = {
    "player_blackjack": "블랙잭 승리!",
    "player_win": "플레이어 승리!",
    "dealer_bust": "딜러 버스트! 플레이어 승리",
    "dealer_win": "딜러 승리",
    "player_bust": "플레이어 버스트",
    "push": "무승부 (Push)",
}
PAYOUT = {"player_blackjack": 25, "player_win": 20, "dealer_bust": 20,
          "push": 10, "dealer_win": 0, "player_bust": 0}

HOLE_INDEX = 3      # 분배 순서: 플레이어, 딜러(앞면), 플레이어, 딜러(숨김)


@dataclass
class Outcome:
    changed: bool
    message: str


def allowed_actions(state: dict) -> list[str]:
    status = state["status"]
    if status == "idle":
        return ["deal", "reset"] if state["current_chips"] >= BET else ["reset"]
    if status == "playing":
        return ["hit", "stand"]
    if status == "finished":
        return ["deal", "reset"]
    return ["reset"]


def _not_now(state: dict, action: str) -> Outcome:
    return Outcome(False, f"지금은 {LABELS[action]}을(를) 할 수 없습니다. (현재 상태: {state['status']})")


def _finish(state: dict, result: str, dealer_full: list[str]) -> None:
    state["dealer_hand"] = dealer_full
    state["result"] = result
    state["current_chips"] += PAYOUT[result]
    state["status"] = "broke" if state["current_chips"] < BET else "finished"


def _deal(state: dict, deck_for: Callable[[int], list[str]]) -> Outcome:
    if state["status"] not in ("idle", "finished"):
        return _not_now(state, "deal")
    if state["current_chips"] < BET:
        return Outcome(False, "칩이 부족합니다. Reset을 눌러 주세요.")
    state["game_id"] += 1
    state["current_chips"] -= BET
    deck = deck_for(state["game_id"])
    player = [deck[0], deck[2]]
    dealer_full = [deck[1], deck[HOLE_INDEX]]
    state["player_hand"] = player
    state["draw_index"] = 4
    state["result"] = None
    player_bj, dealer_bj = is_blackjack(player), is_blackjack(dealer_full)
    if player_bj or dealer_bj:
        result = "push" if player_bj and dealer_bj else ("player_blackjack" if player_bj else "dealer_win")
        _finish(state, result, dealer_full)
        return Outcome(True, f"새 판 시작 · {RESULT_TEXT[result]}")
    state["status"] = "playing"
    state["dealer_hand"] = [deck[1]]
    return Outcome(True, f"새 판 시작 · 베팅 {BET} · 합계 {hand_value(player)[0]}")


def _hit(state: dict, deck_for: Callable[[int], list[str]]) -> Outcome:
    if state["status"] != "playing":
        return _not_now(state, "hit")
    deck = deck_for(state["game_id"])
    card = deck[state["draw_index"]]
    state["draw_index"] += 1
    state["player_hand"].append(card)
    total = hand_value(state["player_hand"])[0]
    message = f"{card} 받음 · 합계 {total}"
    if total > 21:
        _finish(state, "player_bust", [state["dealer_hand"][0], deck[HOLE_INDEX]])
        message += f" · {RESULT_TEXT['player_bust']}"
    return Outcome(True, message)


def _stand(state: dict, deck_for: Callable[[int], list[str]]) -> Outcome:
    if state["status"] != "playing":
        return _not_now(state, "stand")
    deck = deck_for(state["game_id"])
    dealer = [state["dealer_hand"][0], deck[HOLE_INDEX]]
    while hand_value(dealer)[0] < 17:       # soft 17에서도 멈춘다 (S17)
        dealer.append(deck[state["draw_index"]])
        state["draw_index"] += 1
    dealer_total = hand_value(dealer)[0]
    player_total = hand_value(state["player_hand"])[0]
    if dealer_total > 21:
        result = "dealer_bust"
    elif player_total > dealer_total:
        result = "player_win"
    elif player_total == dealer_total:
        result = "push"
    else:
        result = "dealer_win"
    _finish(state, result, dealer)
    return Outcome(True, f"딜러 {' '.join(dealer)} · 합계 {dealer_total} · {RESULT_TEXT[result]}")


def _reset(state: dict, actor: str, now: datetime, fetch_contributions: Callable[[str], int]) -> Outcome:
    if state["status"] == "playing":
        return _not_now(state, "reset")
    today = now.astimezone(KST).date().isoformat()
    if state["reset_log"]["date"] != today:
        state["reset_log"] = {"date": today, "counts": {}}
    counts = state["reset_log"]["counts"]
    key = actor.lower()
    if counts.get(key, 0) >= RESET_LIMIT:
        return Outcome(False, "오늘 Reset 횟수를 다 쓰셨습니다")
    try:
        contributions = int(fetch_contributions(state["owner"]))
    except Exception:
        return Outcome(False, "기여 수를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
    chips = max(contributions, MIN_CHIPS)
    state.update(commit_chips=contributions, current_chips=chips, status="idle", result=None,
                 player_hand=[], dealer_hand=[], draw_index=0)
    counts[key] = counts.get(key, 0) + 1
    return Outcome(True, f"칩을 🪙 {chips}개로 설정 (최근 1년 기여 {contributions})")


def apply_action(state: dict, action: str, *, actor: str, now: datetime,
                 deck_for: Callable[[int], list[str]],
                 fetch_contributions: Callable[[str], int]) -> Outcome:
    """state를 제자리에서 바꾸고 결과 문구를 돌려준다."""
    if action == "deal":
        return _deal(state, deck_for)
    if action == "hit":
        return _hit(state, deck_for)
    if action == "stand":
        return _stand(state, deck_for)
    if action == "reset":
        return _reset(state, actor, now, fetch_contributions)
    raise ValueError(f"unknown action: {action}")
