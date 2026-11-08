"""README 게임 구간 HTML 생성과 마커 사이 치환.

GitHub README가 허용하는 태그만 쓰고, CSS/JS는 쓰지 않는다.
생성한 HTML 안에 빈 줄이 있으면 GitHub가 HTML 블록을 끊으므로 빈 줄을 넣지 않는다.
"""

import html
from datetime import datetime
from urllib.parse import quote

from blackjack.cards import hand_value
from blackjack.game import BET, LABELS, RESULT_TEXT, allowed_actions

MARK_START = "<!-- blackjack -->"
MARK_END = "<!-- /blackjack -->"
REPO = "how-to-song/how-to-song"
CARD_WIDTH = 70

NOTICE = "🤖 링크를 누른 뒤 약 1분 후 새로고침(F5)해 주세요!"
ISSUE_BODY = "이 Issue의 제목과 내용을 바꾸지 말고 그대로 제출만 하세요. 약 1분 뒤 프로필 README가 갱신됩니다."


class MarkerError(Exception):
    """README의 게임 구간 마커가 없거나 짝이 맞지 않음."""


def action_url(action: str) -> str:
    return f"https://github.com/{REPO}/issues/new?title=blackjack-{action}&body={quote(ISSUE_BODY)}"


def _card_img(card: str) -> str:
    return f'<img src="assets/cards/{card}.svg" width="{CARD_WIDTH}">'


def _hand_row(label: str, cards: list[str], total: str) -> str:
    imgs = " ".join(_card_img(c) for c in cards)
    return f"<tr><th>{label}</th><td>{imgs}</td><td><b>{total}</b></td></tr>"


def _updated(state: dict) -> str:
    if not state["last_updated"]:
        return "-"
    return datetime.fromisoformat(state["last_updated"]).strftime("%Y-%m-%d %H:%M")


def render_board(state: dict) -> str:
    status = state["status"]
    lines = ['<div align="center">',
             f"<p>{NOTICE}<br><sub>마지막 갱신: {_updated(state)} KST</sub></p>"]

    if status in ("finished", "broke") and state["result"]:
        lines.append(f'<h3 align="center">{RESULT_TEXT[state["result"]]}</h3>')

    player, dealer = state["player_hand"], state["dealer_hand"]
    lines.append("<table>")
    if not player:
        lines.append(_hand_row("Dealer", ["back", "back"], "-"))
        lines.append(_hand_row("Player", ["back", "back"], "-"))
    else:
        if status == "playing":
            lines.append(_hand_row("Dealer", dealer + ["back"], "?"))
        else:
            lines.append(_hand_row("Dealer", dealer, str(hand_value(dealer)[0])))
        lines.append(_hand_row("Player", player, str(hand_value(player)[0])))
    lines.append("</table>")

    lines.append(f"<p>🪙 보유 칩 <b>{state['current_chips']}</b> · 베팅 <b>{BET}</b></p>")
    if status == "idle":
        hint = "Reset을 눌러 게임을 시작하세요" if state["current_chips"] < BET else "Deal을 눌러 새 판을 시작하세요"
        lines.append(f"<p>{hint}</p>")

    buttons = " ".join(
        f'<a href="{html.escape(action_url(a))}"><img src="assets/buttons/{a}.svg" alt="{LABELS[a]}"></a>'
        for a in allowed_actions(state))
    lines.append(f"<p>{buttons}</p>")

    lines.append("<table>")
    lines.append("<tr><th>행동</th><th>내용</th><th>플레이어</th></tr>")
    if not state["history"]:
        lines.append('<tr><td colspan="3">아직 기록이 없습니다</td></tr>')
    for entry in state["history"]:
        actor = html.escape(entry["actor"])
        lines.append(f"<tr><td>{html.escape(entry['action'])}</td><td>{html.escape(entry['detail'])}</td>"
                     f'<td><a href="https://github.com/{actor}">@{actor}</a></td></tr>')
    lines.append("</table>")
    lines.append("</div>")
    return "\n".join(lines)


def replace_section(readme: str, board: str) -> str:
    if readme.count(MARK_START) != 1 or readme.count(MARK_END) != 1:
        raise MarkerError("README에 게임 구간 마커가 정확히 한 쌍 있어야 합니다")
    start = readme.find(MARK_START)
    end = readme.find(MARK_END)
    if end < start:
        raise MarkerError("README 게임 구간 마커의 순서가 잘못되었습니다")
    return readme[:start] + MARK_START + "\n" + board + "\n" + readme[end:]
