"""게임 상태 파일 읽기/쓰기와 행동 기록."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
STATE_PATH = Path(".github/blackjack_state.json")
HISTORY_LIMIT = 10


def initial_state() -> dict:
    return {
        "version": 1,
        "owner": "how-to-song",
        "commit_chips": 0,
        "current_chips": 0,
        "bet": 10,
        "status": "idle",
        "result": None,
        "game_id": 0,
        "draw_index": 0,
        "player_hand": [],
        "dealer_hand": [],
        "reset_log": {"date": None, "counts": {}},
        "history": [],
        "last_processed_issue": 0,
        "last_updated": None,
    }


def load_state(path: Path) -> dict:
    if not path.exists():
        return initial_state()
    return json.loads(path.read_text(encoding="utf-8"))


def dump_state(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2) + "\n"


def save_state(state: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump_state(state))


def kst_iso(now: datetime) -> str:
    return now.astimezone(KST).isoformat(timespec="seconds")


def add_history(state: dict, *, issue: int, action: str, detail: str, actor: str, now: datetime) -> None:
    entry = {"issue": issue, "action": action, "detail": detail, "actor": actor, "at": kst_iso(now)}
    state["history"] = [entry] + state["history"][: HISTORY_LIMIT - 1]


def find_history(state: dict, issue: int) -> dict | None:
    for entry in state["history"]:
        if entry["issue"] == issue:
            return entry
    return None
