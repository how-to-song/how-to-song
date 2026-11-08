# CLAUDE.md

GitHub 프로필 저장소(`how-to-song/how-to-song`)의 README에서 방문자 누구나 Issue 링크로 하나의 공유 판을 이어서 플레이하는 블랙잭 게임.

## 문서
- 개요: [docs/overview.md](docs/overview.md) · 요구사항: [docs/requirements.md](docs/requirements.md) · 설계: [docs/architecture.md](docs/architecture.md)
- 설계 문서가 원본 기획서(`D:\How_Vault\10.PROJECT\github_blackjack\GitHub Blackjack.md`)보다 우선한다. 기획서와 다르면 설계 문서를 따른다.
- 요구사항 번호(R1…)로 서로 참조한다. 설계를 바꾸면 해당 문서도 함께 고친다.

## 기술 스택
- Python 3.12. 게임 코드(`blackjack/`)는 **표준 라이브러리만** 쓴다. HTTP는 `urllib.request`.
- 테스트는 pytest(`tests/`). 서버·외부 호스팅 없음. GitHub Actions와 저장소 파일만 쓴다.

## 명령
```bash
python -m pytest            # 전체 테스트
python -m blackjack.main    # 워크플로 진입점 (GITHUB_TOKEN, BLACKJACK_SECRET 필요)
```

## 꼭 지킬 것
- **README는 `<!-- blackjack -->` … `<!-- /blackjack -->` 사이만 바꾼다.** 구간 밖(기존 프로필 내용)은 바이트 단위로 그대로 둔다. 마커가 없거나 짝이 안 맞으면 건드리지 않고 실패한다.
- 생성하는 README HTML 블록 안에 **빈 줄을 넣지 않는다**(GitHub가 Markdown으로 해석함). CSS·JS 없이 GitHub가 허용하는 태그만 쓴다.
- **덱 비공개(R19):** 상태 파일·로그·Issue 댓글·커밋 메시지 어디에도 남은 덱 순서나 딜러의 숨긴 카드를 남기지 않는다. 덱은 `HMAC-SHA256(BLACKJACK_SECRET, "game:{game_id}")` 시드로 매번 다시 계산한다. `deck` 필드를 상태 파일에 두지 않는다.
- 상태 변경은 커밋·push가 성공한 뒤에만 Issue 댓글·닫기·잠금을 한다. `last_processed_issue` 이하 번호에는 행동을 다시 적용하지 않는다.
- 제목이 `blackjack-`으로 시작하지 않는 Issue는 절대 건드리지 않는다.
- GitHub API는 테스트에서 가짜 클라이언트로 바꿀 수 있는 인터페이스로 둔다. 테스트가 실제 GitHub를 호출하지 않게 한다.
- 카드 SVG는 퍼블릭 도메인/CC0 등 공개 라이선스만 쓰고, 출처와 라이선스 파일을 `assets/cards/`에 함께 둔다.

## Git과 자동화 범위
- `main`은 곧 공개 프로필 README다. 작업은 **기능 브랜치**에서 하고 PR로 `main`에 합친다.
- 확인 없이 해도 되는 것: 테스트가 통과한 작업 단위의 로컬 커밋, 기능 브랜치 push, PR 생성.
- **확인 받고 할 것:** PR 머지(= 프로필에 공개됨), GitHub Issue 생성(테스트용 `blackjack-*` Issue는 공개 판 상태를 바꿈), 저장소 설정 변경.
- `main`에 직접 커밋·push하지 않는다.

## 소유자가 직접 하는 일
- 저장소 Secret `BLACKJACK_SECRET` 등록.
- 실제 동작 확인(Issue로 Deal → Hit → Stand, Reset 6회).

## 기타
- `.superpowers/`는 설계 시안 파일이라 커밋하지 않는다(`.gitignore`).
- 문서와 코드 주석, 커밋 메시지는 한국어로 쓴다.
