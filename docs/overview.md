# GitHub Commit-Powered Blackjack 개요

## 한 줄 요약
GitHub 프로필 저장소(`how-to-song/how-to-song`)의 README에서, 방문자 누구나 Issue 링크를 눌러 하나의 공유 판을 이어서 플레이하는 블랙잭 게임이다. 칩은 소유자(`how-to-song`)의 최근 1년 기여 수에서 나온다.

## 왜 만드는가
- 프로필에 들어온 사람의 **눈에 확 들어오는** 볼거리를 만든다. (사용자 발언: "디자인이 눈에 확 들어왔으면 좋겠어")
- 소유자의 GitHub 활동(잔디)이 게임 자산이 되어, 프로필과 게임이 자연스럽게 연결된다.

## 목표
- 기존 프로필 README 내용(Tech Stacks, Hi there, Projects, Skills 등)을 그대로 둔 채, 정해진 구간에 게임판을 그린다.
- 카드 그림이 들어간 표 형태의 게임판(A안)으로 시각적으로 돋보이게 한다.
- Deal / Hit / Stand / Reset 네 가지 행동으로 블랙잭 한 판을 끝까지 진행할 수 있다.
- 누가 무엇을 했는지 행동 기록이 남아, 공유 판의 재미를 살린다.

## 하지 않는 것 (Non-goals)
- 실시간 반응: README 특성상 불가능하다. 한 행동당 약 1분이 걸리는 것을 받아들인다.
- 더블다운, 스플릿, 인슈어런스, 베팅금 변경.
- 방문자별 개별 판이나 개별 칩.
- 서버나 외부 호스팅. GitHub Actions와 저장소 파일만 사용한다.

## 실패로 보는 것 (Anti-goals)
- 게임이 기존 프로필 내용을 덮어쓰거나 망가뜨리는 것.
- 공개 저장소 파일이나 Actions 로그를 보고 다음 카드나 딜러의 숨긴 카드를 알 수 있는 것.
- 처리되지 않은 Issue가 열린 채로 쌓이는 것.
- 게임판이 밋밋한 텍스트 표로만 보이는 것.

## 관련 문서
- 요구사항: [requirements.md](requirements.md)
- 설계: [architecture.md](architecture.md)
- 원본 기획서: `D:\How_Vault\10.PROJECT\github_blackjack\GitHub Blackjack.md`
