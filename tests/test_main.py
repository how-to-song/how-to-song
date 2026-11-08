import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from blackjack.deck import shuffled_deck
from blackjack.github import Issue
from blackjack.main import main, parse_action, run
from blackjack.state import add_history, initial_state, load_state, save_state
from tests.fakes import FakeGitHub

NOW = datetime(2026, 11, 8, 5, 5, tzinfo=timezone.utc)
README = "<!-- blackjack -->\n<!-- /blackjack -->\n\n<div>profile</div>\n"


@pytest.fixture
def files(tmp_path):
    rp = tmp_path / "README.md"
    rp.write_text(README, encoding="utf-8")
    sp = tmp_path / "state.json"
    pushes = []

    def default_push(paths, msg):
        pushes.append((paths, msg))

    def go(gh, push=default_push):
        return run(gh=gh, secret="s", now=NOW, state_path=sp, readme_path=rp, push=push)

    return SimpleNamespace(sp=sp, rp=rp, pushes=pushes, go=go)


def test_parse_action():
    assert parse_action(" Blackjack-HIT ") == "hit"
    assert parse_action("blackjack-hit please") == "unknown"
    assert parse_action("blackjack-split") == "unknown"


def test_processes_issues_in_order(files):
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a"), Issue(6, "blackjack-deal", "b"), Issue(7, "blackjack-foo", "c")])
    assert files.go(gh) == 0
    s = load_state(files.sp)
    assert s["last_processed_issue"] == 7 and [h["issue"] for h in s["history"]] == [6, 5]
    assert s["game_id"] == 1 and s["history"][0]["action"] == "Deal"
    assert gh.closed == {5, 6, 7} and gh.locked == {5, 6, 7}
    assert gh.comments[7] == ["알 수 없는 행동입니다. README의 버튼을 눌러 주세요."]
    assert len(files.pushes) == 1 and files.pushes[0][1] == "blackjack: Issue #5~#7 처리"
    assert "<div>profile</div>" in files.rp.read_text(encoding="utf-8")


def test_rejected_action_is_commented_but_not_in_history(files):
    gh = FakeGitHub([Issue(5, "blackjack-hit", "a")])
    files.go(gh)
    assert gh.comments[5] == ["지금은 Hit을(를) 할 수 없습니다. (현재 상태: idle)"]
    s = load_state(files.sp)
    assert s["history"] == [] and s["last_processed_issue"] == 5
    assert files.pushes[0][1] == "blackjack: Issue #5 처리"


def test_already_processed_issue_is_not_reapplied(files):
    s = initial_state()
    s["last_processed_issue"] = 10
    add_history(s, issue=10, action="Reset", detail="이전 결과", actor="a", now=NOW)
    save_state(s, files.sp)
    files.go(FakeGitHub([]))                   # README 게임판을 한 번 그려 둔다
    files.pushes.clear()
    gh = FakeGitHub([Issue(10, "blackjack-reset", "a")])
    assert files.go(gh) == 0
    assert gh.comments[10] == ["이전 결과"] and gh.closed == {10}
    assert files.pushes == [] and load_state(files.sp)["reset_log"]["counts"] == {}


def test_already_processed_with_bot_comment_only_closes(files):
    s = initial_state()
    s["last_processed_issue"] = 10
    save_state(s, files.sp)
    gh = FakeGitHub([Issue(10, "blackjack-deal", "a")], bot_commented={10})
    files.go(gh)
    assert 10 not in gh.comments and gh.closed == {10} and gh.locked == {10}


def test_already_processed_without_history_says_so(files):
    s = initial_state()
    s["last_processed_issue"] = 10
    save_state(s, files.sp)
    gh = FakeGitHub([Issue(9, "blackjack-deal", "a")])
    files.go(gh)
    assert gh.comments[9] == ["이미 처리된 요청입니다."]


def test_missing_marker_changes_nothing(files):
    files.rp.write_text("<div>profile</div>\n", encoding="utf-8")
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a")])
    assert files.go(gh) == 1
    assert not files.sp.exists() and files.rp.read_text(encoding="utf-8") == "<div>profile</div>\n"
    assert files.pushes == [] and gh.comments == {} and gh.closed == set()


def test_push_failure_leaves_issues_open(files):
    def bad_push(paths, msg):
        raise subprocess.CalledProcessError(1, "git push")

    gh = FakeGitHub([Issue(5, "blackjack-reset", "a")])
    assert files.go(gh, push=bad_push) == 1
    assert gh.comments == {} and gh.closed == set()


def test_idle_run_does_not_push(files):
    files.go(FakeGitHub([]))            # 첫 실행: 초기 상태와 게임판을 만든다
    assert len(files.pushes) == 1 and files.pushes[0][1] == "blackjack: 게임판 갱신"
    files.go(FakeGitHub([]))
    assert len(files.pushes) == 1


def test_one_close_failure_does_not_block_others(files):
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a"), Issue(6, "blackjack-deal", "a")], fail_close={5})
    assert files.go(gh) == 1
    assert gh.closed == {6}


def test_state_file_never_contains_hole_card(files):
    gh = FakeGitHub([Issue(5, "blackjack-reset", "a"), Issue(6, "blackjack-deal", "a")])
    files.go(gh)
    hole = shuffled_deck("s", 1)[3]
    s = load_state(files.sp)
    if s["status"] == "playing":
        assert hole not in files.sp.read_text(encoding="utf-8")
        assert f"assets/cards/{hole}.svg" not in files.rp.read_text(encoding="utf-8")


def test_main_requires_secret(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.delenv("BLACKJACK_SECRET", raising=False)
    assert main() == 1
