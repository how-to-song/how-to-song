# GitHub 프로필 블랙잭 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 방문자가 README 버튼 → Issue 제출로 하나의 공유 블랙잭 판을 이어서 플레이하고, GitHub Actions가 상태 파일과 README 게임 구간을 갱신한다.

**Architecture:** 순수 로직(`cards`, `deck`, `state`, `game`, `render`)과 입출력(`github`, `main`)을 나눈다. `main`은 열린 `blackjack-*` Issue를 번호순으로 적용 → 상태 파일·README 저장 → git push → 성공하면 Issue 댓글·닫기·잠금. 덱은 상태 파일에 없고 `BLACKJACK_SECRET` HMAC 시드로 매번 다시 계산한다.

**Tech Stack:** Python 3.12(Actions) / 표준 라이브러리만, pytest, GitHub Actions, GitHub REST + GraphQL API.

**Spec:** [docs/architecture.md](../../architecture.md), [docs/requirements.md](../../requirements.md). 요구사항 번호(R1…)는 requirements.md를 따른다.

## Global Constraints

- 게임 코드(`blackjack/`)는 표준 라이브러리만 쓴다. HTTP는 `urllib.request`. 테스트만 pytest.
- 로컬 Python은 3.11.9, Actions는 3.12다. **3.11에서도 돌아가는 문법만** 쓴다(`type X = ...` 문 금지).
- 저장소: `how-to-song/how-to-song`, 소유자(칩 기준 계정): `how-to-song`, 베팅: `10`, 최소 시작 칩: `10`.
- 상태 파일 경로: `.github/blackjack_state.json`. README 마커: `<!-- blackjack -->`, `<!-- /blackjack -->`.
- 카드 표기: 무늬 `S/H/D/C` + 숫자 `A, 2~10, J, Q, K` (예: `CA`, `D10`, `SK`). 이미지 경로: `assets/cards/<표기>.svg`, 뒷면 `assets/cards/back.svg`.
- 시각은 KST(UTC+9). 저장은 `datetime.isoformat(timespec="seconds")`(예: `2026-11-08T14:05:00+09:00`).
- 남은 덱 순서와 플레이 중 딜러의 숨긴 카드는 상태 파일·README·로그(`print`)·Issue 댓글·커밋 메시지 어디에도 나오지 않는다(R19).
- 커밋 메시지·주석은 한국어. 작업은 `feat/blackjack-game` 브랜치에서, 태스크마다 커밋.

### 고정 문구 (game.py `MESSAGES`, render.py에서 그대로 사용)

| 키 | 문구 |
|---|---|
| 결과 `player_blackjack` | `블랙잭 승리!` |
| 결과 `player_win` | `플레이어 승리!` |
| 결과 `dealer_bust` | `딜러 버스트! 플레이어 승리` |
| 결과 `dealer_win` | `딜러 승리` |
| 결과 `player_bust` | `플레이어 버스트` |
| 결과 `push` | `무승부 (Push)` |
| Deal 성공(판 계속) | `새 판 시작 · 베팅 10 · 합계 {player_total}` |
| Deal 즉시 판정 | `새 판 시작 · {결과 문구}` |
| Hit | `{card} 받음 · 합계 {total}` (버스트면 뒤에 ` · 플레이어 버스트`) |
| Stand | `딜러 {cards를 ' '로 연결} · 합계 {dealer_total} · {결과 문구}` |
| Reset 성공 | `칩을 🪙 {chips}개로 설정 (최근 1년 기여 {contributions})` |
| 지금 할 수 없음 | `지금은 {Label}을(를) 할 수 없습니다. (현재 상태: {status})` |
| 칩 부족 Deal | `칩이 부족합니다. Reset을 눌러 주세요.` |
| Reset 한도 | `오늘 Reset 횟수를 다 쓰셨습니다` |
| 기여 수 조회 실패 | `기여 수를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.` |
| 알 수 없는 제목 | `알 수 없는 행동입니다. README의 버튼을 눌러 주세요.` |
| 이미 처리됨(기록 없음) | `이미 처리된 요청입니다.` |
| README 안내(R31) | `🤖 링크를 누른 뒤 약 1분 후 새로고침(F5)해 주세요!` |
| Issue 본문(R3) | `이 Issue의 제목과 내용을 바꾸지 말고 그대로 제출만 하세요. 약 1분 뒤 프로필 README가 갱신됩니다.` |
| 칩 0 시작 안내 | `Reset을 눌러 게임을 시작하세요` |
| 판 시작 전 안내 | `Deal을 눌러 새 판을 시작하세요` |

`{Label}`은 `Deal`/`Hit`/`Stand`/`Reset`.

## Review Focus

1. **로그인 대소문자** — `Octocat`과 `octocat`은 같은 사람이다. Reset 횟수 키는 소문자로 저장한다(Task 5 테스트 `test_reset_count_ignores_login_case`).
2. **열린 Issue가 100개 넘음** — 목록 API는 `Link: rel="next"`를 따라 모든 페이지를 읽어야 한다(Task 7 `test_list_follows_pagination`).
3. **소유자가 README 마커를 지움** — 상태 파일도 README도 쓰지 않고, push도 댓글도 하지 않은 채 실패한다. Issue는 열린 채 남는다(Task 8 `test_missing_marker_changes_nothing`).
4. **Deal 직후 숨긴 카드 노출** — Deal 결과 문구, 상태 파일 JSON, 렌더된 README 어디에도 덱 4번째 카드가 나오지 않는다(Task 4 `test_deal_never_exposes_hole_card`, Task 6 `test_playing_board_hides_hole_card`).
5. **처리할 Issue가 없는 정기 실행** — 1시간마다 도는 `schedule`이 아무 Issue도 없을 때 파일을 바꾸거나 커밋하지 않는다(`last_updated`는 Issue를 처리할 때만 바뀐다)(Task 8 `test_idle_run_does_not_push`).

---

## 파일 구조

```text
pyproject.toml                    # pytest 설정 (testpaths, pythonpath)
requirements-dev.txt              # pytest
.github/workflows/ci.yml          # push/PR 시 pytest            (Task 1)
.github/workflows/blackjack.yml   # 게임 워크플로                  (Task 10)
blackjack/__init__.py
blackjack/cards.py     # 카드 표기, 점수                          (Task 1)
blackjack/deck.py      # HMAC 시드 셔플                          (Task 2)
blackjack/state.py     # 초기 상태, 읽기/쓰기, 기록, KST          (Task 3)
blackjack/game.py      # 행동 적용, 판정, 정산, Reset 제한         (Task 4, 5)
blackjack/render.py    # 게임판 HTML, 마커 치환                   (Task 6)
blackjack/github.py    # GitHub API 클라이언트                    (Task 7)
blackjack/main.py      # Issue 처리 흐름, git push, 진입점         (Task 8)
assets/cards/          # 52장 + back.svg + LICENSE.md             (Task 9)
assets/buttons/        # deal/hit/stand/reset.svg                 (Task 9)
tests/helpers.py       # stacked_deck()                           (Task 4)
tests/fakes.py         # FakeGitHub                               (Task 8)
tests/test_*.py
README.md              # 맨 위에 마커 추가                         (Task 9)
```

