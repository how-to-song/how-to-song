"""비밀값 기반 셔플. 덱은 저장하지 않고 필요할 때마다 다시 계산한다."""

import hashlib
import hmac
import random

from blackjack.cards import full_deck


def shuffled_deck(secret: str, game_id: int) -> list[str]:
    digest = hmac.new(secret.encode(), f"game:{game_id}".encode(), hashlib.sha256).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    deck = full_deck()
    rng.shuffle(deck)
    return deck
