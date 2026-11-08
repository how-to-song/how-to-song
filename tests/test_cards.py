from blackjack.cards import full_deck, hand_value, is_blackjack


def test_full_deck_is_52_unique_cards():
    deck = full_deck()
    assert len(deck) == 52 and len(set(deck)) == 52
    assert deck[0] == "SA" and deck[-1] == "CK" and "D10" in deck


def test_face_cards_are_ten():
    assert hand_value(["HK", "DQ"]) == (20, False)
    assert hand_value(["SJ", "C10"]) == (20, False)


def test_ace_is_eleven_when_safe():
    assert hand_value(["SA", "H6"]) == (17, True)


def test_ace_drops_to_one_when_over():
    assert hand_value(["SA", "H6", "DK"]) == (17, False)


def test_two_aces():
    assert hand_value(["SA", "HA"]) == (12, True)
    assert hand_value(["SA", "HA", "D9"]) == (21, True)
    assert hand_value(["SA", "HA", "D9", "CK"]) == (21, False)


def test_blackjack_needs_exactly_two_cards():
    assert is_blackjack(["SA", "HK"]) is True
    assert is_blackjack(["SA", "H5", "D5"]) is False
    assert is_blackjack(["HK", "DQ"]) is False