[결정] 설계 3장은 "커밋·push는 워크플로 단계"처럼 읽히지만, push 성공 뒤에만 댓글을 달아야 하므로 커밋·push도 `main.py`가 `subprocess`로 한다. 그래야 순서가 한 프로세스 안에서 보장된다.

---

### Task 1: 프로젝트 뼈대, 카드 점수, CI

**Files:**
- Create: `pyproject.toml`, `requirements-dev.txt`, `.gitattributes`, `blackjack/__init__.py`, `blackjack/cards.py`, `.github/workflows/ci.yml`
- Test: `tests/test_cards.py`

**Interfaces:**
- Produces:
  - `SUITS = ("S", "H", "D", "C")`, `RANKS = ("A", "2", …, "10", "J", "Q", "K")`
  - `full_deck() -> list[str]` — 52장, 무늬 순(S→H→D→C) 안에서 RANKS 순. 항상 같은 순서.
  - `hand_value(cards: list[str]) -> tuple[int, bool]` — (합계, soft 여부). soft = Ace 하나를 11로 셌을 때 True.
  - `is_blackjack(cards: list[str]) -> bool` — 정확히 2장이고 합계 21.

- [ ] **Step 1: pytest 설치와 설정**

`requirements-dev.txt`에 `pytest` 한 줄. `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```
`.gitattributes`에 `* text=auto eol=lf` 한 줄(Windows와 Actions의 줄바꿈 통일).
Run: `python -m pip install -r requirements-dev.txt` → `python -m pytest --version`이 버전을 출력.

- [ ] **Step 2: 실패하는 테스트 작성** (`tests/test_cards.py`)

```python
from blackjack.cards import full_deck, hand_value, is_blackjack

def test_full_deck_is_52_unique_cards():
    deck = full_deck()
    assert len(deck) == 52 and len(set(deck)) == 52
    assert deck[0] == "SA" and deck[-1] == "CK" and "D10" in deck

def test_face_cards_are_ten():
    assert hand_value(["HK", "DQ"]) == (20, False)
    assert hand_value(["SJ", "C10"]) == (20, False)

def test_ace_is_eleven_when_safe():
    assert hand_value(["SA", "H6"]) == (17, True)

def test_ace_drops_to_one_when_over():
    assert hand_value(["SA", "H6", "DK"]) == (17, False)

def test_two_aces():
    assert hand_value(["SA", "HA"]) == (12, True)
    assert hand_value(["SA", "HA", "D9"]) == (21, True)
    assert hand_value(["SA", "HA", "D9", "CK"]) == (21, False)

def test_blackjack_needs_exactly_two_cards():
    assert is_blackjack(["SA", "HK"]) is True
    assert is_blackjack(["SA", "H5", "D5"]) is False
    assert is_blackjack(["HK", "DQ"]) is False
```

- [ ] **Step 3: 실패 확인** — Run: `python -m pytest tests/test_cards.py -v` → FAIL (`ModuleNotFoundError: blackjack.cards`)

- [ ] **Step 4: `blackjack/cards.py` 구현** — 숫자 부분은 `card[1:]`. Ace는 1로 더한 뒤, Ace가 있고 합계+10 ≤ 21이면 +10 하고 soft=True.

- [ ] **Step 5: 통과 확인** — Run: `python -m pytest -v` → 6 passed

- [ ] **Step 6: CI 워크플로** (`.github/workflows/ci.yml`)

```yaml
name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -r requirements-dev.txt
      - run: python -m pytest
```

- [ ] **Step 7: 커밋** — `git add pyproject.toml requirements-dev.txt .gitattributes blackjack tests .github/workflows/ci.yml` → `git commit -m "feat: 카드 점수 계산과 CI 추가"`

---

### Task 2: 비밀값 기반 덱

**Files:**
- Create: `blackjack/deck.py`
- Test: `tests/test_deck.py`

**Interfaces:**
- Consumes: `cards.full_deck()`
- Produces: `shuffled_deck(secret: str, game_id: int) -> list[str]` — 52장 새 리스트.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from blackjack.cards import full_deck
from blackjack.deck import shuffled_deck

def test_same_secret_and_game_give_same_deck():
    assert shuffled_deck("s3cret", 7) == shuffled_deck("s3cret", 7)

def test_different_game_or_secret_changes_deck():
    base = shuffled_deck("s3cret", 7)
    assert shuffled_deck("s3cret", 8) != base
    assert shuffled_deck("other", 7) != base

def test_deck_is_a_permutation_and_shuffled():
    deck = shuffled_deck("s3cret", 1)
    assert sorted(deck) == sorted(full_deck())
    assert deck != full_deck()
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_deck.py -v` → FAIL (import error)

- [ ] **Step 3: 구현** — 시드는 설계 5장 그대로:
```python
digest = hmac.new(secret.encode(), f"game:{game_id}".encode(), hashlib.sha256).digest()
rng = random.Random(int.from_bytes(digest, "big"))
deck = full_deck(); rng.shuffle(deck); return deck
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 5: 커밋** — `git commit -m "feat: HMAC 시드 기반 덱 셔플"`

---

### Task 3: 상태 파일

**Files:**
- Create: `blackjack/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Produces:
  - `KST = timezone(timedelta(hours=9))`
  - `STATE_PATH = Path(".github/blackjack_state.json")`, `HISTORY_LIMIT = 10`
  - `initial_state() -> dict` — 설계 4장의 키 전부. 값: `version 1, owner "how-to-song", commit_chips 0, current_chips 0, bet 10, status "idle", result None, game_id 0, draw_index 0, player_hand [], dealer_hand [], reset_log {"date": None, "counts": {}}, history [], last_processed_issue 0, last_updated None`.
  - `load_state(path: Path) -> dict` — 파일이 없으면 `initial_state()`.
  - `dump_state(state: dict) -> str` — `json.dumps(state, ensure_ascii=False, indent=2) + "\n"`. (main이 바뀌었는지 비교하는 데 씀)
  - `save_state(state: dict, path: Path) -> None` — `dump_state` 결과를 UTF-8, 줄바꿈 `\n`으로 쓴다(`newline="\n"`).
  - `kst_iso(now: datetime) -> str` — `now.astimezone(KST).isoformat(timespec="seconds")`.
  - `add_history(state, *, issue: int, action: str, detail: str, actor: str, now: datetime) -> None` — 맨 앞에 넣고 10개까지만 남김. 항목 키: `issue, action, detail, actor, at`.
  - `find_history(state, issue: int) -> dict | None`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from datetime import datetime, timezone
from blackjack.state import (initial_state, load_state, save_state, add_history,
                             find_history, kst_iso)

NOW = datetime(2026, 11, 8, 5, 5, tzinfo=timezone.utc)

def test_missing_file_gives_initial_state(tmp_path):
    s = load_state(tmp_path / "none.json")
    assert s["status"] == "idle" and s["current_chips"] == 0 and s["last_processed_issue"] == 0
    assert "deck" not in s

def test_round_trip_keeps_korean(tmp_path):
    p = tmp_path / "s.json"
    s = initial_state(); add_history(s, issue=1, action="Hit", detail="C3 받음 · 합계 18", actor="octocat", now=NOW)
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
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_state.py -v` → FAIL

