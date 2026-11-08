import pytest

from blackjack.github import GitHubClient, GitHubError, Issue


class Scripted(GitHubClient):
    def __init__(self, responses):
        super().__init__("tok", "how-to-song/how-to-song")
        self.responses = responses
        self.calls = []

    def _request(self, method, url, body=None):
        self.calls.append((method, url, body))
        return self.responses.pop(0)


def item(n, title, pr=False):
    d = {"number": n, "title": title, "user": {"login": "octocat"}}
    if pr:
        d["pull_request"] = {}
    return d


def test_list_filters_and_sorts():
    gh = Scripted([([item(9, " Blackjack-HIT "), item(3, "blackjack-deal"), item(5, "bug report"),
                     item(4, "blackjack-stand", pr=True)], {})])
    assert gh.list_open_game_issues() == [Issue(3, "blackjack-deal", "octocat"),
                                          Issue(9, " Blackjack-HIT ", "octocat")]


def test_list_follows_pagination():
    nxt = ('<https://api.github.com/repositories/1/issues?page=2>; rel="next", '
           '<https://api.github.com/repositories/1/issues?page=2>; rel="last"')
    gh = Scripted([([item(1, "blackjack-deal")], {"Link": nxt}), ([item(2, "blackjack-hit")], {})])
    assert [i.number for i in gh.list_open_game_issues()] == [1, 2]
    assert gh.calls[1][1] == "https://api.github.com/repositories/1/issues?page=2"


def test_has_bot_comment():
    gh = Scripted([([{"user": {"login": "octocat"}}, {"user": {"login": "github-actions[bot]"}}], {})])
    assert gh.has_bot_comment(7) is True


def test_close_and_lock_requests():
    gh = Scripted([(None, {}), (None, {})])
    gh.close(7)
    gh.lock(7)
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
    with pytest.raises(GitHubError):
        gh.total_contributions("how-to-song")
    with pytest.raises(GitHubError):
        gh.total_contributions("how-to-song")
