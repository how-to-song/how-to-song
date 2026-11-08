# 설계

요구사항 번호(R1…)는 [requirements.md](requirements.md)를 따른다. **[Claude 결정]** 표시는 사용자가 아니라 Claude가 정한 것이다.

## 1. 전체 구조
```text
방문자: README 버튼 클릭 → 미리 채워진 Issue 제출
   ↓ (issues: opened)
GitHub Actions: blackjack.yml
   ↓
python -m blackjack.main
   1) 열린 blackjack-* Issue를 번호 오름차순으로 모두 가져온다
   2) 상태 파일을 읽고 Issue마다 행동을 적용한다
   3) 상태 파일 + README 게임 구간을 쓴다
   4) 커밋하고 push한다
   5) Issue마다 결과 댓글 → Close → Lock
```
- 언어: Python 3.12. 게임 코드는 표준 라이브러리만 사용, 테스트는 pytest. [Claude 결정: 사용자가 Python을 알고, Actions에 기본 설치되어 있어 빌드가 필요 없음]
- 서버 없음. 저장소 파일과 Actions만 사용한다.

## 2. 저장소 구성
```text
.github/
  workflows/blackjack.yml   # 게임 워크플로
  workflows/ci.yml          # push/PR 시 pytest
  blackjack_state.json      # 게임 상태
blackjack/
  cards.py      # 카드 표기, 점수 계산(soft/hard)
  deck.py       # 비밀값 기반 셔플
  game.py       # 행동 적용, 판정, 정산, Reset 제한
  state.py      # 상태 파일 읽기/쓰기, 초기 상태
  render.py     # README 게임 구간 HTML 생성, 마커 사이 치환
  github.py     # GitHub API (GraphQL 기여 수, Issue 목록/댓글/닫기/잠금)
  main.py       # 진입점, Issue 처리 순서와 커밋 흐름
assets/
  cards/        # 52장 + back.svg + 라이선스 파일
  buttons/      # deal.svg, hit.svg, stand.svg, reset.svg
tests/
README.md       # 기존 프로필 + <!-- blackjack --> 구간
.gitignore      # .superpowers/ 포함
```
[Claude 결정: 파일 구성 전체]

## 3. 워크플로 (`blackjack.yml`)
- 트리거: `issues: [opened]`, 수동 복구용 `workflow_dispatch`, 남은 Issue 정리용 `schedule`(1시간마다). 마지막 실행이 실패해도 다음 Issue를 기다리지 않고 열린 Issue를 다시 처리하기 위해서다. [Claude 결정: 검토 반영]
- 권한: `contents: write`, `issues: write`.
- 동시 실행: `concurrency: { group: blackjack, cancel-in-progress: false }`.
- 단계: checkout → setup-python 3.12 → `python -m blackjack.main` → 바뀐 파일이 있으면 커밋 후 push → (main이) 댓글·닫기·잠금.
- 환경 변수: `GITHUB_TOKEN`(기본 토큰), `BLACKJACK_SECRET`(저장소 Secret).
- 커밋 작성자는 `github-actions[bot]`. `GITHUB_TOKEN`으로 한 push는 워크플로를 다시 트리거하지 않으므로 무한 반복이 없다.

### 왜 "열린 Issue를 모두 처리"하는가 (R33)
GitHub의 `concurrency`는 실행 중 1개 + 대기 1개만 유지하고, 더 오래된 대기 실행은 취소한다. 그래서 Issue가 빠르게 3개 이상 들어오면 일부 실행이 취소된다. 각 실행이 **자기 Issue만이 아니라 열린 `blackjack-*` Issue 전체를 번호 순서대로** 처리하면, 취소된 실행의 Issue도 다음 실행이 처리한다. [Claude 결정]

### 처리 순서와 중복 방지
1. 상태 변경 → 상태 파일·README 커밋 → push 성공 후에 댓글·닫기·잠금.
   push가 실패하면 Issue는 열린 채로 남고, 다음 실행이나 수동 실행이 다시 처리한다.
