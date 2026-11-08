import pytest

from blackjack.render import MarkerError, action_url, render_board, replace_section
from blackjack.state import initial_state


def playing_state():
    s = initial_state()
    s.update(status="playing", current_chips=90, player_hand=["HK", "C9"], dealer_hand=["D5"])
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
    s = playing_state()
    s["status"] = status
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
    s = playing_state()
    s.update(status="finished", result="player_blackjack", dealer_hand=["D5", "S7"])
    html = render_board(s)
    assert '<h3 align="center">블랙잭 승리!</h3>' in html
    assert "assets/cards/S7.svg" in html and "back.svg" not in html


def test_history_links_actor_and_escapes():
    s = initial_state()
    s["history"] = [{"issue": 3, "action": "Hit", "detail": "<b>x</b>", "actor": "octocat",
                     "at": "2026-11-08T14:05:00+09:00"}]
    s["last_updated"] = "2026-11-08T14:05:00+09:00"
    html = render_board(s)
    assert '<a href="https://github.com/octocat">@octocat</a>' in html
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "마지막 갱신: 2026-11-08 14:05 KST" in html


def test_action_url_prefills_body():
    url = action_url("deal")
    assert url.startswith("https://github.com/how-to-song/how-to-song/issues/new?title=blackjack-deal&body=")
    assert " " not in url
