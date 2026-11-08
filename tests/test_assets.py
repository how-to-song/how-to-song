from pathlib import Path

from blackjack.cards import full_deck
from blackjack.render import MARK_END, MARK_START

ROOT = Path(__file__).resolve().parent.parent


def test_every_card_has_an_image():
    missing = [c for c in full_deck() + ["back"] if not (ROOT / "assets/cards" / f"{c}.svg").exists()]
    assert missing == []


def test_card_license_recorded():
    text = (ROOT / "assets/cards/LICENSE.md").read_text(encoding="utf-8")
    assert "출처" in text and "라이선스" in text


def test_buttons_exist():
    for a in ("deal", "hit", "stand", "reset"):
        assert (ROOT / "assets/buttons" / f"{a}.svg").exists()


def test_readme_game_section_is_at_bottom():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(MARK_START)
    before = text[:start]
    assert "Tech Stacks" in before and "## Let's connect" in before
    assert before.rstrip().endswith("## 🃏 Blackjack")      # 템플릿 주석 밖, 제목 바로 아래
    assert before.endswith("\n\n")                          # HTML 블록이 앞 내용과 섞이지 않게
    assert text.rstrip().endswith(MARK_END)


def test_projects_lists_blackjack():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    projects = text[text.index("## Projects"):text.index("## Skills")]
    assert "### [GitHub Blackjack](https://github.com/how-to-song/how-to-song/tree/main/blackjack) - " in projects