- [ ] **Step 3: `blackjack/state.py` 구현**

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 5: 커밋** — `git commit -m "feat: 상태 파일 읽기·쓰기와 행동 기록"`

---

### Task 4: Deal / Hit / Stand와 정산

**Files:**
- Create: `blackjack/game.py`, `tests/helpers.py`
- Test: `tests/test_game.py`

**Interfaces:**
- Consumes: `cards.hand_value`, `cards.is_blackjack`, `cards.full_deck`
- Produces:
  - `ACTIONS = ("deal", "hit", "stand", "reset")`, `LABELS = {"deal": "Deal", "hit": "Hit", "stand": "Stand", "reset": "Reset"}`
  - `RESULT_TEXT: dict[str, str]` — 고정 문구 표의 결과 6개.
  - `PAYOUT = {"player_blackjack": 25, "player_win": 20, "dealer_bust": 20, "push": 10, "dealer_win": 0, "player_bust": 0}`
  - `@dataclass class Outcome: changed: bool; message: str`
  - `apply_action(state: dict, action: str, *, actor: str, now: datetime, deck_for: Callable[[int], list[str]], fetch_contributions: Callable[[str], int]) -> Outcome` — `state`를 제자리에서 바꾼다. `deck_for(game_id)`가 그 판의 52장 덱을 돌려준다. (Reset은 Task 5)
  - `allowed_actions(state: dict) -> list[str]` — R28 버튼용. `idle`: 칩 ≥ 10이면 `["deal", "reset"]`, 아니면 `["reset"]`; `playing`: `["hit", "stand"]`; `finished`: `["deal", "reset"]`; `broke`: `["reset"]`.
- `tests/helpers.py`: `stacked_deck(top: list[str]) -> list[str]` — `top` 뒤에 `full_deck()`에서 `top`을 뺀 나머지를 붙인다.

규칙(설계 5·6장):
- Deal: `status in (idle, finished)` 이고 칩 ≥ 10. `game_id += 1`, 칩 −10, 덱 `d = deck_for(game_id)`. 플레이어 `[d[0], d[2]]`, 딜러 앞면 `d[1]`, 숨긴 카드 `d[3]`, `draw_index = 4`, `result = None`. 블랙잭이 하나라도 있으면 즉시 판정(둘 다 → push, 플레이어만 → player_blackjack, 딜러만 → dealer_win), 딜러 손은 `[d[1], d[3]]` 전체 저장. 아니면 `status = "playing"`, `dealer_hand = [d[1]]`.
- Hit: `d[draw_index]`를 받고 `draw_index += 1`. 21 초과면 `player_bust`로 판 종료, 딜러 손 공개(`[up, d[3]]`).
- Stand: 딜러 손 `[up, d[3]]`, 합계 17 미만인 동안 `d[draw_index]`를 뽑는다(soft 17에서 멈춤). 딜러 > 21 → `dealer_bust`, 플레이어 > 딜러 → `player_win`, 같으면 `push`, 아니면 `dealer_win`.
- 판 종료: `status = "finished"`, `result` 저장, 칩 += `PAYOUT[result]`, 칩 < 10이면 `status = "broke"`.
- 할 수 없는 행동: 상태를 그대로 두고 `Outcome(False, "지금은 …")`. Deal인데 칩 부족이면 `Outcome(False, "칩이 부족합니다. Reset을 눌러 주세요.")`.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_game.py`)

공통: `def play(state, action, top): return apply_action(state, action, actor="octocat", now=NOW, deck_for=lambda gid: stacked_deck(top), fetch_contributions=lambda login: 345)`, 그리고 `def fresh(chips=100): s = initial_state(); s["current_chips"] = chips; return s`.

```python
def test_deal_starts_playing_round():
    s = fresh(); out = play(s, "deal", ["HK", "D5", "C9", "S7"])
    assert out.changed and out.message == "새 판 시작 · 베팅 10 · 합계 19"
    assert s["status"] == "playing" and s["current_chips"] == 90 and s["game_id"] == 1
    assert s["player_hand"] == ["HK", "C9"] and s["dealer_hand"] == ["D5"] and s["draw_index"] == 4

def test_deal_never_exposes_hole_card():
    s = fresh(); out = play(s, "deal", ["HK", "D5", "C9", "S7"])
    assert "S7" not in out.message and "S7" not in json.dumps(s)

def test_player_blackjack_pays_25():
    s = fresh(); out = play(s, "deal", ["SA", "D5", "HK", "S7"])
    assert s["result"] == "player_blackjack" and s["status"] == "finished"
    assert s["current_chips"] == 115 and s["dealer_hand"] == ["D5", "S7"]
    assert out.message == "새 판 시작 · 블랙잭 승리!"

def test_dealer_blackjack_wins():
    s = fresh(); play(s, "deal", ["H9", "SA", "H8", "DK"])
    assert s["result"] == "dealer_win" and s["current_chips"] == 90

def test_both_blackjack_is_push():
    s = fresh(); play(s, "deal", ["SA", "HA", "SK", "DK"])
    assert s["result"] == "push" and s["current_chips"] == 100

def test_hit_then_bust():
    top = ["HK", "D5", "C5", "S7", "C3", "SK"]
    s = fresh(); play(s, "deal", top)
    out = play(s, "hit", top)
    assert out.message == "C3 받음 · 합계 18" and s["status"] == "playing"
    out = play(s, "hit", top)
    assert out.message == "SK 받음 · 합계 28 · 플레이어 버스트"
    assert s["result"] == "player_bust" and s["current_chips"] == 90 and s["dealer_hand"] == ["D5", "S7"]

def test_stand_player_wins():
    top = ["HK", "D5", "C9", "S7", "H6"]
    s = fresh(); play(s, "deal", top); out = play(s, "stand", top)
    assert s["dealer_hand"] == ["D5", "S7", "H6"] and s["result"] == "player_win"
    assert s["current_chips"] == 110
    assert out.message == "딜러 D5 S7 H6 · 합계 18 · 플레이어 승리!"

def test_stand_dealer_bust():
    top = ["HK", "D5", "C9", "S7", "SQ"]
    s = fresh(); play(s, "deal", top); play(s, "stand", top)
    assert s["result"] == "dealer_bust" and s["current_chips"] == 110

