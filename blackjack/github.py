"""GitHub REST/GraphQL 클라이언트 (urllib만 사용)."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

API = "https://api.github.com"
BOT_LOGIN = "github-actions[bot]"
GAME_PREFIX = "blackjack-"

CONTRIBUTIONS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionCalendar { totalContributions } }
  }
}
"""


class GitHubError(Exception):
    pass


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    author: str


def _next_link(headers: dict[str, str]) -> str | None:
    link = headers.get("Link") or headers.get("link") or ""
    for part in link.split(","):
        url_part, _, rel = part.partition(";")
        if 'rel="next"' in rel:
            return url_part.strip().strip("<>")
    return None


class GitHubClient:
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo

    def _request(self, method: str, url: str, body: dict | None = None) -> tuple[object, dict[str, str]]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "how-to-song-blackjack",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                headers = dict(resp.headers.items())
        except urllib.error.HTTPError as e:
            raise GitHubError(f"{method} {url} → HTTP {e.code}") from None
        except urllib.error.URLError as e:
            raise GitHubError(f"{method} {url} → {e.reason}") from None
        return (json.loads(raw) if raw else None), headers

    def _issue_url(self, number: int) -> str:
        return f"{API}/repos/{self.repo}/issues/{number}"

    def list_open_game_issues(self) -> list[Issue]:
        url: str | None = f"{API}/repos/{self.repo}/issues?state=open&per_page=100"
        issues = []
        while url:
            items, headers = self._request("GET", url)
            for it in items:
                if "pull_request" in it:
                    continue
                if it["title"].strip().lower().startswith(GAME_PREFIX):
                    issues.append(Issue(it["number"], it["title"], it["user"]["login"]))
            url = _next_link(headers)
        return sorted(issues, key=lambda i: i.number)

    def has_bot_comment(self, number: int) -> bool:
        url: str | None = f"{self._issue_url(number)}/comments?per_page=100"
        while url:
            items, headers = self._request("GET", url)
            if any((c.get("user") or {}).get("login") == BOT_LOGIN for c in items):
                return True
            url = _next_link(headers)
        return False

    def comment(self, number: int, body: str) -> None:
        self._request("POST", f"{self._issue_url(number)}/comments", {"body": body})

    def close(self, number: int) -> None:
        self._request("PATCH", self._issue_url(number), {"state": "closed", "state_reason": "completed"})

    def lock(self, number: int) -> None:
        self._request("PUT", f"{self._issue_url(number)}/lock", {"lock_reason": "resolved"})

    def total_contributions(self, login: str) -> int:
        data, _ = self._request("POST", f"{API}/graphql",
                                {"query": CONTRIBUTIONS_QUERY, "variables": {"login": login}})
        if not isinstance(data, dict) or data.get("errors"):
            raise GitHubError("기여 수 조회 실패")
        user = (data.get("data") or {}).get("user")
        if not user:
            raise GitHubError("기여 수 조회 실패: 사용자를 찾을 수 없음")
        return int(user["contributionsCollection"]["contributionCalendar"]["totalContributions"])