2. 상태 파일의 `last_processed_issue`보다 번호가 작거나 같은 Issue는 이미 반영된 것이다. 이런 Issue에는 행동을 다시 적용하지 않는다. push 뒤 댓글·닫기 단계에서 실패해도 같은 행동이 두 번 적용되지 않는다.
   - 봇 댓글이 아직 없으면, `history`에서 그 Issue 번호의 결과 문구를 찾아 댓글로 단 뒤 닫고 잠근다. 결과를 못 찾으면 "이미 처리된 요청입니다" 댓글을 단다. 이를 위해 `history` 항목에 `issue` 번호를 함께 저장한다. [Claude 결정: 검토 반영]
   - 이미 반영된 번호인데 늦게 보이거나 다시 열린 Issue도 같은 방식으로 처리한다.
3. push 전에 `git pull --rebase`를 한다. 소유자가 직접 README를 고쳐 push한 경우를 대비한다.

### Issue 분류 (R2, R4)
- 제목을 앞뒤 공백 제거 + 소문자로 비교한다.
- `blackjack-deal|hit|stand|reset` → 행동 처리.
- `blackjack-`으로 시작하지만 그 밖의 제목 → "알 수 없는 행동" 댓글 후 닫기. [Claude 결정]
- 그 밖의 Issue → 목록에서 제외, 건드리지 않음.

## 4. 상태 파일 (`.github/blackjack_state.json`)
```json
{
  "version": 1,
  "owner": "how-to-song",
  "commit_chips": 345,
  "current_chips": 230,
  "bet": 10,
  "status": "playing",
  "result": null,
  "game_id": 12,
  "draw_index": 5,
  "player_hand": ["HK", "D5", "C3"],
  "dealer_hand": ["CA"],
  "reset_log": { "date": "2026-11-08", "counts": { "octocat": 2 } },
  "history": [
    { "issue": 42, "action": "Hit", "detail": "C3 받음 · 합계 18", "actor": "octocat", "at": "2026-11-08T14:05:00+09:00" }
  ],
  "last_processed_issue": 42,
  "last_updated": "2026-11-08T14:05:00+09:00"
}
```
- 원본 기획서의 `deck` 필드는 **두지 않는다**. 덱을 공개하지 않기 위해서다(R19, 5장).
- `player_name` 대신 `owner`(칩 기준 계정)를 둔다.
- `status`: `idle` / `playing` / `finished` / `broke`.
- `result`: `player_blackjack` / `player_win` / `dealer_bust` / `dealer_win` / `player_bust` / `push` / `null`.
- `dealer_hand`: `playing` 동안은 **앞면 카드 1장만** 저장한다. 판이 끝나면 전체를 저장한다.
- `reset_log`: 오늘(KST) 날짜와 사람별 Reset 횟수만 남긴다. 날짜가 바뀌면 비운다.
- `history`: 최근 10개만 남긴다. [Claude 결정: 10개]
- 카드 표기: 무늬 `S/H/D/C` + 숫자 `A, 2~10, J, Q, K`. 예: `CA`, `D10`, `SK`.
- 초기 상태: `status: idle`, `current_chips: 0`. Deal은 칩 10 이상일 때만 보이므로 처음에는 Reset만 보인다. 화면에는 "Reset을 눌러 게임을 시작하세요"를 표시한다. [Claude 결정]

## 5. 덱 비공개 (R19)
- 셔플 시드 = `HMAC-SHA256(BLACKJACK_SECRET, "game:{game_id}")`. 이 시드로 `random.Random(seed).shuffle()`한 52장 덱을 매번 다시 계산한다.
- 상태 파일에는 `game_id`와 `draw_index`(지금까지 뽑은 장수)만 저장한다.
- 분배 순서는 플레이어 → 딜러 → 플레이어 → 딜러(숨긴 카드 = 덱 4번째 카드)로 고정한다. 숨긴 카드는 필요할 때 덱에서 다시 계산한다.
- Deal마다 `game_id`를 1 늘린다. 판마다 덱이 달라지고, 지난 판의 공개된 카드로 다음 판을 알 수 없다.
- 로그, Issue 댓글, 커밋 메시지에 남은 덱이나 숨긴 카드를 출력하지 않는다.
- `BLACKJACK_SECRET`은 소유자가 저장소 Secret으로 직접 등록한다. Secret이 없으면 워크플로는 아무것도 바꾸지 않고 실패한다.
[Claude 결정: 방식 전체. 사용자에게 제안했고 반대 의견은 없었음]