def test_dealer_stands_on_soft_17():
    top = ["HK", "SA", "C7", "H6"]
    s = fresh(); play(s, "deal", top); play(s, "stand", top)
    assert s["dealer_hand"] == ["SA", "H6"] and s["result"] == "push" and s["current_chips"] == 100

def test_dealer_soft_ace_turns_hard():
    top = ["HK", "SA", "C9", "H5", "SK", "C2"]
    s = fresh(); play(s, "deal", top); play(s, "stand", top)
    assert s["dealer_hand"] == ["SA", "H5", "SK", "C2"] and s["result"] == "player_win"

def test_losing_last_chips_goes_broke():
    top = ["HK", "D5", "C6", "S7", "H6"]   # 플레이어 16, 딜러 18
    s = fresh(chips=10); play(s, "deal", top); play(s, "stand", top)
    assert s["current_chips"] == 0 and s["status"] == "broke"

def test_push_with_last_chips_is_not_broke():
    top = ["HK", "SA", "C7", "H6"]
    s = fresh(chips=10); play(s, "deal", top); play(s, "stand", top)
    assert s["current_chips"] == 10 and s["status"] == "finished"

@pytest.mark.parametrize("status,action", [
    ("idle", "hit"), ("idle", "stand"), ("finished", "hit"),
    ("playing", "deal"), ("broke", "deal"), ("broke", "hit")])
def test_disallowed_action_changes_nothing(status, action):
    s = fresh(); s["status"] = status; before = json.dumps(s)
    out = play(s, action, ["HK", "D5", "C9", "S7"])
    assert not out.changed and json.dumps(s) == before
    assert out.message == f"지금은 {LABELS[action]}을(를) 할 수 없습니다. (현재 상태: {status})"

def test_deal_without_chips():
    s = fresh(chips=0); out = play(s, "deal", ["HK", "D5", "C9", "S7"])
    assert not out.changed and out.message == "칩이 부족합니다. Reset을 눌러 주세요."

@pytest.mark.parametrize("status,chips,expected", [
    ("idle", 0, ["reset"]), ("idle", 100, ["deal", "reset"]), ("playing", 90, ["hit", "stand"]),
    ("finished", 50, ["deal", "reset"]), ("broke", 0, ["reset"])])
def test_allowed_actions(status, chips, expected):
    s = fresh(chips); s["status"] = status
    assert allowed_actions(s) == expected
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_game.py -v` → FAIL (import error)

- [ ] **Step 3: `blackjack/game.py` 구현** — 위 규칙대로. `apply_action`은 `action`별 내부 함수로 나누고, 판 종료는 `_finish(state, result, dealer_full)` 하나로 모은다. `reset`은 이 태스크에서 `NotImplementedError`로 둔다.

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 5: 커밋** — `git commit -m "feat: Deal·Hit·Stand와 정산"`

---

### Task 5: Reset과 하루 5회 제한

**Files:**
- Modify: `blackjack/game.py` (reset 처리)
- Test: `tests/test_reset.py`

**Interfaces:**
- Consumes: Task 4의 `apply_action`, `Outcome`; `state.KST`
- Produces: 추가 상수 `RESET_LIMIT = 5`, `MIN_CHIPS = 10`. `apply_action(..., "reset")`.

규칙(R5, R6, R11, R20, R21, R34):
1. `status == "playing"` → 거절(일반 "지금은 Reset을(를)…" 문구). 횟수·날짜 기록 그대로.
2. `today = now.astimezone(KST).date().isoformat()`. `reset_log["date"] != today`면 `{"date": today, "counts": {}}`로 비운다.
3. `key = actor.lower()`. `counts.get(key, 0) >= 5` → `Outcome(False, "오늘 Reset 횟수를 다 쓰셨습니다")`.
4. `fetch_contributions(state["owner"])`가 예외를 내면 → `Outcome(False, "기여 수를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")`, 횟수 차감 없음.
5. 성공: `commit_chips = c`, `current_chips = max(c, 10)`, `status = "idle"`, `result = None`, 손패 비움, `draw_index = 0`, `counts[key] += 1`. (`game_id`는 그대로 — Deal이 올린다.)

- [ ] **Step 1: 실패하는 테스트 작성**

`def reset(s, actor="octocat", now=KST_EVENING, fetch=lambda login: 345): return apply_action(s, "reset", actor=actor, now=now, deck_for=lambda g: full_deck(), fetch_contributions=fetch)`
`KST_EVENING = datetime(2026, 11, 8, 14, 59, tzinfo=timezone.utc)` (KST 11-08 23:59), `KST_MIDNIGHT = datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc)` (KST 11-09 00:00).

```python
def test_reset_sets_chips_from_contributions():
    s = initial_state(); out = reset(s)
    assert out.changed and out.message == "칩을 🪙 345개로 설정 (최근 1년 기여 345)"
    assert s["current_chips"] == 345 and s["commit_chips"] == 345 and s["status"] == "idle"

def test_reset_floor_is_10():
    s = initial_state(); out = reset(s, fetch=lambda login: 3)
    assert s["current_chips"] == 10 and s["commit_chips"] == 3
    assert out.message == "칩을 🪙 10개로 설정 (최근 1년 기여 3)"

def test_reset_queries_owner_not_actor():
    asked = []; s = initial_state()
    reset(s, actor="visitor", fetch=lambda login: asked.append(login) or 50)
    assert asked == ["how-to-song"]

def test_reset_from_finished_and_broke():
    for status in ("finished", "broke"):
        s = initial_state(); s["status"] = status; s["player_hand"] = ["HK"]
        assert reset(s).changed and s["status"] == "idle" and s["player_hand"] == []

def test_reset_blocked_while_playing_and_not_counted():
    s = initial_state(); s["status"] = "playing"
    out = reset(s)
    assert not out.changed and out.message == "지금은 Reset을(를) 할 수 없습니다. (현재 상태: playing)"
    assert s["reset_log"]["counts"] == {}

def test_sixth_reset_in_a_day_is_rejected():
    s = initial_state()
    for _ in range(5): assert reset(s).changed
    out = reset(s)
    assert not out.changed and out.message == "오늘 Reset 횟수를 다 쓰셨습니다"
    assert s["reset_log"] == {"date": "2026-11-08", "counts": {"octocat": 5}}

def test_limit_is_per_person():
    s = initial_state()
    for _ in range(5): reset(s)
    assert reset(s, actor="someone").changed

def test_reset_count_ignores_login_case():
    s = initial_state()
    for _ in range(5): reset(s, actor="Octocat")
    assert not reset(s, actor="octocat").changed

def test_count_resets_at_kst_midnight():
    s = initial_state()
    for _ in range(5): reset(s, now=KST_EVENING)
    assert not reset(s, now=KST_EVENING).changed
    assert reset(s, now=KST_MIDNIGHT).changed
    assert s["reset_log"] == {"date": "2026-11-09", "counts": {"octocat": 1}}

