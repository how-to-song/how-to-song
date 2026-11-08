from blackjack.github import GitHubError, Issue


class FakeGitHub:
    """GitHubClient와 같은 메서드를 가진 테스트용 가짜."""

    def __init__(self, issues: list[Issue], contributions=345, bot_commented=(), fail_close=()):
        self.issues = list(issues)
        self.contributions = contributions
        self.bot_commented = set(bot_commented)
        self.fail_close = set(fail_close)
        self.comments: dict[int, list[str]] = {}
        self.closed: set[int] = set()
        self.locked: set[int] = set()

    def list_open_game_issues(self) -> list[Issue]:
        return sorted(self.issues, key=lambda i: i.number)

    def has_bot_comment(self, number: int) -> bool:
        return number in self.bot_commented

    def comment(self, number: int, body: str) -> None:
        self.comments.setdefault(number, []).append(body)

    def close(self, number: int) -> None:
        if number in self.fail_close:
            raise GitHubError(f"close #{number} failed")
        self.closed.add(number)

    def lock(self, number: int) -> None:
        self.locked.add(number)

    def total_contributions(self, login: str) -> int:
        if isinstance(self.contributions, Exception):
            raise self.contributions
        return self.contributions
