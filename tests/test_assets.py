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


def test_readme_has_markers_at_top():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert text.startswith(MARK_START + "\n" + MARK_END + "\n\n<div align=\"center\">")