def test_fetch_failure_changes_nothing_and_is_not_counted():
    s = initial_state(); s["current_chips"] = 40; s["status"] = "finished"
    def boom(login): raise RuntimeError("api down")
    out = reset(s, fetch=boom)
    assert not out.changed and out.message == "기여 수를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
    assert s["current_chips"] == 40 and s["status"] == "finished"
    assert s["reset_log"]["counts"] == {}
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_reset.py -v` → FAIL (`NotImplementedError`)

- [ ] **Step 3: reset 처리 구현** — 위 규칙 1~5 순서 그대로.

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 5: 커밋** — `git commit -m "feat: Reset과 하루 5회 제한"`

---

### Task 6: README 게임판 렌더링

**Files:**
- Create: `blackjack/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `game.allowed_actions`, `game.RESULT_TEXT`, `cards.hand_value`
- Produces:
  - `MARK_START = "<!-- blackjack -->"`, `MARK_END = "<!-- /blackjack -->"`, `REPO = "how-to-song/how-to-song"`, `CARD_WIDTH = 70`
  - `class MarkerError(Exception)`
  - `render_board(state: dict) -> str` — 마커를 뺀 게임판 HTML. **빈 줄 없음**.
  - `replace_section(readme: str, board: str) -> str` — 결과는 `앞부분 + MARK_START + "\n" + board + "\n" + MARK_END + 뒷부분`. 각 마커가 정확히 1번이고 시작이 끝보다 앞이 아니면 `MarkerError`.
  - `action_url(action: str) -> str` — `https://github.com/how-to-song/how-to-song/issues/new?title=blackjack-<action>&body=<Issue 본문 문구를 urllib.parse.quote>`

게임판 순서(설계 8장, 허용 태그만: `div align`, `p`, `sub`, `h3`, `table`, `tr`, `th`, `td`, `img width`, `a`, `b`):
1. `<div align="center">`
2. 안내 문구 + `<br><sub>마지막 갱신: YYYY-MM-DD HH:MM KST</sub>` (`last_updated`가 None이면 `-`)
3. `finished`/`broke`이고 `result`가 있으면 `<h3 align="center">{RESULT_TEXT}</h3>`
4. 표 하나에 `Dealer` 줄과 `Player` 줄: 카드 칸(`<img src="assets/cards/SK.svg" width="70">`들), 합계 칸 `<b>…</b>`.
   - `playing`: 딜러 카드 뒤에 `back.svg` 1장, 딜러 합계 `?`.
   - 손패가 비었으면(idle) 양쪽 다 `back.svg` 2장, 합계 `-`.
5. `<p>🪙 보유 칩 <b>{current_chips}</b> · 베팅 <b>10</b></p>`. `idle`이면 그 아래 안내(칩 < 10이면 `Reset을 눌러 게임을 시작하세요`, 아니면 `Deal을 눌러 새 판을 시작하세요`).
6. 버튼 줄: `allowed_actions` 순서대로 `<a href="{action_url}"><img src="assets/buttons/{action}.svg" alt="{Label}"></a>`.
7. 기록 표: `<tr><th>행동</th><th>내용</th><th>플레이어</th></tr>` + 항목마다 `<td>{action}</td><td>{detail}</td><td><a href="https://github.com/{actor}">@{actor}</a></td>`. 비었으면 `<td colspan="3">아직 기록이 없습니다</td>`. `detail`·`actor`는 `html.escape`.
8. `</div>`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def playing_state():
    s = initial_state(); s.update(status="playing", current_chips=90, player_hand=["HK", "C9"], dealer_hand=["D5"])
    return s

def test_replace_keeps_outside_bytes():
    readme = "A\r\n<!-- blackjack -->\nold\n<!-- /blackjack -->\n\n<div>B</div>\n"
    out = replace_section(readme, "NEW")
    assert out == "A\r\n<!-- blackjack -->\nNEW\n<!-- /blackjack -->\n\n<div>B</div>\n"

@pytest.mark.parametrize("readme", [
    "no markers", "<!-- blackjack --> only start",
    "<!-- /blackjack --> x <!-- blackjack -->",
    "<!-- blackjack --><!-- /blackjack --><!-- blackjack --><!-- /blackjack -->"])
def test_bad_markers_raise(readme):
    with pytest.raises(MarkerError):
        replace_section(readme, "NEW")

@pytest.mark.parametrize("status", ["idle", "playing", "finished", "broke"])
def test_board_has_no_blank_lines(status):
    s = playing_state(); s["status"] = status
    assert all(line.strip() for line in render_board(s).splitlines())

def test_playing_board_hides_hole_card():
    html = render_board(playing_state())
    assert "assets/cards/D5.svg" in html and "assets/cards/back.svg" in html
    assert "<b>?</b>" in html and "<b>19</b>" in html
    assert "title=blackjack-hit" in html and "title=blackjack-stand" in html
    assert "title=blackjack-reset" not in html and "title=blackjack-deal" not in html

def test_initial_board_shows_only_reset():
    html = render_board(initial_state())
    assert "Reset을 눌러 게임을 시작하세요" in html
    assert "title=blackjack-reset" in html and "title=blackjack-deal" not in html
    assert "아직 기록이 없습니다" in html

def test_finished_board_shows_banner_and_full_dealer_hand():
    s = playing_state(); s.update(status="finished", result="player_blackjack", dealer_hand=["D5", "S7"])
    html = render_board(s)
    assert '<h3 align="center">블랙잭 승리!</h3>' in html
    assert "assets/cards/S7.svg" in html and "back.svg" not in html

def test_history_links_actor_and_escapes():
    s = initial_state()
    s["history"] = [{"issue": 3, "action": "Hit", "detail": "<b>x</b>", "actor": "octocat", "at": "2026-11-08T14:05:00+09:00"}]
    s["last_updated"] = "2026-11-08T14:05:00+09:00"
    html = render_board(s)
    assert '<a href="https://github.com/octocat">@octocat</a>' in html
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "마지막 갱신: 2026-11-08 14:05 KST" in html

