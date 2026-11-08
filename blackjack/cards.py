"""카드 표기와 점수 계산."""

SUITS = ("S", "H", "D", "C")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")


def full_deck() -> list[str]:
    """정렬된 52장 덱 (무늬 순, 그 안에서 숫자 순)."""
    return [suit + rank for suit in SUITS for rank in RANKS]


def _rank_points(card: str) -> int:
    rank = card[1:]
    if rank == "A":
        return 1
    if rank in ("J", "Q", "K"):
        return 10
    return int(rank)


def hand_value(cards: list[str]) -> tuple[int, bool]:
    """(합계, soft 여부). Ace 하나를 11로 셀 수 있으면 soft."""
    total = sum(_rank_points(c) for c in cards)
    has_ace = any(c[1:] == "A" for c in cards)
    if has_ace and total + 10 <= 21:
        return total + 10, True
    return total, False


def is_blackjack(cards: list[str]) -> bool:
    return len(cards) == 2 and hand_value(cards)[0] == 21