## 6. 행동 처리 (game.py)
- **Deal:** 상태가 `idle`/`finished`이고 칩이 10 이상이어야 한다. `game_id += 1`, 칩 −10, 덱에서 4장을 나눈다. 블랙잭을 즉시 확인한다(R16). 블랙잭이 아니면 `playing`.
- **Hit:** 상태가 `playing`이어야 한다. 1장을 받고, 21을 넘으면 `player_bust`로 판이 끝난다.
- **Stand:** 상태가 `playing`이어야 한다. 숨긴 카드를 공개하고, 딜러가 합계 17 이상(S17)이 될 때까지 뽑은 뒤 판정한다.
- **Reset:** `idle`/`finished`/`broke`에서만 가능하다(`playing`이면 거절, 횟수 차감 없음). 먼저 오늘 이 사람의 횟수를 확인하고(이미 5회면 거절), 기여 수를 조회한다(실패하면 거절, 횟수 차감 없음). 그다음 칩을 설정하고 `idle`로 바꾼 뒤 횟수 +1.
- **판 종료 정산(R18):** 블랙잭 +25, 승리(딜러 버스트 포함) +20, push +10, 패배 0. 정산 후 칩이 10 미만이면 `broke`.
- 할 수 없는 행동은 상태를 그대로 두고 안내 문구를 돌려준다(R13).
- 모든 행동은 결과 문구를 돌려주고, 이 문구가 Issue 댓글과 `history`에 쓰인다.

## 7. GitHub API (github.py)
- **기여 수:** GraphQL `user(login: "how-to-song") { contributionsCollection { contributionCalendar { totalContributions } } }`. `GITHUB_TOKEN`으로 호출한다.
  - 기준은 **방문자가 프로필에서 보는 잔디 숫자**다. 기본 토큰은 다른 방문자와 같은 공개 달력을 본다. 소유자가 "비공개 기여 포함"을 켜 두었다면 비공개 기여도 익명 숫자로 포함되므로, 프로필 숫자와 일치해야 한다. 그래서 개인 토큰(PAT)은 쓰지 않는다. PAT를 쓰면 오히려 프로필보다 큰 숫자가 나올 수 있다. 구현 후 실제 값을 프로필과 한 번 비교한다. [Claude 결정: 검토 반영]
- **Issue:** REST로 열린 Issue 목록을 가져와 Pull Request를 제외하고, 댓글 작성, 닫기(`state: closed`), 잠금(`lock_reason: resolved`)을 한다.
- HTTP는 `urllib.request`로 호출한다.
- 테스트에서는 같은 인터페이스를 가진 가짜 클라이언트로 바꿔 쓸 수 있게 한다.

## 8. README 렌더링 (render.py)
- `<!-- blackjack -->`와 `<!-- /blackjack -->` 사이만 치환한다. 마커가 없거나 짝이 맞지 않으면 README를 건드리지 않고 실패한다(R24).
- GitHub README가 허용하는 HTML만 사용한다: `table`, `img`(`width`), `a`, `h3`, `b`, `div align`. CSS와 JS는 사용하지 않는다.
- 구간 전체를 `<details open>` + `<summary><b>🎮 게임판 열기/닫기</b></summary>`로 감싸 방문자가 접고 펼 수 있게 한다. 버튼을 누르고 새로고침했을 때 다시 펼칠 필요가 없도록 기본은 펼침이다. [사용자 요청, 기본값은 Claude 결정]
- 구간 안의 순서:
  1. 안내 문구 + 마지막 갱신 시각(KST)
  2. 결과 배너(판이 끝났을 때, `h3 align="center"`)
  3. Dealer 표: 카드 이미지 칸, 합계 칸. `playing`이면 두 번째 칸은 `back.svg`, 합계는 `?`.
  4. Player 표: 카드 이미지 칸, 합계 칸
  5. 🪙 보유 칩 · 베팅 10
  6. 버튼 줄: 지금 가능한 행동만 보인다(R28). 각 버튼은 `<a href="https://github.com/how-to-song/how-to-song/issues/new?title=blackjack-hit&body=...">` 안에 `assets/buttons/*.svg`를 넣는다.
  7. 행동 기록 표: 행동 | 내용 | 행동한 사람(`https://github.com/<login>` 링크)