def test_action_url_prefills_body():
    url = action_url("deal")
    assert url.startswith("https://github.com/how-to-song/how-to-song/issues/new?title=blackjack-deal&body=")
    assert " " not in url
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_render.py -v` → FAIL

- [ ] **Step 3: `blackjack/render.py` 구현** — 줄 리스트를 만들고 `"\n".join`. 빈 문자열 줄은 넣지 않는다. 마커 위치는 `str.find`/`count`로 찾고, 나머지 바이트는 손대지 않는다.

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 5: 커밋** — `git commit -m "feat: README 게임판 렌더링"`

---

### Task 7: GitHub API 클라이언트

**Files:**
- Create: `blackjack/github.py`
- Test: `tests/test_github.py`

**Interfaces:**
- Produces:
  - `BOT_LOGIN = "github-actions[bot]"`, `API = "https://api.github.com"`
  - `class GitHubError(Exception)`
  - `@dataclass(frozen=True) class Issue: number: int; title: str; author: str`
  - `class GitHubClient(token: str, repo: str)`, 메서드:
    - `_request(method: str, url: str, body: dict | None = None) -> tuple[object, dict[str, str]]` — JSON 응답(본문 없으면 `None`)과 응답 헤더. 헤더: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`, `User-Agent: how-to-song-blackjack`. `urllib.error.URLError`/`HTTPError` → `GitHubError`(메시지에 토큰 넣지 않음).
    - `list_open_game_issues() -> list[Issue]` — `GET {API}/repos/{repo}/issues?state=open&per_page=100`, `Link` 헤더의 `rel="next"`를 끝까지 따른다. `pull_request` 키가 있는 항목 제외. 제목을 `strip().lower()`해서 `blackjack-`으로 시작하는 것만. 번호 오름차순.
    - `has_bot_comment(number: int) -> bool` — `GET …/issues/{n}/comments?per_page=100`, `user.login == BOT_LOGIN`이 하나라도 있으면 True.
    - `comment(number: int, body: str) -> None` — `POST …/issues/{n}/comments` `{"body": body}`
    - `close(number: int) -> None` — `PATCH …/issues/{n}` `{"state": "closed", "state_reason": "completed"}`
    - `lock(number: int) -> None` — `PUT …/issues/{n}/lock` `{"lock_reason": "resolved"}`
    - `total_contributions(login: str) -> int` — `POST {API}/graphql`, 쿼리는 설계 7장 그대로(`$login` 변수). `errors`가 있거나 `user`가 null이면 `GitHubError`.

- [ ] **Step 1: 실패하는 테스트 작성** — `_request`를 덮어쓰는 테스트용 하위 클래스로 응답을 흉내낸다.

```python
class Scripted(GitHubClient):
    def __init__(self, responses):
        super().__init__("tok", "how-to-song/how-to-song"); self.responses = responses; self.calls = []
    def _request(self, method, url, body=None):
        self.calls.append((method, url, body)); return self.responses.pop(0)

def item(n, title, pr=False):
    d = {"number": n, "title": title, "user": {"login": "octocat"}}
    if pr: d["pull_request"] = {}
    return d

def test_list_filters_and_sorts():
    gh = Scripted([([item(9, " Blackjack-HIT "), item(3, "blackjack-deal"), item(5, "bug report"),
                     item(4, "blackjack-stand", pr=True)], {})])
    assert gh.list_open_game_issues() == [Issue(3, "blackjack-deal", "octocat"), Issue(9, " Blackjack-HIT ", "octocat")]

def test_list_follows_pagination():
    nxt = '<https://api.github.com/repositories/1/issues?page=2>; rel="next", <…>; rel="last"'
    gh = Scripted([([item(1, "blackjack-deal")], {"Link": nxt}), ([item(2, "blackjack-hit")], {})])
    assert [i.number for i in gh.list_open_game_issues()] == [1, 2]
    assert gh.calls[1][1] == "https://api.github.com/repositories/1/issues?page=2"

def test_has_bot_comment():
    gh = Scripted([([{"user": {"login": "octocat"}}, {"user": {"login": "github-actions[bot]"}}], {})])
    assert gh.has_bot_comment(7) is True

def test_close_and_lock_requests():
    gh = Scripted([(None, {}), (None, {})])
    gh.close(7); gh.lock(7)
    assert gh.calls[0] == ("PATCH", "https://api.github.com/repos/how-to-song/how-to-song/issues/7",
                           {"state": "closed", "state_reason": "completed"})
    assert gh.calls[1] == ("PUT", "https://api.github.com/repos/how-to-song/how-to-song/issues/7/lock",
                           {"lock_reason": "resolved"})

def test_total_contributions():
    data = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"totalContributions": 345}}}}}
    gh = Scripted([(data, {})])
    assert gh.total_contributions("how-to-song") == 345
    assert gh.calls[0][2]["variables"] == {"login": "how-to-song"}

def test_total_contributions_errors_raise():
    gh = Scripted([({"data": {"user": None}}, {}), ({"errors": [{"message": "x"}]}, {})])
    with pytest.raises(GitHubError): gh.total_contributions("how-to-song")
    with pytest.raises(GitHubError): gh.total_contributions("how-to-song")
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_github.py -v` → FAIL

- [ ] **Step 3: `blackjack/github.py` 구현** — `Link` 헤더는 `,`로 나누고 `rel="next"`인 조각의 `<…>` 안을 꺼낸다. `_request`는 `urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method, headers=…)` + `urlopen(timeout=30)`.

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 5: 커밋** — `git commit -m "feat: GitHub API 클라이언트"`

---

### Task 8: Issue 처리 흐름과 진입점

**Files:**
- Create: `blackjack/main.py`, `tests/fakes.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `state.*`, `game.apply_action`, `game.LABELS`, `deck.shuffled_deck`, `render.render_board`, `render.replace_section`, `render.MarkerError`, `github.GitHubClient`, `github.Issue`
- Produces:
  - `parse_action(title: str) -> str` — `strip().lower()`가 `blackjack-<action>`이고 action이 `ACTIONS`에 있으면 그 action, 아니면 `"unknown"`.
  - `@dataclass class Reply: number: int; message: str; already_processed: bool`
  - `handle_issues(state, issues: list[Issue], *, now, deck_for, fetch_contributions) -> list[Reply]` — 번호순으로:
    - `number <= last_processed_issue`: 행동 적용 안 함. `find_history`의 `detail`이 있으면 그것, 없으면 `이미 처리된 요청입니다.` → `Reply(…, already_processed=True)`.
    - 새 Issue: `unknown`이면 `알 수 없는 행동입니다. README의 버튼을 눌러 주세요.`, 아니면 `apply_action`. `changed`면 `add_history(issue=n, action=LABELS[a], detail=out.message, actor=issue.author, now=now)`. 어느 경우든 `last_processed_issue = n`, `last_updated = kst_iso(now)`.
  - `finalize(gh, replies: list[Reply]) -> int` — Issue마다 (`already_processed`이고 `gh.has_bot_comment(n)`이면 댓글 생략) 댓글 → `close` → `lock`. Issue 하나의 실패(`GitHubError`)는 출력하고 다음 Issue로 넘어간다. 실패한 Issue 수를 돌려준다.
  - `git_commit_and_push(paths: list[Path], message: str) -> None` — `git add <paths>` → `git diff --cached --quiet`가 0이면 그냥 끝 → `git -c user.name=github-actions[bot] -c user.email=41898282+github-actions[bot]@users.noreply.github.com commit -m <message>` → `git pull --rebase` → `git push`. 모두 `check=True`.
  - `run(*, gh, secret: str, now: datetime, state_path: Path, readme_path: Path, push: Callable[[list[Path], str], None]) -> int`:
    1. 상태 읽기, `issues = gh.list_open_game_issues()`
    2. `replies = handle_issues(…, deck_for=lambda gid: shuffled_deck(secret, gid), fetch_contributions=gh.total_contributions)`
    3. README 읽기(`newline=""`로 원래 줄바꿈 유지) → `replace_section(readme, render_board(state))`. `MarkerError`면 출력 후 **아무것도 쓰지 않고** `return 1`.
    4. 상태 JSON(`dump_state`)과 README가 디스크 내용과 다를 때만 쓴다(README는 `newline=""`로 써서 줄바꿈을 그대로 둔다). 쓴 파일이 있으면 `push(written, message)`. 메시지: Issue가 있으면 `blackjack: Issue #{첫 번호}~#{끝 번호} 처리`(1개면 `#{n}`), 없으면 `blackjack: 게임판 갱신`. 카드 정보는 넣지 않는다. push 예외 → 출력 후 `return 1`(댓글 없음).
    5. `return 1 if finalize(gh, replies) else 0`
  - `main() -> int` — 환경 변수 `GITHUB_TOKEN`, `BLACKJACK_SECRET`, `GITHUB_REPOSITORY`(기본 `how-to-song/how-to-song`). 토큰이나 Secret이 비어 있으면 `BLACKJACK_SECRET이 설정되지 않았습니다` 같은 안내를 출력하고 `return 1`. 그 밖엔 `run(gh=GitHubClient(...), now=datetime.now(timezone.utc), state_path=STATE_PATH, readme_path=Path("README.md"), push=git_commit_and_push)`. 파일 끝에 `if __name__ == "__main__": sys.exit(main())`.
