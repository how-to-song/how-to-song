"""워크플로 진입점: 열린 blackjack-* Issue를 처리하고 README를 갱신한다.

순서: 행동 적용 → 상태 파일·README 저장 → 커밋·push → (성공하면) 댓글·닫기·잠금.
push가 실패하면 Issue는 열린 채로 남고 다음 실행이 다시 처리한다.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from blackjack.deck import shuffled_deck
from blackjack.game import ACTIONS, LABELS, apply_action
from blackjack.github import GitHubClient, GitHubError, Issue
from blackjack.render import MarkerError, render_board, replace_section
from blackjack.state import STATE_PATH, add_history, dump_state, find_history, kst_iso, load_state

UNKNOWN_MESSAGE = "알 수 없는 행동입니다. README의 버튼을 눌러 주세요."
ALREADY_MESSAGE = "이미 처리된 요청입니다."
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


@dataclass
class Reply:
    number: int
    message: str
    already_processed: bool


def parse_action(title: str) -> str:
    name = title.strip().lower()
    if name.startswith("blackjack-") and name[len("blackjack-"):] in ACTIONS:
        return name[len("blackjack-"):]
    return "unknown"


def handle_issues(state: dict, issues: list[Issue], *, now: datetime,
                  deck_for: Callable[[int], list[str]],
                  fetch_contributions: Callable[[str], int]) -> list[Reply]:
    replies = []
    for issue in sorted(issues, key=lambda i: i.number):
        if issue.number <= state["last_processed_issue"]:
            entry = find_history(state, issue.number)
            replies.append(Reply(issue.number, entry["detail"] if entry else ALREADY_MESSAGE, True))
            continue
        action = parse_action(issue.title)
        if action == "unknown":
            message = UNKNOWN_MESSAGE
        else:
            out = apply_action(state, action, actor=issue.author, now=now,
                               deck_for=deck_for, fetch_contributions=fetch_contributions)
            message = out.message
            if out.changed:
                add_history(state, issue=issue.number, action=LABELS[action],
                            detail=message, actor=issue.author, now=now)
        state["last_processed_issue"] = issue.number
        state["last_updated"] = kst_iso(now)
        replies.append(Reply(issue.number, message, False))
    return replies


def finalize(gh, replies: list[Reply]) -> int:
    failures = 0
    for reply in replies:
        try:
            if not (reply.already_processed and gh.has_bot_comment(reply.number)):
                gh.comment(reply.number, reply.message)
            gh.close(reply.number)
            gh.lock(reply.number)
        except GitHubError as e:
            failures += 1
            print(f"Issue #{reply.number} 마무리 실패: {e}")
    return failures


def git_commit_and_push(paths: list[Path], message: str) -> None:
    subprocess.run(["git", "add", *map(str, paths)], check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        return
    subprocess.run(["git", "-c", f"user.name={BOT_NAME}", "-c", f"user.email={BOT_EMAIL}",
                    "commit", "-m", message], check=True)
    subprocess.run(["git", "pull", "--rebase"], check=True)
    subprocess.run(["git", "push"], check=True)


def _commit_message(new_numbers: list[int]) -> str:
    if not new_numbers:
        return "blackjack: 게임판 갱신"
    if len(new_numbers) == 1:
        return f"blackjack: Issue #{new_numbers[0]} 처리"
    return f"blackjack: Issue #{new_numbers[0]}~#{new_numbers[-1]} 처리"


def _read(path: Path) -> str | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def run(*, gh, secret: str, now: datetime, state_path: Path, readme_path: Path,
        push: Callable[[list[Path], str], None]) -> int:
    state = load_state(state_path)
    issues = gh.list_open_game_issues()
    replies = handle_issues(state, issues, now=now,
                            deck_for=lambda gid: shuffled_deck(secret, gid),
                            fetch_contributions=gh.total_contributions)

    readme = _read(readme_path) or ""
    try:
        new_readme = replace_section(readme, render_board(state))
    except MarkerError as e:
        print(f"README를 갱신할 수 없습니다: {e}")
        return 1

    written = []
    new_state = dump_state(state)
    if _read(state_path) != new_state:
        _write(state_path, new_state)
        written.append(state_path)
    if readme != new_readme:
        _write(readme_path, new_readme)
        written.append(readme_path)

    if written:
        new_numbers = [r.number for r in replies if not r.already_processed]
        try:
            push(written, _commit_message(new_numbers))
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"커밋·push 실패, Issue는 열어 둡니다: {e}")
            return 1

    return 1 if finalize(gh, replies) else 0


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    secret = os.environ.get("BLACKJACK_SECRET", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "how-to-song/how-to-song")
    if not token:
        print("GITHUB_TOKEN이 설정되지 않았습니다")
        return 1
    if not secret:
        print("BLACKJACK_SECRET이 설정되지 않았습니다. 저장소 Secret에 등록해 주세요.")
        return 1
    return run(gh=GitHubClient(token, repo), secret=secret, now=datetime.now(timezone.utc),
               state_path=STATE_PATH, readme_path=Path("README.md"), push=git_commit_and_push)


if __name__ == "__main__":
    sys.exit(main())