- 이미지는 저장소 상대 경로(`assets/cards/SK.svg`)로 넣는다.
- 생성하는 HTML 블록 안에는 빈 줄을 넣지 않는다. 빈 줄이 있으면 GitHub가 HTML 블록을 끊고 Markdown으로 해석한다.
- GitHub 기본 표 테두리와 줄무늬는 CSS 없이 없앨 수 없다. 이 한계 안에서 카드 이미지 크기와 배치로 시각 효과를 낸다.
- 버튼은 외부 배지 서비스(shields.io)가 아닌 저장소 안 SVG를 쓴다. 외부 의존을 없애기 위해서다. [Claude 결정]

## 9. 카드 이미지 (R32)
- 퍼블릭 도메인 또는 CC0 SVG 카드 세트를 `assets/cards/`에 넣고, 출처와 라이선스 파일을 함께 둔다.
- 파일 이름은 카드 표기와 같게 한다(`SK.svg`, `D10.svg`, `back.svg`).
- 어떤 세트를 쓸지는 구현할 때 라이선스를 확인해서 고른다. [Claude 결정: 세트 선택은 구현자에게 맡김]

## 10. 기존 README와의 결합
- 기존 프로필 내용은 그대로 둔다. 게임 구간 마커를 처음 한 번 넣는다.
- 위치: README **맨 아래**. 템플릿 안내 `<!-- ... -->` 주석이 끝난 뒤에 `---`, `## 🃏 Blackjack` 제목, 빈 줄, 마커 구간 순서로 둔다. 기존 `<div>` 안쪽이나 템플릿 주석 안에는 넣지 않는다. (2026-11-08 맨 위 → 맨 아래로 변경) [사용자]
- Projects 절에 `### [GitHub Blackjack](https://github.com/how-to-song/how-to-song/tree/main/blackjack) - …` 한 줄 소개를 둔다. [사용자]
- 마커 구간과 기존 내용 사이에 빈 줄을 하나 둔다. 그래야 두 HTML 블록이 서로 섞이지 않는다.

## 11. 테스트
- **cards:** soft/hard Ace 조합, 블랙잭 판별.
- **deck:** 같은 Secret과 `game_id`면 같은 덱, 다르면 다른 덱. 상태 파일에 숨긴 카드가 없는지 확인.
- **game:** 상태별 허용·거절(판 중 Reset 거절 포함), 정산 금액, 파산 전이, S17, 블랙잭 즉시 판정 3가지.
- **Reset 제한:** 5회까지 허용하고 6회째 거절. KST 자정에 횟수 초기화(UTC 14:59와 15:00 경계). 조회 실패 시 횟수 미차감.
- **render:** 마커 밖 내용이 바이트 단위로 그대로인지, 상태별로 보이는 버튼(`playing`에서는 Reset 버튼 숨김), 숨긴 카드가 뒷면으로 나오는지, 생성 HTML에 빈 줄이 없는지.
- **main:** 가짜 GitHub 클라이언트로 여러 Issue를 순서대로 처리하는지, `last_processed_issue` 중복 방지, 알 수 없는 제목 처리.
- **실제 동작:** push 후 소유자가 Issue를 만들어 직접 확인한다(Deal → Hit → Stand, Reset 6회).

## 12. 소유자가 직접 할 일
- 저장소 Secret `BLACKJACK_SECRET` 등록(긴 무작위 문자열).
- 구현 결과 커밋과 push.
- (선택) 방문자 행동마다 Issue 알림이 오므로, 원하면 저장소 Watch 설정을 Custom으로 바꾼다.
- 참고: 2026-11-08 기준 `main` 브랜치는 보호 규칙이 없어 봇이 push할 수 있다. 나중에 보호 규칙을 켜면 봇 push가 막힌다.