- `tests/fakes.py`: `FakeGitHub(issues: list[Issue], contributions: int | Exception = 345, bot_commented: set[int] = ∅, fail_close: set[int] = ∅)` — `list_open_game_issues`, `has_bot_comment`, `comment`(→ `self.comments: dict[int, list[str]]`), `close`(→ `self.closed`, `fail_close`면 `GitHubError`), `lock`(→ `self.locked`), `total_contributions`(예외면 raise).

- [ ] **Step 1: 실패하는 테스트 작성**

공통 픽스처 `files`는 `SimpleNamespace(sp, rp, pushes, go)`를 돌려준다. 아래 테스트의 `sp`, `rp`, `pushes`, `go`는 `files.sp` 등을 줄여 쓴 것이다.
- `rp = tmp_path/"README.md"`, 내용 `"<!-- blackjack -->\n<!-- /blackjack -->\n\n<div>profile</div>\n"`
- `sp = tmp_path/"state.json"` (만들지 않음)
- `pushes = []`, 기본 push는 `lambda paths, msg: pushes.append((paths, msg))`
- `NOW = datetime(2026, 11, 8, 5, 5, tzinfo=timezone.utc)`
- `go(gh, push=<기본>) -> int` = `run(gh=gh, secret="s", now=NOW, state_path=sp, readme_path=rp, push=push)`

```python
def test_parse_action():
    assert parse_action(" Blackjack-HIT ") == "hit"
    assert parse_action("blackjack-hit please") == "unknown"
    assert parse_action("blackjack-split") == "unknown"

def test_processes_issues_in_order(files):
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a"), Issue(6, "blackjack-deal", "b"), Issue(7, "blackjack-foo", "c")])
    assert go(gh) == 0
    s = load_state(sp)
    assert s["last_processed_issue"] == 7 and [h["issue"] for h in s["history"]] == [6, 5]
    assert s["game_id"] == 1 and s["history"][0]["action"] == "Deal"   # 첫 판이 블랙잭일 수도 있어 status는 보지 않는다
    assert gh.closed == {5, 6, 7} and gh.locked == {5, 6, 7}
    assert gh.comments[7] == ["알 수 없는 행동입니다. README의 버튼을 눌러 주세요."]
    assert len(pushes) == 1 and pushes[0][1] == "blackjack: Issue #5~#7 처리"
    assert "<div>profile</div>" in rp.read_text(encoding="utf-8")

def test_rejected_action_is_commented_but_not_in_history(files):
    gh = FakeGitHub([Issue(5, "blackjack-hit", "a")])
    go(gh)
    assert gh.comments[5] == ["지금은 Hit을(를) 할 수 없습니다. (현재 상태: idle)"]
    assert load_state(sp)["history"] == [] and load_state(sp)["last_processed_issue"] == 5

def test_already_processed_issue_is_not_reapplied(files):
    s = initial_state(); s["last_processed_issue"] = 10
    add_history(s, issue=10, action="Reset", detail="이전 결과", actor="a", now=NOW); save_state(s, sp)
    go(FakeGitHub([]))                         # README 게임판을 한 번 그려 둔다
    pushes.clear()
    gh = FakeGitHub([Issue(10, "blackjack-reset", "a")])
    assert go(gh) == 0
    assert gh.comments[10] == ["이전 결과"] and gh.closed == {10}
    assert pushes == [] and load_state(sp)["reset_log"]["counts"] == {}

def test_already_processed_with_bot_comment_only_closes(files):
    s = initial_state(); s["last_processed_issue"] = 10; save_state(s, sp)
    gh = FakeGitHub([Issue(10, "blackjack-deal", "a")], bot_commented={10})
    go(gh)
    assert 10 not in gh.comments and gh.closed == {10} and gh.locked == {10}

def test_missing_marker_changes_nothing(files):
    rp.write_text("<div>profile</div>\n", encoding="utf-8")
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a")])
    assert go(gh) == 1
    assert not sp.exists() and rp.read_text(encoding="utf-8") == "<div>profile</div>\n"
    assert pushes == [] and gh.comments == {} and gh.closed == set()

def test_push_failure_leaves_issues_open(files):
    def bad_push(paths, msg): raise subprocess.CalledProcessError(1, "git push")
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a")])
    assert go(gh, push=bad_push) == 1
    assert gh.comments == {} and gh.closed == set()

def test_idle_run_does_not_push(files):
    go(FakeGitHub([]))            # 첫 실행: 초기 상태와 게임판을 만든다
    assert len(pushes) == 1 and pushes[0][1] == "blackjack: 게임판 갱신"
    go(FakeGitHub([]))
    assert len(pushes) == 1

def test_one_close_failure_does_not_block_others(files):
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a"), Issue(6, "blackjack-deal", "a")], fail_close={5})
    assert go(gh) == 1
    assert gh.closed == {6}

def test_state_file_never_contains_hole_card(files):
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a"), Issue(6, "blackjack-deal", "a")])
    go(gh)
    hole = shuffled_deck("s", 1)[3]
    s = load_state(sp)
    if s["status"] == "playing":
        assert hole not in sp.read_text(encoding="utf-8")
        assert f"assets/cards/{hole}.svg" not in rp.read_text(encoding="utf-8")

def test_main_requires_secret(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t"); monkeypatch.delenv("BLACKJACK_SECRET", raising=False)
    assert main() == 1
```

