from blackjack.cards import full_deck


def stacked_deck(top: list[str]) -> list[str]:
    """top을 맨 위에 두고, 나머지는 정렬된 덱 순서로 붙인다."""
    return list(top) + [c for c in full_deck() if c not in top]