(`files` 픽스처가 `sp`, `rp`, `pushes`를 준비한다. `test_state_file_never_contains_hole_card`는 Secret `"s"`의 1번 판이 블랙잭이면 판이 이미 끝나 숨긴 카드가 공개되므로 `playing`일 때만 확인한다.)

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_main.py -v` → FAIL

- [ ] **Step 3: `tests/fakes.py`와 `blackjack/main.py` 구현**

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 5: 커밋** — `git commit -m "feat: Issue 처리 흐름과 진입점"`

---

### Task 9: 카드·버튼 이미지와 README 마커

**Files:**
- Create: `assets/cards/*.svg`(52장 + `back.svg`), `assets/cards/LICENSE.md`, `assets/buttons/{deal,hit,stand,reset}.svg`
- Modify: `README.md:1` (맨 위에 마커)
- Test: `tests/test_assets.py`

**Interfaces:**
- Consumes: `cards.full_deck()`, `render.MARK_START`, `render.MARK_END`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
ROOT = Path(__file__).resolve().parent.parent

def test_every_card_has_an_image():
    missing = [c for c in full_deck() + ["back"] if not (ROOT / "assets/cards" / f"{c}.svg").exists()]
    assert missing == []

def test_card_license_recorded():
    text = (ROOT / "assets/cards/LICENSE.md").read_text(encoding="utf-8")
    assert "출처" in text and "라이선스" in text

def test_buttons_exist():
    for a in ("deal", "hit", "stand", "reset"):
        assert (ROOT / "assets/buttons" / f"{a}.svg").exists()

def test_readme_has_markers_at_top():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert text.startswith(MARK_START + "\n" + MARK_END + "\n\n<div align=\"center\">")
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_assets.py -v` → 4 FAIL

- [ ] **Step 3: 카드 세트 고르기 — 소유자 확인 필요**

후보(구현 시 라이선스를 직접 확인):
1. Byron Knoll의 "Vector Playing Cards" — 퍼블릭 도메인으로 배포됨.
2. Wikimedia Commons의 Dmitry Fomin 카드 세트 — CC0로 표시됨.

라이선스 페이지를 확인한 뒤, **어느 세트를 어디서 내려받을지(URL, 대략 용량) 소유자에게 보여주고 승인받은 다음** 내려받는다. 내려받은 파일은 스크래치 폴더의 새 빈 폴더에 두고, 이름을 카드 표기로 바꿔(`S`=spades, `H`=hearts, `D`=diamonds, `C`=clubs; `A, 2~10, J, Q, K`) `assets/cards/`로 복사한다. 뒷면이 없는 세트면 `back.svg`는 직접 만든다(단색 무늬, 같은 비율). `LICENSE.md`에 `출처:` URL, `라이선스:` 이름과 원문 링크, 바꾼 점(파일 이름)을 적는다.

- [ ] **Step 4: 버튼 SVG 직접 작성** — 4개 모두 `width="120" height="40"`, 둥근 사각형(`rx="8"`) + 가운데 굵은 글자, `font-family="Segoe UI, Helvetica, Arial, sans-serif"`. 색: Deal `#2da44e`, Hit `#0969da`, Stand `#cf222e`, Reset `#6e7781`, 글자 흰색. 글자: `🃏 DEAL`, `👆 HIT`, `✋ STAND`, `🔄 RESET`. 외부 폰트·스크립트·링크 없음.

- [ ] **Step 5: README 맨 위에 마커 추가** — 기존 첫 줄 `<div align="center">` 앞에 `<!-- blackjack -->\n<!-- /blackjack -->\n\n`. 나머지 내용은 한 글자도 바꾸지 않는다. 확인: `git diff README.md`가 추가 3줄만 보여야 한다.

- [ ] **Step 6: 통과 확인** — Run: `python -m pytest -v` → all passed

- [ ] **Step 7: 미리보기 확인** — `tmp`에 README 복사본을 두고 `run()`을 Fake로 한 번 돌려 게임판을 그린 뒤, `gh api markdown -f text=@<파일> -f mode=gfm`로 GitHub 렌더링 HTML을 받아 브라우저 창에서 열어 본다. 카드가 한 줄에 나란히 보이고 버튼이 이미지로 보이면 통과(상대 경로 이미지는 로컬 미리보기에서 깨질 수 있으므로 `assets/` 경로를 파일 절대 경로로 바꿔서 본다).

- [ ] **Step 8: 커밋** — `git add assets README.md tests/test_assets.py` → `git commit -m "feat: 카드·버튼 이미지와 README 게임 구간"`

---

### Task 10: 게임 워크플로와 배포

**Files:**
- Create: `.github/workflows/blackjack.yml`
- Test: 없음(설정 파일). 실제 동작 확인으로 검증.

- [ ] **Step 1: 워크플로 작성**

```yaml
name: Blackjack
on:
  issues:
    types: [opened]
  workflow_dispatch:
  schedule:
    - cron: "17 * * * *"
permissions:
  contents: write
  issues: write
concurrency:
  group: blackjack
  cancel-in-progress: false
jobs:
  play:
    if: github.event_name != 'issues' || startsWith(github.event.issue.title, 'blackjack-')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m blackjack.main
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BLACKJACK_SECRET: ${{ secrets.BLACKJACK_SECRET }}
```
(`startsWith`는 대소문자를 구분하지 않으므로 `Blackjack-Hit`도 실행된다. 앞 공백이 있는 제목은 다음 정기 실행이 처리한다.)

- [ ] **Step 2: 전체 테스트** — Run: `python -m pytest -v` → all passed

- [ ] **Step 3: 커밋 후 브랜치 push, PR 생성** — `git commit -m "feat: 블랙잭 게임 워크플로"` → `git push -u origin feat/blackjack-game` → `gh pr create`. PR 본문에 소유자 할 일(아래)을 적는다. CI(pytest)가 통과하는지 확인.

- [ ] **Step 4: 소유자 할 일 안내 후 대기** — (1) 저장소 Secret `BLACKJACK_SECRET` 등록(긴 무작위 문자열), (2) PR 머지 승인. **머지는 소유자 승인 후.**

- [ ] **Step 5: 첫 게임판 그리기** — 머지 후 소유자 승인을 받아 `gh workflow run blackjack.yml` → 실행 성공, `main`에 `blackjack: 게임판 갱신` 커밋, 프로필에 "Reset을 눌러 게임을 시작하세요"와 Reset 버튼이 보인다.

- [ ] **Step 6: 실제 동작 확인(소유자)** — Reset → Deal → Hit → Stand 순서로 Issue 제출. 각 Issue에 결과 댓글·닫힘·잠김, README 갱신 확인. Reset 기여 수가 프로필 잔디 숫자와 같은지 비교. 같은 날 Reset 6번째가 거절되는지 확인. 확인용 Issue 생성은 소유자가 직접 하거나, Claude가 만들 때는 매번 승인받는다.
